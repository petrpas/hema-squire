from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import (
    bank,
    dedup,
    emails,
    importer,
    issuing,
    matching,
    nameresolve,
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
    ManualPayment,
    Operation,
    OperationKind,
    PaymentEvent,
    RefundState,
    Registration,
    RegistrationState,
    Tournament,
)

# one rounding rule for money leaving the API, not a second copy of it here
from app.routers.registrations import _cents_to_amount, next_vs
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import (
    ExpiredHoldingOut,
    IngestAndMatchOut,
    LinkIn,
    ManualPaymentIn,
    ManualPaymentOut,
    PaymentLinkOut,
    RankedFencerOut,
    TransactionOut,
    TransactionRosterOut,
)

router = APIRouter(prefix="/api/tournaments/{slug}/payments", tags=["payments"])

FioClientDep = Annotated[bank.FioClient, Depends(bank.get_fio_client)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]
# None where no model is configured; an unrecognised statement then has nothing
# to be read with, and the endpoint says so rather than ingesting nothing
StatementParserDep = Annotated[
    bank.StatementParser | None, Depends(bank.get_statement_parser)
]


def _refuse_while_duplicates_pending(session, tournament) -> None:
    """Intake stops while the fencer list still holds unresolved duplicates.

    Not a rule about intake at all, but the only place it can be enforced. Intake
    issues registrations for the rows before it matches anything, and a merge
    collapses *rows*, not registrations — so a registration issued ahead of the
    verdict survives its own merge and leaves one person holding two, with a
    payment free to settle either. Refusing here makes that state unreachable by
    the order of the phases rather than by an error the organizer meets two
    phases before they could act on it (spec payments-intake, design Decision 10).
    """
    pending = dedup.unresolved_groups(session, tournament)
    if pending:
        raise HTTPException(
            status_code=409,
            detail={"code": "dedup_pending", "groups": pending},
        )


def _ingest_and_match(session, tournament, mailer, source, transactions) -> IngestAndMatchOut:
    # the roster is made billable first, because matching resolves a payment
    # through `Registration.vs` and a row has none. Idempotent, so every intake
    # after the first issues nothing and a list that gained rows in between is
    # caught up without anybody remembering to (spec payments-intake)
    issued = issuing.issue(session, tournament, next_vs)
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
        issued=issued.issued,
        already_issued=issued.already,
        skipped=[
            {"row_id": skip.row_id, "name": skip.name, "reason": skip.reason}
            for skip in issued.skipped
        ],
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
    _refuse_while_duplicates_pending(session, tournament)
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
    _refuse_while_duplicates_pending(session, tournament)
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
    known_ids = set(
        session.scalars(
            select(Registration.id).where(
                Registration.tournament_id == tournament.id,
                Registration.id.in_(data.registration_ids),
            )
        )
    )
    unknown_ids = [rid for rid in data.registration_ids if rid not in known_ids]
    if unknown_ids:
        raise HTTPException(status_code=404, detail={"unknown_registrations": unknown_ids})

    payload = {"vs": data.vs}
    if data.registration_ids:
        payload["registration_ids"] = data.registration_ids
    rule = rules.create_rule(
        session,
        tournament,
        fencer,
        phase="payments",
        kind="payment_link",
        target=f"txn:{transaction.external_id}",
        payload=payload,
    )
    applied = matching.apply_payment_links(session, tournament, mailer)
    return {"rule_id": rule.id, "applied": applied}


@router.get("/likely", response_model=list[TransactionOut])
def likely_transactions(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Payments the resolver read a fencer's name in, waiting for a person.

    A queue of proposals, not of outcomes: nothing here has been credited and
    nobody has been mailed. Confirming is the organizer supplying the variable
    symbol the payer omitted (spec name-assisted-matching)."""
    require_console_access(session, tournament, fencer)
    rows = session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.tournament_id == tournament.id,
            BankTransaction.status == nameresolve.LIKELY,
        )
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
    return [_transaction_out(session, tournament, row) for row in rows]


def _proposal(session, tournament, transaction_id: int) -> BankTransaction:
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if transaction.status != nameresolve.LIKELY:
        raise HTTPException(status_code=409, detail="not_a_proposal")
    return transaction


@router.post("/likely/{transaction_id}/confirm", status_code=201)
def confirm_proposal(
    transaction_id: int,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    """Accept the resolver's reading and credit the payment.

    Goes through the manual-link path rather than beside it (design Decision
    5): the same `payment_link` rule, the same crediting, the same tolerance,
    the same survival across reruns. Confirming *is* the organizer supplying
    the reference the payer omitted, so a confirmed proposal is afterwards
    indistinguishable from a payment linked by hand — which is what it is.
    """
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    transaction = _proposal(session, tournament, transaction_id)
    registration = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == transaction.proposed_fencer_id,
            Registration.state.in_([RegistrationState.RESERVED, RegistrationState.PAID]),
        )
    )
    if registration is None:
        raise HTTPException(status_code=409, detail="no_registration_to_credit")

    # addressed by id, not by symbol: the proposal named a person, and on a
    # tournament whose organizer keeps the roster there is no symbol to name
    rule = rules.create_rule(
        session,
        tournament,
        fencer,
        phase="payments",
        kind="payment_link",
        target=f"txn:{transaction.external_id}",
        payload={"vs": [], "registration_ids": [registration.id]},
    )
    applied = matching.apply_payment_links(session, tournament, mailer)
    return {"rule_id": rule.id, "applied": applied}


@router.post("/likely/{transaction_id}/reject", response_model=TransactionOut)
def reject_proposal(
    transaction_id: int,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """Refuse the resolver's reading. The payment returns to unresolved and the
    pairing is remembered, so the same wrong answer is not offered twice.

    Remembered per payment rather than per fencer: a name that mis-attracts one
    payment has not thereby stopped being somebody's name (design, Open
    Questions)."""
    require_console_access(session, tournament, fencer)
    transaction = _proposal(session, tournament, transaction_id)
    refused = list(transaction.rejected_fencer_ids or [])
    if transaction.proposed_fencer_id is not None:
        refused.append(transaction.proposed_fencer_id)
    transaction.rejected_fencer_ids = refused
    transaction.proposed_fencer_id = None
    transaction.status = "unmatched"
    transaction.status_reason = "proposal_rejected"
    session.commit()
    session.refresh(transaction)
    return _transaction_out(session, tournament, transaction)


@router.get("/transactions/{transaction_id}/roster", response_model=TransactionRosterOut)
def transaction_roster(
    transaction_id: int,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """The whole roster, ordered by how well each fencer matches this payment's
    own text.

    Every fencer, always. Ranking them all costs nothing once the scores exist
    and never orders worse than alphabetically, and the hard payments — a
    surname two fencers share, a placeholder somebody left in the form — are
    exactly the ones no shortlist would have helped with (design Decision 6).
    """
    require_console_access(session, tournament, fencer)
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")

    resolution = nameresolve.resolve(session, tournament, transaction)
    query, _ = nameresolve.query_for(transaction)
    refused = set(transaction.rejected_fencer_ids or [])
    proposed_id = resolution.proposed.id if resolution.proposed else None

    registrations = {
        registration.fencer_id: registration
        for registration in session.scalars(
            select(Registration).where(
                Registration.tournament_id == tournament.id,
                Registration.state.in_(
                    [RegistrationState.RESERVED, RegistrationState.PAID]
                ),
            )
        )
    }
    fencers = []
    for ranked in resolution.ranked:
        registration = registrations.get(ranked.key)
        if registration is None:
            continue
        fencers.append(
            RankedFencerOut(
                fencer_id=ranked.key,
                name=ranked.name,
                registration_id=registration.id,
                vs=registration.vs,
                outstanding_amount=_cents_to_amount(registration.balance_cents(tournament)[0]),
                score=round(ranked.score, 4),
                proposed=ranked.key == proposed_id,
                rejected=ranked.key in refused,
            )
        )
    return TransactionRosterOut(
        transaction_id=transaction.id, query=query, fencers=fencers
    )


def _transaction_out(session, tournament, transaction: BankTransaction) -> TransactionOut:
    out = TransactionOut.model_validate(transaction)
    if transaction.status == "flagged":
        registration = _flagged_registration(session, tournament, transaction)
        out.reinstate_available = (
            registration is not None
            and registration.state == RegistrationState.EXPIRED
            and matching.seats_free(session, registration)
        )
        # what settled the registration, where a person did. The organizer is
        # deciding whether this is further money or the same money twice, and
        # needs the earlier act in front of them (design D6)
        if registration is not None:
            out.settled_by_hand_reason = registration.settled_by_hand_reason
            recorded = session.scalars(
                select(ManualPayment)
                .where(
                    ManualPayment.registration_id == registration.id,
                    ManualPayment.removed_at.is_(None),
                )
                .order_by(ManualPayment.id.desc())
            ).first()
            if recorded is not None:
                out.settled_by_recorded_payment = _manual_payment_out(
                    session, tournament, recorded
                )
    if transaction.status == "unmatched":
        out.candidate_vs = matching.detect_candidates(session, transaction)
    if transaction.proposed_fencer is not None:
        out.proposed_fencer_name = transaction.proposed_fencer.display_name
    return out


@router.get("/links", response_model=list[PaymentLinkOut])
def payment_links(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """The tournament's active payment links, resolved into what they join.

    A link rule names its transaction by external id and its registrations by
    symbol or id. None of that is readable: on a statement from a bank that
    numbers nothing, the external id is a fingerprint of the row's own content,
    and a link made by choosing a fencer carries no symbol to show at all. The
    queue exists so the organizer can undo the wrong link, which they cannot do
    without seeing which payment and which fencer it is — so the resolving
    happens here, once, rather than in three requests the console would have to
    join for itself (spec `payments-console`).
    """
    require_console_access(session, tournament, fencer)
    out = []
    for rule in rules.active_rules(session, tournament, kind="payment_link"):
        payload = rule.payload or {}
        registrations = matching.linked_registrations(session, tournament, payload)
        transaction = matching.transaction_for_link(session, tournament, rule.target)
        out.append(
            PaymentLinkOut(
                rule_id=rule.id,
                auto_created=payload.get("auto_created") is True,
                fencers=[
                    registration.fencer.display_name
                    for registration in registrations
                    if registration.fencer is not None
                ],
                vs=[r.vs for r in registrations if r.vs is not None],
                transaction=(
                    _transaction_out(session, tournament, transaction)
                    if transaction is not None
                    else None
                ),
            )
        )
    return out


@router.get("/resettle")
def resettleable_payments(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> dict[str, int]:
    """How many short payments the tolerance as it stands would now let
    through. Read by the tolerance card so the number is stated before the
    organizer commits to it (spec payments, Re-deciding a short payment)."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    return {"resettleable": matching.resettleable(session, tournament)}


@router.post("/resettle")
def resettle_payments(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep, mailer: MailerDep
) -> dict[str, int]:
    """Re-decide the short payments a widened tolerance now covers. Credits
    nothing: the money is already on the registration and only the verdict on
    whether it was close enough is asked again."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    return {"settled": matching.resettle_within_tolerance(session, tournament, mailer)}


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
            detail=f"{registration.audit_label}: reinstated by organizer",
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


def _manual_payment_out(
    session, tournament: Tournament, payment: ManualPayment
) -> ManualPaymentOut:
    registration = payment.registration
    which = matching.manual_payment_currency(payment, tournament)
    credited = (
        registration.amount_paid_cents if which == "local" else registration.amount_paid_eur_cents
    )
    total = (
        registration.total_amount * 100
        if which == "local"
        else (registration.total_eur or 0) * 100
    )
    return ManualPaymentOut(
        id=payment.id,
        registration_id=registration.id,
        fencer_name=registration.fencer.display_name,
        amount=_cents_to_amount(payment.amount_cents),
        currency=payment.currency,
        received_on=payment.received_on,
        method=payment.method,
        note=payment.note,
        recorded_by=payment.recorded_by,
        created_at=payment.created_at,
        # what removal would do, answered before it is asked: taking this
        # amount back leaves the lane short, so the registration would return
        # to reserved and the roster would stop saying paid
        removal_unsettles=(
            registration.state == RegistrationState.PAID
            and which is not None
            and credited - payment.amount_cents < total
        ),
    )


def _live_manual_payments(session, tournament: Tournament):
    return session.scalars(
        select(ManualPayment)
        .where(
            ManualPayment.tournament_id == tournament.id,
            ManualPayment.removed_at.is_(None),
        )
        .order_by(ManualPayment.received_on.desc(), ManualPayment.id.desc())
    ).all()


@router.get("/manual", response_model=list[ManualPaymentOut])
def list_manual_payments(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """The payments an organizer recorded by hand. Removed ones are absent:
    what the view answers is what is credited now, and a reversed payment
    credits nothing. Its record survives in the audit trail."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    return [
        _manual_payment_out(session, tournament, payment)
        for payment in _live_manual_payments(session, tournament)
    ]


@router.post("/manual", response_model=ManualPaymentOut, status_code=201)
def record_manual_payment(
    data: ManualPaymentIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    """Record a payment that arrived outside the bank feed — cash at the desk,
    a transfer to another account, a card terminal — and credit it exactly as
    an ingested transaction is credited.

    Gated on the payments setting like every other path in this router, and for
    the reason the gate exists: where Squire tracks no amounts, an amount means
    nothing it could keep. A tournament that needs amounts tracked wants Squire
    handling its payments — the line `add-manual-paid-marking` drew, and this
    keeps (design add-manual-payment-entry D7).

    The record is a `ManualPayment` and **not** a row in the bank transactions:
    that list is the statement ledger, and a row no bank sent would falsify it
    for every reader (design D2)."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    registration = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.id == data.registration_id,
        )
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="registration_not_found")
    # money is credited to a live reservation or one already settled; a
    # cancelled or expired registration is not revived by a payment being
    # typed in, exactly as it is not revived by one being ingested
    if registration.state not in (RegistrationState.RESERVED, RegistrationState.PAID):
        raise HTTPException(status_code=409, detail="registration_not_live")
    amount_cents = int((data.amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if amount_cents <= 0:
        raise HTTPException(status_code=422, detail="amount_not_positive")

    payment = ManualPayment(
        tournament_id=tournament.id,
        registration_id=registration.id,
        amount_cents=amount_cents,
        currency=data.currency,
        received_on=data.received_on,
        method=data.method,
        note=data.note,
        # the label the audit trail uses, not a foreign key: the record must
        # still read correctly when the account that made it is gone
        recorded_by=f"{fencer.display_name} <{fencer.email}>",
    )
    which = matching.manual_payment_currency(payment, tournament)
    if which is None:
        raise HTTPException(status_code=409, detail="currency_not_accepted")
    session.add(payment)
    session.flush()
    session.add(
        PaymentEvent(
            tournament_id=tournament.id,
            registration_id=registration.id,
            kind="manual_payment_recorded",
            detail=(
                f"recorded payment {payment.id}: {registration.audit_label},"
                f" {payment.amount_cents} cents {payment.currency}"
                f" by {payment.method} on {payment.received_on},"
                f" recorded by {payment.recorded_by}"
            ),
        )
    )
    matching.credit_manual_payment(session, tournament, mailer, registration, payment, which)
    session.commit()
    return _manual_payment_out(session, tournament, payment)


@router.delete("/manual/{payment_id}", response_model=ManualPaymentOut)
def remove_manual_payment(
    payment_id: int,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """Reverse a recorded payment. A soft delete, so the wrong entry and its
    reversal both survive — and there is no edit endpoint for the same reason:
    a correction is a removal and a new record, so that what was credited and
    what took it back are both readable afterwards."""
    require_console_access(session, tournament, fencer)
    bank.require_payments_enabled(tournament)
    payment = session.get(ManualPayment, payment_id)
    if payment is None or payment.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="manual_payment_not_found")
    if payment.removed_at is not None:
        raise HTTPException(status_code=409, detail="already_removed")
    which = matching.manual_payment_currency(payment, tournament)
    if which is None:
        raise HTTPException(status_code=409, detail="currency_not_accepted")
    out = _manual_payment_out(session, tournament, payment)
    matching.uncredit_manual_payment(session, tournament, payment.registration, payment, which)
    payment.removed_at = datetime.now(UTC)
    session.commit()
    return out
