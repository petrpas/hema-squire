from datetime import UTC, date, datetime
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
    ledger,
    matching,
    nameresolve,
    operations,
    paymentsclear,
    rules,
    scheduler,
    setup,
    statements,
)
from app.auth import require_console_access, require_published
from app.fieldtypes import RowId
from app.mail import Mailer, get_mailer
from app.models import (
    BankTransaction,
    CreditOrigin,
    CreditSource,
    Currency,
    ManualPayment,
    Operation,
    OperationKind,
    PaymentCredit,
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
    CreditedPaymentOut,
    CreditReversalOut,
    CreditReversalRow,
    ExpiredHoldingOut,
    IngestAndMatchOut,
    IssueSkipOut,
    LinkIn,
    ManualPaymentIn,
    ManualPaymentOut,
    PairedRegistrationOut,
    RankedFencerOut,
    TransactionOut,
    TransactionRosterOut,
    UncreditedPaymentOut,
)

router = APIRouter(prefix="/api/tournaments/{slug}/payments", tags=["payments"])

FioClientDep = Annotated[bank.FioClient, Depends(bank.get_fio_client)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]
# None where no model is configured; an unrecognised statement then has nothing
# to be read with, and the endpoint says so rather than ingesting nothing
StatementParserDep = Annotated[bank.StatementParser | None, Depends(bank.get_statement_parser)]


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
        dropped=ingested.dropped,
        matched=matched.matched,
        flagged=matched.flagged,
        unmatched=matched.unmatched,
        partial=matched.partial,
        set_aside=matched.set_aside,
        issued=issued.issued,
        already_issued=issued.already,
        skipped=[
            IssueSkipOut(row_id=skip.row_id, name=skip.name, reason=skip.reason)
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
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    _refuse_while_duplicates_pending(session, tournament)
    content = await file.read()
    filename = file.filename or "statement.csv"

    is_fio = bank.is_fio_export(content)
    if not is_fio:
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
        operation = operations.start(session, tournament, OperationKind.STATEMENT, total, fencer.id)
    except operations.OperationInFlightError as busy:
        raise HTTPException(
            status_code=409,
            detail={"code": "operation_running", "kind": busy.kind.value},
        ) from None

    def body(work_session: Session, work_operation: Operation) -> dict:
        work_tournament = operations.reload(work_session, Tournament, work_operation.tournament_id)
        if is_fio:
            transactions = bank.parse_fio_csv(content)
            operations.advance(work_session, work_operation, 1)
        else:
            if parser is None:  # pragma: no cover - refused in the request
                # the same `is_fio` refused a missing parser above
                raise AssertionError("a non-Fio statement needs a parser")
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
    since: date | None = None,
):
    """Ask the bank about this tournament's own window and credit what it says.

    The window is `setup.bank_poll_window` — from the day registration opened
    to the day the tournament is held. It used to be a rolling fortnight, and a
    fortnight is the wrong question for a poll an organizer presses: pointed at
    a tournament whose window has passed it asked about days in which nothing
    could have been paid, found nothing, and said so.

    `since` moves the window's start later, and exists for exactly one caller:
    the console, answering the bank's history lock. Fio serves the last ninety
    days unasked and refuses the rest, so an organizer who will not authorize
    the whole history can still ask for the part of the window that lies inside
    it. It never widens the window — the days before registration opened are
    not this tournament's under any authorization — and it never silently
    empties it: a start past the window's end is refused rather than answered
    with a poll of nothing.
    """
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    _refuse_while_duplicates_pending(session, tournament)
    if not tournament.fio_token:
        raise HTTPException(status_code=409, detail="fio_token_not_configured")
    # today as the UTC day, not the process's: an operational boundary with
    # nobody's calendar behind it (design unify-day-boundary-clocks D1)
    date_from, date_to = setup.bank_poll_window(tournament, datetime.now(UTC).date())
    if since is not None:
        date_from = max(date_from, since)
    if date_from > date_to:
        # the shortened window and the tournament's do not overlap: no day of
        # it could hold a payment, and answering "nothing found" would say the
        # bank was asked
        raise HTTPException(
            status_code=409,
            detail={"code": "poll_window_empty", "window_to": date_to.isoformat()},
        )
    try:
        transactions = fio.fetch(tournament.fio_token, date_from, date_to)
    except bank.FioAuthorizationRequired as refusal:
        # not an error to report as one: the window is right, the token is
        # good, and the organizer can open the history themselves. The bank's
        # own date and the window travel together, because what the console has
        # to offer depends on whether they overlap at all
        raise HTTPException(
            status_code=409,
            detail={
                "code": "fio_authorization_required",
                "since": refusal.since.isoformat(),
                "window_from": date_from.isoformat(),
                "window_to": date_to.isoformat(),
            },
        ) from refusal
    except bank.FioUnreachable as failure:
        raise HTTPException(status_code=502, detail={"code": "fio_unreachable"}) from failure
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
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    demoted = scheduler.settle_seating_if_due(session, tournament, datetime.now(UTC))
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
    require_published(tournament)
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


def _proposal(session, tournament, transaction_id: int) -> BankTransaction:
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if transaction.status != nameresolve.LIKELY:
        raise HTTPException(status_code=409, detail="not_a_proposal")
    return transaction


@router.post("/likely/{transaction_id}/confirm", status_code=201)
def confirm_proposal(
    transaction_id: RowId,
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
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    transaction = _proposal(session, tournament, transaction_id)
    registration = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == transaction.proposed_fencer_id,
            Registration.state == RegistrationState.RESERVED,
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
    transaction_id: RowId,
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
    require_published(tournament)
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
    transaction_id: RowId,
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
                Registration.state == RegistrationState.RESERVED,
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
    return TransactionRosterOut(transaction_id=transaction.id, query=query, fencers=fencers)


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
            out.settled_by_hand_reason = registration.waiver_reason
            recorded = session.scalars(
                select(ManualPayment)
                .where(
                    ManualPayment.registration_id == registration.id,
                    ManualPayment.removed_at.is_(None),
                )
                .order_by(ManualPayment.id.desc())
            ).first()
            if recorded is not None:
                out.settled_by_recorded_payment = _manual_payment_out(session, tournament, recorded)
    if transaction.status == "unmatched":
        out.candidate_vs = matching.detect_candidates(session, transaction)
    if transaction.proposed_fencer is not None:
        out.proposed_fencer_name = transaction.proposed_fencer.display_name
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
    require_published(tournament)
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
    require_published(tournament)
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
    # built by comprehension rather than `dict(rows)`: the `is_not(None)` above
    # already excluded a null registration id, and this is what says so
    expired_at = {
        registration_id: at for registration_id, at in rows if registration_id is not None
    }
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
            credited_amount=_cents_to_amount(registration.credited_in("local")),
            credited_eur_amount=(
                _cents_to_amount(registration.credited_in("eur"))
                if registration.credited_in("eur")
                else None
            ),
            expired_at=expired_at[registration.id],
        )
        for registration in registrations
        if registration.credited_in("local") or registration.credited_in("eur")
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
    transaction_id: RowId,
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
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    transaction = _flagged_transaction(session, tournament, transaction_id)
    registration = _flagged_registration(session, tournament, transaction)
    if registration is None or registration.state != RegistrationState.EXPIRED:
        raise HTTPException(status_code=409, detail="not_reinstatable")
    if not matching.seats_free(session, registration):
        raise HTTPException(status_code=409, detail="capacity_unavailable")

    # the reservation comes back to life; whether it then reads as paid is the
    # credit below and the derivation over it, not a state assigned here
    registration.state = RegistrationState.RESERVED
    currency = matching.transaction_currency(transaction, tournament)
    if matching.match_currency(transaction, tournament) is not None and currency is not None:
        ledger.credit(
            session,
            tournament,
            registration,
            amount_cents=transaction.amount_cents,
            currency=currency,
            # the transaction's own day, like any other credit; the day the
            # registration became paid is derived from it
            value_date=transaction.date,
            source_kind=CreditSource.BANK_TRANSACTION,
            source_id=transaction.id,
            origin=CreditOrigin.REINSTATE,
        )
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


def _reversal_preview(
    session, tournament: Tournament, transaction: BankTransaction
) -> CreditReversalOut:
    """What reversing this transaction's credits would leave behind, asked of
    the journal rather than guessed from the transaction's amount: one
    transaction may have covered several registrations with different amounts,
    and each of them is its own entry."""
    rows = []
    for entry in ledger.credits_of_source(
        session, tournament, CreditSource.BANK_TRANSACTION, transaction.id
    ):
        registration = entry.registration
        # the settled state this registration would be left with, asked by
        # taking the entry out of the sum rather than by writing anything
        remaining = registration.credited_in(registration.paid_lane) - entry.amount_cents
        rows.append(
            CreditReversalRow(
                registration_id=registration.id,
                fencer_name=registration.fencer.display_name,
                vs=registration.vs,
                amount=_cents_to_amount(entry.amount_cents),
                currency=entry.currency,
                unsettles=registration.settled and not registration.waived and remaining <= 0,
            )
        )
    return CreditReversalOut(transaction_id=transaction.id, registrations=rows)


def _credit_rows(session, tournament: Tournament, credits: list[PaymentCredit]) -> list:
    """Who a payment credited and how much each of them got, with whether that
    registration stops reading as paid once the credit is gone.

    The same rows the reversal preflight builds, from entries already in hand:
    the table states what it holds without a request per line, and reversing is
    still confirmed against a preflight asked at the moment it is done, because
    whether a registration reads as paid is a derivation and a listing can be
    older than the answer."""
    rows = []
    for entry in credits:
        registration = entry.registration
        remaining = registration.credited_in(registration.paid_lane) - entry.amount_cents
        rows.append(
            CreditReversalRow(
                registration_id=registration.id,
                fencer_name=registration.fencer.display_name,
                vs=registration.vs,
                amount=_cents_to_amount(entry.amount_cents),
                currency=entry.currency,
                unsettles=registration.settled and not registration.waived and remaining <= 0,
            )
        )
    return rows


@router.get("/credited", response_model=list[CreditedPaymentOut])
def credited_payments(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Every payment holding a live credit, newest first — the bank's and the
    hand-recorded together.

    One table where the console had three. A transaction the matcher resolved
    sits in no resolution queue, a pairing an organizer drew was listed under
    the rule that decided it, and a cash payment somebody entered had a view of
    its own; all three are the same fact, and answering it in three places meant
    the pairing view and the credited view listing overlapping rows under
    different keys while a pairing that credited nothing appeared as a result.

    Asked of the journal and not of `matched_registration_id` or of status: what
    a payment credited is what its live entries say, and one payment may have
    credited several registrations (design D1).
    """
    require_console_access(session, tournament, fencer)
    entries = session.scalars(
        select(PaymentCredit)
        .where(
            PaymentCredit.tournament_id == tournament.id,
            PaymentCredit.reversed_at.is_(None),
        )
        .order_by(PaymentCredit.id)
    ).all()
    if not entries:
        return []

    # grouped by what carried the money, which is how the journal names it
    grouped: dict[tuple[CreditSource, int], list[PaymentCredit]] = {}
    for entry in entries:
        grouped.setdefault((entry.source_kind, entry.source_id), []).append(entry)

    transactions = {
        transaction.id: transaction
        for transaction in session.scalars(
            select(BankTransaction).where(
                BankTransaction.tournament_id == tournament.id,
                BankTransaction.id.in_(
                    [
                        source_id
                        for kind, source_id in grouped
                        if kind == CreditSource.BANK_TRANSACTION
                    ]
                ),
            )
        )
    }
    recorded = {
        payment.id: payment
        for payment in session.scalars(
            select(ManualPayment).where(
                ManualPayment.tournament_id == tournament.id,
                ManualPayment.id.in_(
                    [
                        source_id
                        for kind, source_id in grouped
                        if kind == CreditSource.MANUAL_PAYMENT
                    ]
                ),
            )
        )
    }

    rows = []
    for (kind, source_id), credits in grouped.items():
        newest = credits[-1]
        common = CreditedPaymentOut(
            source_kind=kind,
            source_id=source_id,
            value_date=newest.value_date,
            # what the payment itself was, which a share of it credited
            amount=_cents_to_amount(sum(entry.amount_cents for entry in credits)),
            currency=newest.currency,
            origin=newest.origin,
            credits=_credit_rows(session, tournament, credits),
        )
        if kind == CreditSource.BANK_TRANSACTION:
            transaction = transactions.get(source_id)
            if transaction is None:
                # the statement was cleared from under a credit nobody reversed.
                # The row still states the money, which is the thing that is
                # true; `payments-clearing` refuses this, so it is not reachable
                # by any console action
                rows.append(common)
                continue
            common.amount = _cents_to_amount(transaction.amount_cents)
            common.currency = Currency(transaction.currency)
            common.payer_name = transaction.payer_name
            common.message = transaction.message
        else:
            payment = recorded.get(source_id)
            if payment is not None:
                common.amount = _cents_to_amount(payment.amount_cents)
                common.currency = payment.currency
                common.recorded_by = payment.recorded_by
                common.method = payment.method
                common.note = payment.note
        rows.append(common)

    rows.sort(key=lambda row: (row.value_date, row.source_id), reverse=True)
    return rows


@router.get("/uncredited", response_model=list[UncreditedPaymentOut])
def uncredited_payments(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Every payment that arrived and lies on nobody, oldest first.

    One table where the console had three — proposals, unresolved money, and the
    money a check refused — because all three are one question with the answer
    to a second question written beside it. Which table a payment belongs to is
    the journal's answer; what is to be done with it is what status is genuinely
    good for, and that is the `disposition` each row carries.

    The queues this replaces filtered on status, which is why a pairing that
    credited nothing fell out of all of them: `apply_payment_links` marks such a
    transaction `matched` though no money moved. Asked of the journal it is
    uncredited money, and it leaves this table by itself once a credit exists
    (design D1).
    """
    require_console_access(session, tournament, fencer)
    live_credit = (
        select(PaymentCredit.id)
        .where(
            PaymentCredit.tournament_id == tournament.id,
            PaymentCredit.source_kind == CreditSource.BANK_TRANSACTION,
            PaymentCredit.source_id == BankTransaction.id,
            PaymentCredit.reversed_at.is_(None),
        )
        .exists()
    )
    transactions = session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.tournament_id == tournament.id,
            ~live_credit,
            # money belonging to a sibling tournament on the same bank account.
            # Uncredited here and never to be credited here: its own console
            # will match it, which is what the phase already tells the
            # organizer in as many words (design Decision 5). The one place the
            # journal's answer is not the whole test — "lies on nobody" is not
            # the same as "is this tournament's to resolve"
            BankTransaction.status != "other_tournament",
        )
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
    if not transactions:
        return []

    # the pairings that named a registration and reached nothing. Read once for
    # the whole table rather than per row: a rule names its transaction by
    # external id, so the lookup is by that
    paired: dict[str, list[PairedRegistrationOut]] = {}
    for rule in rules.active_rules(session, tournament, kind="payment_link"):
        registrations = matching.linked_registrations(session, tournament, rule.payload or {})
        named = [
            PairedRegistrationOut(
                registration_id=registration.id,
                fencer_name=registration.fencer.display_name,
                vs=registration.vs,
            )
            for registration in registrations
            if registration.fencer is not None
        ]
        if named:
            paired.setdefault(rule.target, []).extend(named)

    rows = []
    for transaction in transactions:
        base = _transaction_out(session, tournament, transaction)
        pairing = paired.get(f"txn:{transaction.external_id}", [])
        if transaction.status == nameresolve.LIKELY and transaction.proposed_fencer is not None:
            disposition = "proposal"
        elif pairing:
            disposition = "paired_uncredited"
        elif transaction.status == "flagged":
            disposition = "refused"
        else:
            disposition = "none"
        out = UncreditedPaymentOut(
            **base.model_dump(),
            disposition=disposition,
            paired_registrations=pairing,
        )
        if disposition == "proposal":
            proposed = session.scalar(
                select(Registration).where(
                    Registration.tournament_id == tournament.id,
                    Registration.fencer_id == transaction.proposed_fencer_id,
                    Registration.state == RegistrationState.RESERVED,
                )
            )
            if proposed is not None:
                out.proposed_outstanding = _cents_to_amount(proposed.balance_cents(tournament)[0])
        rows.append(out)
    return rows


@router.get("/transactions/{transaction_id}/reversal", response_model=CreditReversalOut)
def reversal_preflight(
    transaction_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """What reversing this transaction's credits would do, before it is done."""
    require_console_access(session, tournament, fencer)
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    return _reversal_preview(session, tournament, transaction)


@router.post("/transactions/{transaction_id}/reverse", response_model=TransactionOut)
def reverse_transaction_credit(
    transaction_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """Release the credit a transaction made and return it to the unmatched
    queue.

    The operation that was missing. A payment link and a payment recorded by
    hand can each already be taken back; a transaction an automatic match
    credited could not, which is why the only route out was a blanket clear —
    and the clear refuses precisely while such a credit stands (spec
    payments-clearing). Every credited transaction now has a way out.

    What each registration reads afterwards is a derivation and is not restored
    here; there is no second state to get wrong.
    """
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    reversed_entries = ledger.reverse_for_source(
        session,
        tournament,
        CreditSource.BANK_TRANSACTION,
        transaction.id,
        by=ledger.actor_label(fencer),
        reason="credit reversed by organizer",
    )
    if not reversed_entries:
        raise HTTPException(status_code=409, detail="no_live_credit")

    transaction.status = "unmatched"
    transaction.status_reason = "credit_reversed"
    transaction.matched_registration_id = None
    for entry in reversed_entries:
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=entry.registration_id,
                transaction_id=transaction.id,
                kind="credit_reversed",
                detail=(
                    f"transaction {transaction.id}: {entry.registration.audit_label},"
                    f" {entry.amount_cents} cents {entry.currency} reversed"
                    f" by {ledger.actor_label(fencer)}"
                ),
            )
        )
    session.commit()
    return transaction


@router.post("/transactions/{transaction_id}/mark-for-refund", response_model=TransactionOut)
def mark_transaction_for_refund(
    transaction_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    bank.require_payments_enabled(tournament)
    transaction = _flagged_transaction(session, tournament, transaction_id)
    registration = _flagged_registration(session, tournament, transaction)
    which = matching.match_currency(transaction, tournament)
    currency = matching.transaction_currency(transaction, tournament)
    if registration is not None and which is not None and currency is not None:
        ledger.credit(
            session,
            tournament,
            registration,
            amount_cents=transaction.amount_cents,
            currency=currency,
            value_date=transaction.date,
            source_kind=CreditSource.BANK_TRANSACTION,
            source_id=transaction.id,
            origin=CreditOrigin.REFUND_HOLD,
        )
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
    credited = registration.credited_in(which) if which is not None else 0
    total = (
        registration.total_amount * 100 if which == "local" else (registration.total_eur or 0) * 100
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
            registration.settled and which is not None and credited - payment.amount_cents < total
        ),
    )


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
    require_published(tournament)
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
    if registration.state is not RegistrationState.RESERVED:
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
    payment_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """Reverse a recorded payment. A soft delete, so the wrong entry and its
    reversal both survive — and there is no edit endpoint for the same reason:
    a correction is a removal and a new record, so that what was credited and
    what took it back are both readable afterwards."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
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
