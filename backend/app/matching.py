"""Automatic payment matching: strictly VS-first, amount within the
tournament's tolerance. Never by payer name or amount alone.

A transaction is compared against the total denominated in its own currency —
the local total for a local-currency transaction, the EUR total for a EUR one
on a tournament that prices in EUR as a second currency. No conversion ever
happens; a transaction in a currency the tournament does not price in is
flagged as not accepted rather than converted and compared (design D4).
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import emails
from app import rules as rules_engine
from app.availability import taken_seats
from app.mail import Mailer
from app.models import (
    BankTransaction,
    Currency,
    PaymentEvent,
    Registration,
    RegistrationState,
    Tournament,
)

# SEPA and other transfers without a VS field carry it in the message text.
VS_IN_MESSAGE = re.compile(r"\bVS[:\s]*(\d{1,10})\b", re.IGNORECASE)

MatchCurrency = Literal["local", "eur"]


class MatchResult(BaseModel):
    matched: int = 0
    flagged: int = 0
    unmatched: int = 0
    # transactions whose VS resolved to a different tournament's registration
    # (design Decision 5) — recorded as belonging elsewhere, not queued here
    set_aside: int = 0


def effective_vs(transaction: BankTransaction) -> int | None:
    if transaction.vs is not None:
        return transaction.vs
    if transaction.message:
        found = VS_IN_MESSAGE.search(transaction.message)
        if found:
            return int(found.group(1))
    return None


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


def match_new_transactions(
    session: Session, tournament: Tournament, mailer: Mailer
) -> MatchResult:
    """Process transactions the matcher has not seen yet (status is NULL)."""
    result = MatchResult()
    pending = session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.tournament_id == tournament.id,
            BankTransaction.status.is_(None),
        )
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()

    for transaction in pending:
        vs = effective_vs(transaction)
        if vs is None:
            _finish(transaction, "unmatched", "no_vs")
            result.unmatched += 1
            continue

        # global lookup by whole value: the prefix is documentation, never
        # routing (design Decision 4) — a mistyped digit must land on nothing
        # rather than on a stranger's registration
        registration = session.scalar(
            select(Registration).where(Registration.vs == vs)
        )
        if registration is None:
            _finish(transaction, "unmatched", "unknown_vs")
            _event(session, transaction, "unknown_vs", f"VS {vs}")
            result.unmatched += 1
            continue

        if registration.tournament_id != tournament.id:
            # belongs to a sibling tournament on the same bank account (design
            # Decision 5): recorded and left alone, not this console's problem
            # to solve — no payment, no email, no registration-affecting event
            _finish(transaction, "other_tournament", "belongs_to_other_tournament")
            result.set_aside += 1
            continue

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
                continue
        elif registration.state != RegistrationState.RESERVED:
            _finish(transaction, "flagged", f"registration_{registration.state.value}")
            _event(
                session, transaction, "match_conflict",
                f"VS {vs}: registration is {registration.state.value}", registration,
            )
            result.flagged += 1
            continue

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
            continue

        paid_cents = transaction.amount_cents
        tolerance = due_cents * tournament.amount_tolerance_percent / 100
        if abs(paid_cents - due_cents) > tolerance:
            _finish(transaction, "flagged", "amount_out_of_tolerance")
            _event(
                session, transaction, "amount_mismatch",
                f"VS {vs}: paid {paid_cents} of {due_cents} cents ({which})",
                registration,
            )
            result.flagged += 1
            continue

        registration.state = RegistrationState.PAID
        registration.paid_at = datetime.now(UTC)
        if which == "local":
            registration.amount_paid_cents += paid_cents
        else:
            registration.amount_paid_eur_cents += paid_cents
        transaction.matched_registration_id = registration.id
        _finish(transaction, "matched", "auto_vs")
        # the audit records the amount and the currency it was credited in
        currency_code = tournament.local_currency if which == "local" else Currency.EUR
        _event(
            session, transaction, "payment_matched",
            f"VS {vs}: {paid_cents} cents {currency_code}", registration,
        )
        result.matched += 1
        session.flush()
        if reinstated:
            emails.send_reservation_reinstated(mailer, tournament, registration.fencer, registration)
        else:
            emails.send_payment_received(mailer, tournament, registration.fencer, registration)

    session.commit()
    return result


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
    transaction is skipped, so reruns and re-ingestion converge on the same state."""
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
        for registration in registrations:
            if registration.state != RegistrationState.RESERVED:
                continue
            registration.state = RegistrationState.PAID
            registration.paid_at = datetime.now(UTC)
            detail = f"manual link (rule {rule.id}): VS {registration.vs}"
            if which == "local":
                registration.amount_paid_cents += transaction.amount_cents
                detail += f" = {transaction.amount_cents} cents {tournament.local_currency}"
            elif which == "eur":
                registration.amount_paid_eur_cents += transaction.amount_cents
                detail += f" = {transaction.amount_cents} cents EUR"
            _event(session, transaction, "payment_matched", detail, registration)
            session.flush()
            emails.send_payment_received(
                mailer, tournament, registration.fencer, registration
            )
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
    back to reserved; the transaction returns to the unmatched queue."""
    transaction = _transaction_by_external_id(
        session, tournament, rule.target.removeprefix("txn:")
    )
    if transaction is not None and transaction.status_reason == "manual_link":
        transaction.status = "unmatched"
        transaction.status_reason = "manual_unlink"
        transaction.matched_registration_id = None
    # the exact amount and currency this link credited, so reverting removes
    # exactly that from exactly that currency's counter
    which = match_currency(transaction, tournament) if transaction is not None else None

    still_linked = {
        vs
        for other in rules_engine.active_rules(session, tournament, kind="payment_link")
        for vs in other.payload.get("vs", [])
    }
    for vs in rule.payload.get("vs", []):
        if vs in still_linked:
            continue
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
            registration.amount_paid_cents -= transaction.amount_cents
        elif which == "eur":
            registration.amount_paid_eur_cents -= transaction.amount_cents
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                transaction_id=transaction.id if transaction else None,
                kind="manual_link_removed",
                detail=f"rule {rule.id}: VS {vs} back to reserved",
            )
        )
    session.commit()
