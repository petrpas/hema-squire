"""Automatic payment matching: strictly VS-first, amount within the
tournament's tolerance. Never by payer name or amount alone.

A transaction is compared against the total denominated in its own currency —
the local total for a local-currency transaction, the EUR total for a EUR one
on a tournament that prices in EUR as a second currency. No conversion ever
happens; a transaction in a currency the tournament does not price in is
flagged as not accepted rather than converted and compared (design D4).

Crediting is credit-first, decide-second (design harden-payment-matching
Decision 1): any VS-matched transaction in an accepted currency is credited
to that currency's counter unconditionally, and the registration's resulting
state — paid, still reserved with a partial balance, or overpaid and routed
to refund tracking — is decided from what that lane's outstanding balance
looks like afterward. The two currency lanes are never summed.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import bank, emails, ledger, nameresolve
from app import rules as rules_engine
from app.availability import taken_seats
from app.mail import Mailer
from app.models import (
    BankTransaction,
    CreditOrigin,
    CreditSource,
    Currency,
    Fencer,
    ManualPayment,
    PaymentEvent,
    PaymentMode,
    RefundState,
    Registration,
    RegistrationState,
    Tournament,
    TournamentOrganizer,
)

# A token explicitly labelled as a variable symbol, wherever in the
# searchable text it appears (design Decision 5, tier 1).
LABELLED_VS = re.compile(r"\bVS[:\s]*(\d{1,10})\b", re.IGNORECASE)
# A bare, unlabelled structured VS is exactly 7 digits (design add-structured-
# vs); the lookaround keeps it from matching inside a longer digit run
# (design Decision 5, tier 2).
BARE_VS = re.compile(r"(?<!\d)\d{7}(?!\d)")

MatchCurrency = Literal["local", "eur"]
MatchOutcome = Literal["paid", "partial", "overpaid"]


class MatchResult(BaseModel):
    matched: int = 0
    flagged: int = 0
    unmatched: int = 0
    # proposed to a fencer by the payer's own words, waiting for a person to
    # confirm. Counted apart from `matched` because nothing has been credited
    # (spec name-assisted-matching)
    likely: int = 0
    # credited but short of the amount due — left reserved, not queued
    # (design Decision 1)
    partial: int = 0
    # transactions whose VS resolved to a different tournament's registration
    # (design Decision 5) — recorded as belonging elsewhere, not queued here
    set_aside: int = 0


def _labelled_vs_values(text: str) -> list[int]:
    return [int(m.group(1)) for m in LABELLED_VS.finditer(text)]


def _bare_vs_values(text: str) -> list[int]:
    return [int(m.group(0)) for m in BARE_VS.finditer(text)]


def effective_vs(transaction: BankTransaction) -> int | None:
    """The transaction's own field, or the first labelled token anywhere in
    its searchable text — never a bare number. Used where a single asserted
    VS is required: an already-flagged transaction being reinstated or marked
    for refund by the organizer. A bare token is an inference gated by amount
    (Decision 5); it never reaches "flagged" on its own, so it has no place
    here."""
    if transaction.vs is not None:
        return transaction.vs
    values = _labelled_vs_values(transaction.searchable_text)
    return values[0] if values else None


def detected_vs_tokens(transaction: BankTransaction) -> list[int]:
    """Every VS-shaped value on a transaction, in priority order — the
    structured field, then labelled tokens, then bare 7-digit ones — each
    appearing once. The organizer-facing candidate list (pre-filling the
    manual dialog) is this list filtered to values that are actually issued."""
    tokens: list[int] = []
    if transaction.vs is not None:
        tokens.append(transaction.vs)
    text = transaction.searchable_text
    for value in _labelled_vs_values(text) + _bare_vs_values(text):
        if value not in tokens:
            tokens.append(value)
    return tokens


def detect_candidates(session: Session, transaction: BankTransaction) -> list[int]:
    """Detected VS values that resolve to a registration **of this tournament**
    — what the manual dialog pre-fills for an unmatched transaction (design
    Decisions 5 and 6).

    Scoped to the tournament because that is what the dialog can act on:
    `POST /payments/link` resolves a typed symbol against this tournament's
    registrations and answers `unknown_vs` for anything else, so a candidate
    from elsewhere in the deployment is a one-click button that fails. It also
    empties the offer on a tournament whose registrations carry no symbol at
    all, which is the whole of the manual mode (`tournament-mode`).
    """
    tokens = detected_vs_tokens(transaction)
    if not tokens:
        return []
    issued = set(
        session.scalars(
            select(Registration.vs).where(
                Registration.tournament_id == transaction.tournament_id,
                Registration.vs.in_(tokens),
            )
        )
    )
    return [vs for vs in tokens if vs in issued]


def _event(
    session: Session,
    transaction: BankTransaction | None,
    kind: str,
    detail: str,
    registration: Registration | None = None,
) -> None:
    """An event with no transaction behind it is a credit an organizer
    recorded by hand; the detail names the `ManualPayment` where the VS would
    otherwise stand, and the tournament comes from the registration, since
    there is nothing else to ask (design add-manual-payment-entry D3)."""
    tournament_id = (
        transaction.tournament_id if transaction is not None else registration.tournament_id  # type: ignore[union-attr]
    )
    session.add(
        PaymentEvent(
            tournament_id=tournament_id,
            registration_id=registration.id if registration else None,
            transaction_id=transaction.id if transaction is not None else None,
            kind=kind,
            detail=detail,
        )
    )


def _finish(transaction: BankTransaction, status: str, reason: str | None = None) -> None:
    transaction.status = status
    transaction.status_reason = reason


def match_currency(transaction: BankTransaction, tournament: Tournament) -> MatchCurrency | None:
    """Which stored total a transaction should be compared against, purely by
    currency identity — never by conversion (design Decision 4). An unset
    transaction currency is trusted as the tournament's local one, matching
    what pre-multi-currency ingestion recorded. None means the tournament
    does not accept that currency at all."""
    currency = (transaction.currency or str(tournament.local_currency)).upper()
    if currency == str(tournament.local_currency):
        return "local"
    if currency == Currency.EUR and tournament.shows_eur:
        return "eur"
    return None


def within_expiry_grace(registration: Registration, tournament: Tournament) -> bool:
    if registration.expires_at is None:
        return False
    # SQLite drops tzinfo on round-trip even for a DateTime(timezone=True)
    # column; every stored instant is UTC (see `_now()` conventions app-wide)
    expires_at = registration.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    deadline = expires_at + timedelta(hours=tournament.expiry_grace_hours)
    return datetime.now(UTC) <= deadline


def seats_free(session: Session, registration: Registration) -> bool:
    """Every seated (non-substitute) discipline on the registration still has a
    free place — the gate that stops grace reinstatement from displacing a
    fencer who has been waiting in the substitute queue."""
    return all(
        taken_seats(session, entry.discipline) < entry.discipline.capacity
        for entry in registration.entries
        if not entry.is_substitute
    )


def _tolerance_cents(
    registration: Registration, tournament: Tournament, which: MatchCurrency
) -> float:
    """Tolerance as a percentage of the registration's stable total in this
    currency lane. Lives on the registration, because the outstanding column
    asks the same question when it decides whether a settled row's leftover
    cents are owed or forgiven."""
    return registration.tolerance_cents(tournament, which)


def transaction_currency(transaction: BankTransaction, tournament: Tournament) -> Currency | None:
    """The currency a transaction actually arrived in, as the enum. An unset
    transaction currency is trusted as the tournament's local one, matching
    what pre-multi-currency ingestion recorded, exactly as `match_currency`
    reads it. None where it is not a currency the deployment knows."""
    raw = (transaction.currency or str(tournament.local_currency)).upper()
    try:
        return Currency(raw)
    except ValueError:
        return None


def _credit(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    transaction: BankTransaction,
    amount_cents: int,
    origin: CreditOrigin,
    *,
    rule_id: int | None = None,
) -> None:
    """Credit a transaction's money to a registration by appending to the
    journal. Idempotent on the transaction: a second pass over money already
    credited writes nothing, whatever state the transaction is in."""
    currency = transaction_currency(transaction, tournament)
    if currency is None:
        return
    ledger.credit(
        session,
        tournament,
        registration,
        amount_cents=amount_cents,
        currency=currency,
        value_date=transaction.date,
        source_kind=CreditSource.BANK_TRANSACTION,
        source_id=transaction.id,
        origin=origin,
        rule_id=rule_id,
    )


def _apply_deposit_threshold(
    session: Session,
    tournament: Tournament,
    transaction: BankTransaction | None,
    registration: Registration,
    which: MatchCurrency,
    origin: str,
) -> None:
    """Reaching the tournament's deposit closes the payment window rather than
    extending it (design add-payment-modes Decision 3).

    `harden-payment-matching` Decision 3 — that a partial payment never extends
    a validity window — stands unmodified: a deposit is a threshold the
    organizer published, not an arbitrary amount the fencer chose, so it cannot
    renew a hold by dribbling money, and the mechanism here is discharge rather
    than extension. Past the deposit the seating deadline is the only remaining
    obligation, so no window may keep running against it. Each currency lane is
    judged against its own deposit figure, never summed, exactly as totals are."""
    if tournament.payment_mode != PaymentMode.DEPOSIT:
        return
    if registration.state != RegistrationState.RESERVED or registration.expires_at is None:
        return
    if which == "local":
        deposit, credited = tournament.deposit_amount, registration.credited_in("local")
    else:
        deposit, credited = tournament.deposit_amount_eur, registration.credited_in("eur")
    if deposit is None or credited < deposit * 100:
        return
    registration.expires_at = None
    _event(
        session,
        transaction,
        "deposit_settled",
        f"{origin}: deposit of {deposit} reached, payment window closed",
        registration,
    )


def _settle(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    transaction: BankTransaction | None,
    registration: Registration,
    which: MatchCurrency,
    origin: str,
    amount_cents: int,
    *,
    reinstated: bool = False,
) -> MatchOutcome:
    """Decide the registration's resulting state from `which`'s outstanding
    balance, after that lane has already been credited (Decision 1), and send
    exactly the notification the outcome calls for.

    The one place that knows what follows a credit — the settle test against
    tolerance, the deposit threshold, the event, the overpayment's refund
    state, and which mail goes out — and so it is reached from both routes
    money takes rather than copied into the second. A payment an organizer
    recorded by hand passes `transaction=None` and names itself in `origin`;
    everything after that is identical, deliberately, down to the mail the
    fencer receives (design add-manual-payment-entry D3).

    `origin` labels the event details: `VS 2501001` where a statement carried
    the money, `recorded payment 7` where a person did.

    It no longer takes the day the money arrived. That day is carried by the
    credit itself, and the day the registration became paid is derived from the
    credit that completed the balance (`ledger.paid_at`) rather than stamped
    here — so the two routes cannot date a registration differently, which is
    what passing the day in was guarding against."""
    remaining = registration.outstanding_in(which)
    tolerance = _tolerance_cents(registration, tournament, which)
    currency_code = tournament.local_currency if which == "local" else Currency.EUR

    if remaining > tolerance:
        _event(
            session,
            transaction,
            "partial_payment",
            f"{origin}: {amount_cents} cents {currency_code}, {remaining} cents still outstanding",
            registration,
        )
        _apply_deposit_threshold(session, tournament, transaction, registration, which, origin)
        session.flush()
        emails.send_partial_payment_received(
            mailer, tournament, registration.fencer, registration, which
        )
        return "partial"

    # Nothing is assigned here. The registration reads as paid because the
    # credit that brought it within tolerance was appended before this was
    # called, and the day it became paid is derived from that credit
    # (`ledger.paid_at`). What remains is what a credit's consequences actually
    # are: the refund state, the event, and the letter.
    overpaid = remaining < -tolerance
    if overpaid:
        registration.refund_state = RefundState.PENDING
        _event(
            session,
            transaction,
            "overpayment",
            f"{origin}: {amount_cents} cents {currency_code}, {-remaining} cents over",
            registration,
        )
    else:
        _event(
            session,
            transaction,
            "payment_matched",
            f"{origin}: {amount_cents} cents {currency_code}",
            registration,
        )
    session.flush()
    if reinstated:
        emails.send_reservation_reinstated(mailer, tournament, registration.fencer, registration)
    else:
        emails.send_payment_received(mailer, tournament, registration.fencer, registration)
    return "overpaid" if overpaid else "paid"


def _resolve_global(session: Session, tokens: list[int]) -> dict[int, Registration]:
    if not tokens:
        return {}
    found = session.scalars(select(Registration).where(Registration.vs.in_(tokens))).all()
    # `IN` never matches NULL, so a row here always carries a symbol; the
    # filter is what says so rather than a new condition
    return {r.vs: r for r in found if r.vs is not None}


def _system_actor(session: Session, tournament: Tournament) -> Fencer:
    """Attribution for a payment_link rule the matcher creates on its own,
    not an organizer (design Decision 6): the tournament owner if one is set,
    otherwise its first console organizer. A tournament reaching a live
    matching pass always has at least one — console access requires it."""
    if tournament.owner is not None:
        return tournament.owner
    organizer = session.scalar(
        select(TournamentOrganizer)
        .where(TournamentOrganizer.tournament_id == tournament.id)
        .order_by(TournamentOrganizer.id)
    )
    if organizer is not None:
        return organizer.fencer
    raise RuntimeError(
        f"tournament {tournament.id} has no organizer to attribute an "
        "automatic payment_link rule to"
    )


def match_new_transactions(session: Session, tournament: Tournament, mailer: Mailer) -> MatchResult:
    """Process transactions the matcher has not yet resolved: newly ingested
    ones (status NULL) and any still flagged, so a transaction flagged before
    the rest of its payment arrived is reconsidered once it does (design
    Decision 2). Transactions in a terminal, organizer-decided state —
    matched, other_tournament, resolved (marked for refund), or already
    unmatched — are never revisited."""
    bank.require_payments_enabled(tournament)
    result = MatchResult()
    candidates = session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.tournament_id == tournament.id,
            or_(BankTransaction.status.is_(None), BankTransaction.status == "flagged"),
        )
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()

    for transaction in candidates:
        transaction.last_evaluated_at = datetime.now(UTC)
        _evaluate_transaction(session, tournament, mailer, transaction, result)

    session.commit()
    return result


def _evaluate_transaction(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    transaction: BankTransaction,
    result: MatchResult,
) -> None:
    tokens = detected_vs_tokens(transaction)
    if not tokens:
        # No symbol quoted — about one payment in ten, and every payment on a
        # tournament whose registrations the organizer keeps. Ask the resolver
        # who the payer's own words name before giving up on it (spec
        # name-assisted-matching, design Decision 7).
        #
        # A proposal moves nothing: the transaction's status becomes `likely`
        # and it names a fencer, while the registration keeps its total, its
        # credited amount and its state. Crediting is by variable symbol alone,
        # and confirming is the organizer supplying the one the payer omitted.
        resolution = nameresolve.resolve(session, tournament, transaction)
        if nameresolve.propose(transaction, resolution):
            result.likely += 1
        else:
            result.unmatched += 1
        return

    issued = _resolve_global(session, tokens)
    # only tokens that are actually issued *to this tournament* count toward
    # "several distinct issued VS" (Decision 6) — a coincidental extra digit
    # run that resolves nowhere, or to a sibling tournament, must not turn an
    # ordinary single match into a bogus multi-registration attempt
    own_tokens = [vs for vs in tokens if vs in issued and issued[vs].tournament_id == tournament.id]
    if len(own_tokens) >= 2:
        _evaluate_multi_vs(session, tournament, mailer, transaction, own_tokens, result)
        return

    resolved = [vs for vs in tokens if vs in issued]
    vs = resolved[0] if resolved else tokens[0]
    is_bare = transaction.vs is None and not _labelled_vs_values(transaction.searchable_text)
    _evaluate_single_vs(session, tournament, mailer, transaction, vs, is_bare, result)


def _evaluate_single_vs(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    transaction: BankTransaction,
    vs: int,
    is_bare: bool,
    result: MatchResult,
) -> None:
    # global lookup by whole value: the prefix is documentation, never
    # routing (design Decision 4) — a mistyped digit must land on nothing
    # rather than on a stranger's registration
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    if registration is None:
        _finish(transaction, "unmatched", "unknown_vs")
        _event(session, transaction, "unknown_vs", f"VS {vs}")
        result.unmatched += 1
        return

    if registration.tournament_id != tournament.id:
        # belongs to a sibling tournament on the same bank account (design
        # Decision 5): recorded and left alone, not this console's problem
        # to solve — no payment, no email, no registration-affecting event
        _finish(transaction, "other_tournament", "belongs_to_other_tournament")
        result.set_aside += 1
        return

    reinstated = False
    if registration.state == RegistrationState.EXPIRED:
        in_grace = within_expiry_grace(registration, tournament)
        if in_grace and seats_free(session, registration):
            registration.state = RegistrationState.RESERVED
            reinstated = True
            _event(
                session,
                transaction,
                "reinstated_in_grace",
                f"VS {vs}: reinstated within {tournament.expiry_grace_hours}h grace",
                registration,
            )
            # falls through to the normal tolerance comparison below; the
            # fencer is told once, combining reinstatement and payment,
            # only once the payment below is actually accepted
        else:
            reason = "expired_outside_grace" if not in_grace else "expired_seat_taken"
            _finish(transaction, "flagged", reason)
            _event(
                session,
                transaction,
                "match_conflict",
                f"VS {vs}: registration expired ({reason})",
                registration,
            )
            result.flagged += 1
            session.flush()
            emails.send_payment_after_expiry(mailer, tournament, registration.fencer, registration)
            return
    elif not _is_payable(registration):
        # a registration already settled — by money, or by a person's word —
        # is flagged rather than credited a second time, so somebody decides
        # whether this is further money or the same money arriving twice
        # (spec payments). Two conditions since the paid state left the enum:
        # such a registration is `reserved` like any other
        reason = "paid" if registration.settled else registration.state.value
        _finish(transaction, "flagged", f"registration_{reason}")
        _event(
            session,
            transaction,
            "match_conflict",
            f"VS {vs}: registration is {registration.state.value}",
            registration,
        )
        result.flagged += 1
        return

    which = match_currency(transaction, tournament)
    due_cents = None
    if which == "local":
        due_cents = registration.outstanding_cents
    elif which == "eur":
        due_cents = registration.outstanding_eur_cents

    if which is None or due_cents is None:
        # either a currency the tournament does not price in, or (rarely)
        # a registration created before EUR pricing applied to it — either
        # way there is nothing to compare the transaction against
        _finish(transaction, "flagged", "currency_not_accepted")
        _event(
            session,
            transaction,
            "currency_not_accepted",
            f"VS {vs}: {transaction.amount_cents} cents in {transaction.currency}, "
            f"tournament accepts {tournament.local_currency}"
            + (" and EUR" if tournament.shows_eur else ""),
            registration,
        )
        result.flagged += 1
        return

    if is_bare:
        # Decision 5: a bare token is an inference, not an assertion — it may
        # credit automatically only when the amount also covers the
        # outstanding balance within tolerance. A shortfall stays uncredited
        # and surfaces only as a pre-filled candidate; a bare token can never
        # itself create a partial payment.
        tolerance = due_cents * tournament.amount_tolerance_percent / 100
        if abs(transaction.amount_cents - due_cents) > tolerance:
            _finish(transaction, "unmatched", "bare_vs_amount_mismatch")
            result.unmatched += 1
            return

    paid_cents = transaction.amount_cents
    _credit(session, tournament, registration, transaction, paid_cents, CreditOrigin.AUTO_VS)
    transaction.matched_registration_id = registration.id
    outcome = _settle(
        session,
        tournament,
        mailer,
        transaction,
        registration,
        which,
        f"VS {vs}",
        paid_cents,
        reinstated=reinstated,
    )
    if outcome == "partial":
        _finish(transaction, "partial", "partial_payment")
        result.partial += 1
    else:
        _finish(transaction, "matched", "auto_vs")
        result.matched += 1


def _evaluate_multi_vs(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    transaction: BankTransaction,
    own_tokens: list[int],
    result: MatchResult,
) -> None:
    """Decision 6: several distinct VS issued to this tournament, found in one
    transaction's text, is a payment covering all of them. Sum their
    outstanding balances in the transaction's own currency lane; within
    tolerance of the transaction, create a payment_link rule and let
    apply_payment_links — called right after this pass in every caller — do
    the actual (distributed) crediting. No subset search: outside tolerance,
    or if fewer than two are actually still reserved, the transaction stays
    unmatched with every detected VS offered as a candidate."""
    which = match_currency(transaction, tournament)
    if which is None:
        _finish(transaction, "flagged", "currency_not_accepted")
        _event(
            session,
            transaction,
            "currency_not_accepted",
            f"multi-VS {own_tokens}: {transaction.amount_cents} cents in {transaction.currency}, "
            f"tournament accepts {tournament.local_currency}"
            + (" and EUR" if tournament.shows_eur else ""),
        )
        result.flagged += 1
        return

    registrations = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.vs.in_(own_tokens),
            Registration.state == RegistrationState.RESERVED,
            # and still owing: a settled registration is `reserved` too now
            ~Registration.settled,
        )
    ).all()
    if len(registrations) < 2:
        # fewer than two are actually still payable — not a genuine
        # multi-registration payment; leave it for the organizer, who sees
        # every detected VS as a pre-filled candidate
        _finish(transaction, "unmatched", "multi_vs_incomplete")
        result.unmatched += 1
        return

    due_cents = sum(registration.outstanding_in(which) for registration in registrations)
    tolerance = due_cents * tournament.amount_tolerance_percent / 100
    if abs(transaction.amount_cents - due_cents) > tolerance:
        _finish(transaction, "unmatched", "multi_vs_amount_mismatch")
        result.unmatched += 1
        return

    actor = _system_actor(session, tournament)
    vs_list = [registration.vs for registration in registrations]
    rules_engine.create_rule(
        session,
        tournament,
        actor,
        phase="payments",
        kind="payment_link",
        target=f"txn:{transaction.external_id}",
        payload={"vs": vs_list, "auto_created": True},
    )
    _event(
        session,
        transaction,
        "multi_vs_link_created",
        f"VS {vs_list}: auto-linked, {transaction.amount_cents} cents {transaction.currency}",
    )
    result.matched += 1


def _transaction_by_external_id(
    session: Session, tournament: Tournament, external_id: str
) -> BankTransaction | None:
    return session.scalar(
        select(BankTransaction).where(
            BankTransaction.tournament_id == tournament.id,
            BankTransaction.external_id == external_id,
        )
    )


def transaction_for_link(
    session: Session, tournament: Tournament, target: str
) -> BankTransaction | None:
    """The transaction a `payment_link` rule's target names.

    The prefix is stripped in one place rather than at each of the three call
    sites that had grown their own `removeprefix`, so what a link's target looks
    like is stated once.
    """
    return _transaction_by_external_id(session, tournament, target.removeprefix("txn:"))


def linked_registrations(
    session: Session, tournament: Tournament, payload: dict
) -> list[Registration]:
    """The registrations one `payment_link` rule covers.

    Addressed two ways, and both are needed. By **variable symbol** where the
    payer quoted one, which is how every rule written before this was recorded.
    By **registration id** where there is no symbol to quote: a registration on
    a tournament whose organizer keeps the roster carries none at all, and an
    organizer resolving a payment whose symbol was mistyped knows the person
    rather than the number (spec name-assisted-matching).

    Order is symbols first, then ids, because a link distributes a payment
    across the registrations it covers in the order they are listed and an
    existing rule must keep distributing it the way it did.
    """
    found: list[Registration] = []
    for vs in payload.get("vs", []):
        registration = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id, Registration.vs == vs
            )
        )
        if registration is not None:
            found.append(registration)
    for registration_id in payload.get("registration_ids", []):
        registration = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id,
                Registration.id == registration_id,
            )
        )
        if registration is not None and registration not in found:
            found.append(registration)
    return found


def _is_payable(registration: Registration) -> bool:
    """Whether a link may credit this registration: still in the reserved
    lifecycle, and not already settled.

    Two conditions where there used to be one. The state alone said both while
    `PAID` lived in the enum; it now says only that the registration has
    neither expired nor been cancelled, and whether it has been paid for is the
    derivation beside it."""
    return registration.state is RegistrationState.RESERVED and not registration.settled


def apply_payment_links(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Re-assert active payment_link rules. Idempotent: an already-matched
    transaction is skipped, so reruns and re-ingestion converge on the same
    state.

    A link distributes the transaction across the registrations it covers —
    each its own outstanding balance in the transaction's own currency lane,
    in VS order, capped by what remains of the transaction (design Decision
    7) — rather than crediting the full amount to every one of them. Each
    amount it credits is a journal entry naming this rule, so withdrawing the
    rule reverses exactly the entries it wrote."""
    bank.require_payments_enabled(tournament)
    applied = 0
    for rule in rules_engine.active_rules(session, tournament, kind="payment_link"):
        transaction = transaction_for_link(session, tournament, rule.target)
        if transaction is None or transaction.status == "matched":
            continue
        registrations = linked_registrations(session, tournament, rule.payload)
        which = match_currency(transaction, tournament)
        remaining = transaction.amount_cents
        for registration in registrations:
            if which is None or remaining <= 0 or not _is_payable(registration):
                continue
            due = registration.outstanding_in(which)
            amount = max(0, min(due, remaining))
            if amount <= 0:
                continue
            remaining -= amount
            _credit(
                session,
                tournament,
                registration,
                transaction,
                amount,
                CreditOrigin.PAYMENT_LINK,
                rule_id=rule.id,
            )
            _settle(
                session,
                tournament,
                mailer,
                transaction,
                registration,
                which,
                f"VS {registration.vs}",
                amount,
            )
        transaction.status = "matched"
        transaction.status_reason = "manual_link"
        transaction.matched_registration_id = (
            registrations[0].id if len(registrations) == 1 else None
        )
        applied += 1
    session.commit()
    return applied


def unapply_payment_link(session: Session, tournament: Tournament, rule, actor: str) -> None:
    """Revert a withdrawn payment_link rule: every live credit it wrote is
    reversed, each losing exactly the amount that entry recorded — not the full
    transaction amount, and not a recomputed guess against today's balances.
    The transaction returns to the unmatched queue.

    **Unconditional.** The version this replaces skipped a registration that
    was no longer paid, or that a transaction had also matched automatically,
    which left the credit standing in a counter while deleting the rule that
    was its only record. There is nothing to decide here now: the entries name
    this rule, and what each registration reads afterwards is a derivation that
    re-answers itself. A registration another live rule also covers keeps that
    rule's own entries, which this reversal never touches.
    """
    transaction = transaction_for_link(session, tournament, rule.target)
    if transaction is not None and transaction.status_reason == "manual_link":
        transaction.status = "unmatched"
        transaction.status_reason = "manual_unlink"
        transaction.matched_registration_id = None

    reversed_entries = ledger.reverse_for_rule(
        session, rule.id, by=actor, reason=f"payment link {rule.id} withdrawn"
    )
    for entry in reversed_entries:
        registration = entry.registration
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                transaction_id=transaction.id if transaction else None,
                kind="manual_link_removed",
                detail=(
                    f"rule {rule.id}: {registration.audit_label} "
                    f"({entry.amount_cents} cents {entry.currency})"
                ),
            )
        )
    session.commit()


def manual_payment_currency(payment: ManualPayment, tournament: Tournament) -> MatchCurrency | None:
    """Which lane a recorded payment credits, by currency identity alone — the
    same question `match_currency` answers of a transaction, asked of a record
    a person made."""
    if payment.currency == tournament.local_currency:
        return "local"
    if payment.currency == Currency.EUR and tournament.shows_eur:
        return "eur"
    return None


def credit_manual_payment(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    registration: Registration,
    payment: ManualPayment,
    which: MatchCurrency,
) -> MatchOutcome:
    """Credit a payment the organizer recorded, and let every consequence of a
    credit follow identically — the settle test against the same tolerance, the
    deposit threshold and the window it closes, the payment event, the
    overpayment's refund state, and the mail the fencer receives.

    Tolerance applies unchanged. A hand-typed figure needs no allowance for
    bank rounding, but tolerance here is what decides settled versus partial,
    and a registration must not be settled by one route and left partial by the
    other at the same number (design add-manual-payment-entry D3)."""
    ledger.credit(
        session,
        tournament,
        registration,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        value_date=payment.received_on,
        source_kind=CreditSource.MANUAL_PAYMENT,
        source_id=payment.id,
        origin=CreditOrigin.RECORDED,
    )
    return _settle(
        session,
        tournament,
        mailer,
        None,
        registration,
        which,
        f"recorded payment {payment.id}",
        payment.amount_cents,
    )


def uncredit_manual_payment(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    payment: ManualPayment,
    which: MatchCurrency,
) -> None:
    """Reverse a recorded payment: subtract **the record's own amount**, never
    a figure derived from today's balance — the same discipline
    `unapply_payment_link` keeps, and for the same reason. A total amended
    upward since the payment was recorded would otherwise take back more than
    ever went in.

    Whether the registration still reads as paid afterwards is not decided
    here and never was a second thing to get right: it is derived from what its
    remaining credits cover. Where it is still covered — by a transaction, or
    by a second recorded payment — it stays paid, and where it was never paid
    there is nothing to return."""
    ledger.reverse_for_source(
        session,
        tournament,
        CreditSource.MANUAL_PAYMENT,
        payment.id,
        by=payment.recorded_by,
        reason="recorded payment removed",
    )
    _event(
        session,
        None,
        "manual_payment_removed",
        f"recorded payment {payment.id}: {registration.audit_label},"
        f" {payment.amount_cents} cents {payment.currency} reversed",
        registration,
    )


def _settles_now(transaction: BankTransaction, tournament: Tournament) -> Registration | None:
    """The registration a `partial` transaction would settle under the
    tournament's tolerance as it stands now, or None where it would not.

    The test is `_settle`'s own — `remaining > tolerance` against
    `_tolerance_cents` — asked again rather than restated, so a change to what
    "close enough" means reaches this and the live matching pass together.

    Only a reservation still owing money qualifies. A registration that has
    since been paid by other means, expired or been demoted is not waiting on
    a tolerance, and re-deciding it here would overwrite an answer something
    else already gave.

    **`matched_registration_id` is what keeps uncredited money out**, not the
    `partial` filter on the query above it. A transaction the tolerance refused
    before crediting — a bare token with the wrong amount, say — is finished
    before `_evaluate_transaction` names a registration on it, so it has none to
    settle and cannot be reached from here however the query is widened. The
    filter narrows the work; this guard is what makes the narrowing true."""
    if transaction.matched_registration_id is None:
        return None
    registration = transaction.matched_registration
    if registration is None or registration.state is not RegistrationState.RESERVED:
        return None
    if registration.waived:
        return None
    which = match_currency(transaction, tournament)
    if which is None:
        return None
    remaining = registration.outstanding_in(which)
    # **The tolerance must be what makes the difference.** A registration whose
    # credits cover the price outright was settled by money and not by a
    # percentage, and re-deciding it here would resolve a transaction and post
    # a second letter for something nothing was waiting on.
    #
    # This test used to be spelled `state != PAID`, which said the same thing
    # while the paid state was stored: money covering the price wrote it, and
    # such a registration never reached here. Since the state became a
    # derivation it turns true the instant the tolerance is widened — so asking
    # it here would exclude precisely the rows this pass exists for.
    if remaining <= 0:
        return None
    if remaining > _tolerance_cents(registration, tournament, which):
        return None
    return registration


def _partial_transactions(session: Session, tournament: Tournament) -> list[BankTransaction]:
    return list(
        session.scalars(
            select(BankTransaction)
            .where(
                BankTransaction.tournament_id == tournament.id,
                BankTransaction.status == "partial",
            )
            .order_by(BankTransaction.date, BankTransaction.id)
        ).all()
    )


def resettleable(session: Session, tournament: Tournament) -> int:
    """How many short payments the tolerance as it stands would now let
    through, so the console can state the number before the organizer commits
    to it rather than report it afterwards."""
    return sum(
        1
        for transaction in _partial_transactions(session, tournament)
        if _settles_now(transaction, tournament) is not None
    )


def resettle_within_tolerance(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Re-decide the short payments a widened tolerance now covers.

    **No money moves, and nothing is assigned.** These transactions were
    credited when they arrived — `_evaluate_transaction` credits before
    `_settle` decides — and what was left open was only the verdict on whether
    the amount was close enough. That verdict is now a derivation, so this pass
    writes no state at all: it resolves the transaction, records the event and
    sends the letter, and the registrations it names read as paid because the
    tolerance they are judged against moved. It credits nothing, it touches no
    transaction the tolerance did not decide, and it never reaches a payment
    nobody has looked at.

    **It only ever loosens.** A tightened tolerance leaves what is already
    settled alone. Symmetry would say a registration outside the new tolerance
    should go back to owing money, but Squire has told that fencer they are
    paid, by mail; taking it back is not something a percentage field does on
    its own (spec `payments`, Re-deciding a short payment).

    Returns how many registrations were settled."""
    bank.require_payments_enabled(tournament)
    settled = 0
    for transaction in _partial_transactions(session, tournament):
        registration = _settles_now(transaction, tournament)
        if registration is None:
            continue
        # nothing is assigned. The registration was credited when the money
        # arrived, and the widened tolerance changes only the answer the
        # derivation gives about it — including the day it became paid, which
        # is the day of that credit rather than the day the organizer widened
        # anything (design paid-at-is-value-date D4, now falling out of
        # `ledger.paid_at` instead of needing a rule of its own)
        transaction.status = "matched"
        transaction.status_reason = "tolerance_widened"
        _event(
            session,
            transaction,
            "payment_matched",
            f"tolerance {tournament.amount_tolerance_percent}%: "
            f"{registration.audit_label} settled short",
            registration,
        )
        session.flush()
        emails.send_payment_received(mailer, tournament, registration.fencer, registration)
        settled += 1
    session.commit()
    return settled
