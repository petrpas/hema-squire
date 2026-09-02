from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import (
    bank,
    emails,
    importer,
    matching,
    operations,
    paymentsclear,
    rules,
    scheduler,
    statements,
)
from app.auth import require_console_access
from app.mail import Mailer, get_mailer
from app.models import (
    BankTransaction,
    Operation,
    OperationKind,
    PaymentEvent,
    RefundState,
    Registration,
    RegistrationState,
    Tournament,
)

# one rounding rule for money leaving the API, not a second copy of it here
from app.routers.registrations import _cents_to_amount
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import ExpiredHoldingOut, IngestAndMatchOut, LinkIn, TransactionOut

router = APIRouter(prefix="/api/tournaments/{slug}/payments", tags=["payments"])

FioClientDep = Annotated[bank.FioClient, Depends(bank.get_fio_client)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]
# None where no model is configured; an unrecognised statement then has nothing
# to be read with, and the endpoint says so rather than ingesting nothing
StatementParserDep = Annotated[
    bank.StatementParser | None, Depends(bank.get_statement_parser)
]


def _ingest_and_match(session, tournament, mailer, source, transactions) -> IngestAndMatchOut:
    ingested = bank.ingest(session, tournament, source, transactions)
    matched = matching.match_new_transactions(session, tournament, mailer)
    matching.apply_payment_links(session, tournament, mailer)
    return IngestAndMatchOut(
        new=ingested.new,
        duplicate=ingested.duplicate,
        matched=matched.matched,
        flagged=matched.flagged,
        unmatched=matched.unmatched,
        partial=matched.partial,
        set_aside=matched.set_aside,
    )


@router.post("/import-statement", status_code=202)
async def import_statement(
    file: UploadFile,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
    parser: StatementParserDep,
):
    """Import a statement from any bank, as a started operation.

    A Fio export is read exactly; anything else is read as a table and
    interpreted (design D1). Started rather than awaited, so a long statement
    survives the organizer leaving the page (design D3) — the ingest counts
    land in the operation's outcome, not in this response.
    """
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    content = await file.read()
    filename = file.filename or "statement.csv"

    if not bank.is_fio_export(content):
        if parser is None:
            raise HTTPException(status_code=409, detail="no_statement_parser")
        try:
            rows = statements.read_rows(filename, content)
        except importer.UnsupportedFormatError:
            raise HTTPException(status_code=422, detail="unsupported_statement_format") from None
        # refused here, in the request, rather than as a failed operation: a
        # table trivial parsing already shows is not a statement should cost no
        # model call and no waiting
        try:
            statements.check_readable(rows)
        except statements.UnreadableStatementError as unreadable:
            raise HTTPException(
                status_code=422,
                detail={"code": "unreadable_statement", "missing": unreadable.missing},
            ) from None

    total = statements.statement_units(filename, content)
    try:
        operation = operations.start(
            session, tournament, OperationKind.STATEMENT, total, fencer.id
        )
    except operations.OperationInFlightError as busy:
        raise HTTPException(
            status_code=409,
            detail={"code": "operation_running", "kind": busy.kind.value},
        ) from None

    def body(work_session: Session, work_operation: Operation) -> dict:
        work_tournament = work_session.get(Tournament, work_operation.tournament_id)
        if bank.is_fio_export(content):
            transactions = bank.parse_fio_csv(content)
            operations.advance(work_session, work_operation, 1)
        else:
            transactions = statements.parse(
                work_session,
                work_tournament,
                statements.read_rows(filename, content),
                parser,
                progress=lambda s, units: operations.advance(s, work_operation, units),
            )
        outcome = _ingest_and_match(work_session, work_tournament, mailer, "csv", transactions)
        return outcome.model_dump()

    operations.run_in_background(operation.id, body)
    return {"operation_id": operation.id, "rows": total}


@router.post("/fio-poll", response_model=IngestAndMatchOut)
def fio_poll(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    fio: FioClientDep,
    mailer: MailerDep,
    days_back: int = 14,
):
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    if not tournament.fio_token:
        raise HTTPException(status_code=409, detail="fio_token_not_configured")
    today = date.today()
    transactions = fio.fetch(tournament.fio_token, today - timedelta(days=days_back), today)
    return _ingest_and_match(session, tournament, mailer, "fio_api", transactions)


@router.post("/process")
def process_lifecycle(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep, mailer: MailerDep
) -> dict[str, int]:
    """Run the lifecycle passes for this tournament now (also runs
    periodically). Same passes in the same order as the scheduler's tick,
    settlement included — running it by hand must not decide anything
    differently from letting the tick reach it.

    Refused for a payments-off tournament, whose tick skips these passes: the
    lifecycle this drives is the payment lifecycle, and settling seating by
    hand has its own action on the tournament."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    demoted = scheduler.settle_seating_if_due(session, tournament)
    expired = scheduler.process_expiries(session, tournament, mailer)
    return {
        "reminders": scheduler.process_reminders(session, tournament, mailer),
        "expired": expired,
        "seating_demoted": demoted,
    }


@router.post("/link", status_code=201)
def link_transaction(
    data: LinkIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    """Manually link an unmatched transaction to one or more registrations.
    Persists as a payment_link rule: survives reruns, removable via the rules API."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    transaction = session.get(BankTransaction, data.transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if transaction.status == "matched":
        raise HTTPException(status_code=409, detail="already_matched")
    known_vs = set(
        session.scalars(
            select(Registration.vs).where(
                Registration.tournament_id == tournament.id, Registration.vs.in_(data.vs)
            )
        )
    )
    unknown = [vs for vs in data.vs if vs not in known_vs]
    if unknown:
        raise HTTPException(status_code=404, detail={"unknown_vs": unknown})

    rule = rules.create_rule(
        session,
        tournament,
        fencer,
        phase="payments",
        kind="payment_link",
        target=f"txn:{transaction.external_id}",
        payload={"vs": data.vs},
    )
    applied = matching.apply_payment_links(session, tournament, mailer)
    return {"rule_id": rule.id, "applied": applied}


def _transaction_out(session, tournament, transaction: BankTransaction) -> TransactionOut:
    out = TransactionOut.model_validate(transaction)
    if transaction.status == "flagged":
        registration = _flagged_registration(session, tournament, transaction)
        out.reinstate_available = (
            registration is not None
            and registration.state == RegistrationState.EXPIRED
            and matching.seats_free(session, registration)
        )
    if transaction.status == "unmatched":
        out.candidate_vs = matching.detect_candidates(session, transaction)
    return out


@router.get("/clear")
def clearable_payments(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """What a clear would remove, and what stands in its way — so the console
    states a refusal before the organizer commits rather than after."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    return paymentsclear.payment_totals(session, tournament)


@router.delete("")
def clear_payments(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Remove every payment the tournament took in, and the stored readings of
    the statement rows behind them. Hard, total and final — the console confirms
    it before calling (spec payments-clearing, Clearing the payments is warned
    about and irreversible)."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    try:
        return paymentsclear.clear_payments(session, tournament)
    except paymentsclear.CreditedTransactionsError as credited:
        # money the tournament has acted on is not the console's to delete, and
        # the refusal is total: nothing is removed (spec, A refusal is total)
        raise HTTPException(
            status_code=409,
            detail={"code": "credited_transactions", "count": credited.count},
        ) from None


@router.get("/unmatched", response_model=list[TransactionOut])
def unmatched_queue(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    transactions = session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.tournament_id == tournament.id,
            BankTransaction.status.in_(["unmatched", "flagged"]),
        )
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
    return [_transaction_out(session, tournament, transaction) for transaction in transactions]


@router.get("/expired-holding", response_model=list[ExpiredHoldingOut])
def expired_holding(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Reservations that lapsed while holding money credited to them.

    Filtered to those *still* expired and still holding credit, so a reservation
    since reinstated or refunded drops off by itself: this is a work queue that
    empties, not a log. The log already exists as the payment-event trail.

    The event is what distinguishes this from an ordinary expiry — deriving the
    list from registration state alone would not tell "expired holding a
    payment" from "expired, then paid late and flagged".
    """
    require_console_access(session, tournament, fencer)
    rows = session.execute(
        select(PaymentEvent.registration_id, func.max(PaymentEvent.created_at))
        .where(
            PaymentEvent.tournament_id == tournament.id,
            PaymentEvent.kind == "expired_holding_payment",
            PaymentEvent.registration_id.is_not(None),
        )
        .group_by(PaymentEvent.registration_id)
    ).all()
    if not rows:
        return []
    expired_at = dict(rows)
    registrations = session.scalars(
        select(Registration).where(
            Registration.id.in_(expired_at),
            Registration.state == RegistrationState.EXPIRED,
        )
    ).all()
    out = [
        ExpiredHoldingOut(
            registration_id=registration.id,
            fencer_name=registration.fencer.display_name,
            vs=registration.vs,
            credited_amount=_cents_to_amount(registration.amount_paid_cents),
            credited_eur_amount=(
                _cents_to_amount(registration.amount_paid_eur_cents)
                if registration.amount_paid_eur_cents
                else None
            ),
            expired_at=expired_at[registration.id],
        )
        for registration in registrations
        if registration.amount_paid_cents or registration.amount_paid_eur_cents
    ]
    out.sort(key=lambda row: row.expired_at, reverse=True)
    return out


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    transactions = session.scalars(
        select(BankTransaction)
        .where(BankTransaction.tournament_id == tournament.id)
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
    return [_transaction_out(session, tournament, transaction) for transaction in transactions]


def _flagged_transaction(session, tournament, transaction_id: int) -> BankTransaction:
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if transaction.status != "flagged":
        raise HTTPException(status_code=409, detail="not_flagged")
    return transaction


def _flagged_registration(session, tournament, transaction: BankTransaction) -> Registration | None:
    vs = matching.effective_vs(transaction)
    if vs is None:
        return None
    return session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id, Registration.vs == vs
        )
    )


@router.post("/transactions/{transaction_id}/reinstate", response_model=TransactionOut)
def reinstate_transaction(
    transaction_id: int,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    """Applies the same effect as automatic grace reinstatement, but as an
    explicit organizer action outside the grace window (or when it was
    refused for capacity): the accepted amount is credited unconditionally,
    since the organizer has already reviewed and decided to accept it."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    transaction = _flagged_transaction(session, tournament, transaction_id)
    registration = _flagged_registration(session, tournament, transaction)
    if registration is None or registration.state != RegistrationState.EXPIRED:
        raise HTTPException(status_code=409, detail="not_reinstatable")
    if not matching.seats_free(session, registration):
        raise HTTPException(status_code=409, detail="capacity_unavailable")

    registration.state = RegistrationState.PAID
    registration.paid_at = datetime.now(UTC)
    which = matching.match_currency(transaction, tournament)
    if which == "local":
        registration.amount_paid_cents += transaction.amount_cents
    elif which == "eur":
        registration.amount_paid_eur_cents += transaction.amount_cents
    transaction.matched_registration_id = registration.id
    transaction.status = "matched"
    transaction.status_reason = "reinstated_by_organizer"
    session.add(
        PaymentEvent(
            tournament_id=tournament.id,
            registration_id=registration.id,
            transaction_id=transaction.id,
            kind="reinstated_by_organizer",
            detail=f"VS {registration.vs}: reinstated by organizer",
        )
    )
    session.commit()
    emails.send_reservation_reinstated(mailer, tournament, registration.fencer, registration)
    return transaction


@router.post("/transactions/{transaction_id}/mark-for-refund", response_model=TransactionOut)
def mark_transaction_for_refund(
    transaction_id: int,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    transaction = _flagged_transaction(session, tournament, transaction_id)
    registration = _flagged_registration(session, tournament, transaction)
    which = matching.match_currency(transaction, tournament)
    if registration is not None and which is not None:
        if which == "local":
            registration.amount_paid_cents += transaction.amount_cents
        else:
            registration.amount_paid_eur_cents += transaction.amount_cents
        registration.refund_state = RefundState.PENDING
    transaction.status = "resolved"
    transaction.status_reason = "marked_for_refund"
    session.add(
        PaymentEvent(
            tournament_id=tournament.id,
            registration_id=registration.id if registration else None,
            transaction_id=transaction.id,
            kind="marked_for_refund",
            detail=f"transaction {transaction.id}: marked for refund",
        )
    )
    session.commit()
    return transaction
