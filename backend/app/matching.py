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

from app import bank, emails
from app import rules as rules_engine
from app.availability import taken_seats
from app.mail import Mailer
from app.models import (
    BankTransaction,
    Currency,
    Fencer,
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
    """Detected VS values that actually resolve to an issued registration
    somewhere in the deployment — what the manual dialog pre-fills for an
    unmatched transaction (design Decisions 5 and 6)."""
    tokens = detected_vs_tokens(transaction)
    if not tokens:
        return []
    issued = set(session.scalars(select(Registration.vs).where(Registration.vs.in_(tokens))))
    return [vs for vs in tokens if vs in issued]


def _event(session: Session, transaction: BankTransaction, kind: str, detail: str,
           registration: Registration | None = None) -> None:
    session.add(
        PaymentEvent(
            tournament_id=transaction.tournament_id,
            registration_id=registration.id if registration else None,
            transaction_id=transaction.id,
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
    currency lane — not of a shrinking remainder, which would tighten with
    every partial payment already credited."""
    total = registration.total_amount if which == "local" else (registration.total_eur or 0)
    return total * 100 * tournament.amount_tolerance_percent / 100


def _credit(registration: Registration, which: MatchCurrency, amount_cents: int) -> None:
    if which == "local":
        registration.amount_paid_cents += amount_cents
    else:
        registration.amount_paid_eur_cents += amount_cents


def _apply_deposit_threshold(
    session: Session,
    tournament: Tournament,
    transaction: BankTransaction,
    registration: Registration,
    which: MatchCurrency,
    vs: int,
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
        deposit, credited = tournament.deposit_amount, registration.amount_paid_cents
    else:
        deposit, credited = tournament.deposit_amount_eur, registration.amount_paid_eur_cents
    if deposit is None or credited < deposit * 100:
        return
    registration.expires_at = None
    _event(
        session, transaction, "deposit_settled",
        f"VS {vs}: deposit of {deposit} reached, payment window closed",
        registration,
    )


def _settle(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    transaction: BankTransaction,
    registration: Registration,
    which: MatchCurrency,
    vs: int,
    amount_cents: int,
    *,
    reinstated: bool = False,
) -> MatchOutcome:
    """Decide the registration's resulting state from `which`'s outstanding
    balance, after that lane has already been credited (Decision 1), and send
    exactly the notification the outcome calls for."""
    remaining = (
        registration.outstanding_cents
        if which == "local"
        else registration.outstanding_eur_cents
    )
    tolerance = _tolerance_cents(registration, tournament, which)
    currency_code = tournament.local_currency if which == "local" else Currency.EUR

    if remaining > tolerance:
        _event(
            session, transaction, "partial_payment",
            f"VS {vs}: {amount_cents} cents {currency_code}, {remaining} cents still outstanding",
            registration,
        )
        _apply_deposit_threshold(session, tournament, transaction, registration, which, vs)
        session.flush()
        emails.send_partial_payment_received(
            mailer, tournament, registration.fencer, registration, which
        )
        return "partial"

    registration.state = RegistrationState.PAID
    registration.paid_at = datetime.now(UTC)
    overpaid = remaining < -tolerance
    if overpaid:
        registration.refund_state = RefundState.PENDING
        _event(
            session, transaction, "overpayment",
            f"VS {vs}: {amount_cents} cents {currency_code}, {-remaining} cents over", registration,
        )
    else:
        _event(
            session, transaction, "payment_matched",
            f"VS {vs}: {amount_cents} cents {currency_code}", registration,
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
    return {r.vs: r for r in found}


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


def match_new_transactions(
    session: Session, tournament: Tournament, mailer: Mailer
) -> MatchResult:
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
        _finish(transaction, "unmatched", "no_vs")
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
                session, transaction, "reinstated_in_grace",
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
                session, transaction, "match_conflict",
                f"VS {vs}: registration expired ({reason})", registration,
            )
            result.flagged += 1
            session.flush()
            emails.send_payment_after_expiry(
                mailer, tournament, registration.fencer, registration
            )
            return
    elif registration.state != RegistrationState.RESERVED:
        _finish(transaction, "flagged", f"registration_{registration.state.value}")
        _event(
            session, transaction, "match_conflict",
            f"VS {vs}: registration is {registration.state.value}", registration,
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
            session, transaction, "currency_not_accepted",
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
    _credit(registration, which, paid_cents)
    transaction.matched_registration_id = registration.id
    outcome = _settle(
        session, tournament, mailer, transaction, registration, which, vs, paid_cents,
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
            session, transaction, "currency_not_accepted",
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
        )
    ).all()
    if len(registrations) < 2:
        # fewer than two are actually still payable — not a genuine
        # multi-registration payment; leave it for the organizer, who sees
        # every detected VS as a pre-filled candidate
        _finish(transaction, "unmatched", "multi_vs_incomplete")
        result.unmatched += 1
        return

    due_cents = sum(
        registration.outstanding_cents if which == "local"
        else (registration.outstanding_eur_cents or 0)
        for registration in registrations
    )
    tolerance = due_cents * tournament.amount_tolerance_percent / 100
    if abs(transaction.amount_cents - due_cents) > tolerance:
        _finish(transaction, "unmatched", "multi_vs_amount_mismatch")
        result.unmatched += 1
        return

    actor = _system_actor(session, tournament)
    vs_list = [registration.vs for registration in registrations]
    rules_engine.create_rule(
        session, tournament, actor, phase="payments", kind="payment_link",
        target=f"txn:{transaction.external_id}",
        payload={"vs": vs_list, "auto_created": True},
    )
    _event(
        session, transaction, "multi_vs_link_created",
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


def apply_payment_links(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Re-assert active payment_link rules. Idempotent: an already-matched
    transaction is skipped, so reruns and re-ingestion converge on the same
    state.

    A link distributes the transaction across the registrations it covers —
    each its own outstanding balance in the transaction's own currency lane,
    in VS order, capped by what remains of the transaction (design Decision
    7) — rather than crediting the full amount to every one of them. The
    amount actually credited to each VS is recorded on the rule, so removing
    it later reverts exactly what happened."""
    bank.require_payments_enabled(tournament)
    applied = 0
    for rule in rules_engine.active_rules(session, tournament, kind="payment_link"):
        transaction = _transaction_by_external_id(
            session, tournament, rule.target.removeprefix("txn:")
        )
        if transaction is None or transaction.status == "matched":
            continue
        registrations = [
            session.scalar(
                select(Registration).where(
                    Registration.tournament_id == tournament.id, Registration.vs == vs
                )
            )
            for vs in rule.payload.get("vs", [])
        ]
        registrations = [r for r in registrations if r is not None]
        which = match_currency(transaction, tournament)
        remaining = transaction.amount_cents
        credited: dict[str, int] = {}
        for registration in registrations:
            if which is None or remaining <= 0 or registration.state != RegistrationState.RESERVED:
                continue
            due = registration.outstanding_cents if which == "local" else (
                registration.outstanding_eur_cents or 0
            )
            amount = max(0, min(due, remaining))
            if amount <= 0:
                continue
            remaining -= amount
            credited[str(registration.vs)] = amount
            _credit(registration, which, amount)
            _settle(
                session,
                tournament,
                mailer,
                transaction,
                registration,
                which,
                registration.vs,
                amount,
            )
        rule.payload = {**rule.payload, "credited": credited}
        transaction.status = "matched"
        transaction.status_reason = "manual_link"
        transaction.matched_registration_id = (
            registrations[0].id if len(registrations) == 1 else None
        )
        applied += 1
    session.commit()
    return applied


def unapply_payment_link(session: Session, tournament: Tournament, rule) -> None:
    """Revert a deleted payment_link rule: registrations paid solely by it go
    back to reserved, each losing exactly the amount this rule recorded
    having credited it (design Decision 7) — not the full transaction amount,
    and not a recomputed guess against today's balances. The transaction
    returns to the unmatched queue."""
    transaction = _transaction_by_external_id(
        session, tournament, rule.target.removeprefix("txn:")
    )
    if transaction is not None and transaction.status_reason == "manual_link":
        transaction.status = "unmatched"
        transaction.status_reason = "manual_unlink"
        transaction.matched_registration_id = None
    which = match_currency(transaction, tournament) if transaction is not None else None
    credited = rule.payload.get("credited", {})

    still_linked = {
        vs
        for other in rules_engine.active_rules(session, tournament, kind="payment_link")
        for vs in other.payload.get("vs", [])
    }
    for vs in rule.payload.get("vs", []):
        if vs in still_linked:
            continue
        amount = credited.get(str(vs))
        if not amount:
            continue  # this rule never actually credited this VS
        registration = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id, Registration.vs == vs
            )
        )
        if registration is None or registration.state != RegistrationState.PAID:
            continue
        auto_matched = session.scalar(
            select(BankTransaction.id).where(
                BankTransaction.matched_registration_id == registration.id,
                BankTransaction.status_reason == "auto_vs",
            )
        )
        if auto_matched:
            continue
        registration.state = RegistrationState.RESERVED
        registration.paid_at = None
        if which == "local":
            registration.amount_paid_cents -= amount
        elif which == "eur":
            registration.amount_paid_eur_cents -= amount
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                transaction_id=transaction.id if transaction else None,
                kind="manual_link_removed",
                detail=f"rule {rule.id}: VS {vs} back to reserved ({amount} cents)",
            )
        )
    session.commit()
