"""Automatic payment matching: strictly VS-first, amount within the
tournament's tolerance. Never by payer name or amount alone.

A transaction in a foreign currency is converted into the tournament's primary
currency before the tolerance comparison — comparing the raw numbers would read
a correct 68.63 EUR transfer against a 1750 CZK total as 96 % short (design D5).
"""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import emails, pricing
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


class MatchResult(BaseModel):
    matched: int = 0
    flagged: int = 0
    unmatched: int = 0


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


def paid_cents_in_primary(
    transaction: BankTransaction, tournament: Tournament
) -> int | None:
    """The transaction's amount in primary-currency cents, or None when the two
    currencies are not commensurable — an unset transaction currency is trusted
    as the primary one (that is what pre-multi-currency ingestion recorded)."""
    currency = (transaction.currency or str(tournament.primary_currency)).upper()
    if currency == str(tournament.primary_currency):
        return transaction.amount_cents
    if currency == Currency.EUR:
        converted = pricing.from_eur_cents(transaction.amount_cents, tournament)
        if converted is None:
            return None
        return int((converted * Decimal(100)).to_integral_value())
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

        registration = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id, Registration.vs == vs
            )
        )
        if registration is None:
            _finish(transaction, "unmatched", "unknown_vs")
            _event(session, transaction, "unknown_vs", f"VS {vs}")
            result.unmatched += 1
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

        paid_cents = paid_cents_in_primary(transaction, tournament)
        if paid_cents is None:
            # a currency the tournament has no rate for: flag it as such rather
            # than pretending the amounts are comparable
            _finish(transaction, "flagged", "currency_unconvertible")
            _event(
                session, transaction, "currency_unconvertible",
                f"VS {vs}: {transaction.amount_cents} cents in {transaction.currency}, "
                f"tournament prices in {tournament.primary_currency}",
                registration,
            )
            result.flagged += 1
            continue

        due_cents = registration.outstanding_cents
        tolerance = due_cents * tournament.amount_tolerance_percent / 100
        if abs(paid_cents - due_cents) > tolerance:
            _finish(transaction, "flagged", "amount_out_of_tolerance")
            _event(
                session, transaction, "amount_mismatch",
                f"VS {vs}: paid {paid_cents} of {due_cents} cents",
                registration,
            )
            result.flagged += 1
            continue

        registration.state = RegistrationState.PAID
        registration.paid_at = datetime.now(UTC)
        registration.amount_paid_cents += paid_cents
        transaction.matched_registration_id = registration.id
        _finish(transaction, "matched", "auto_vs")
        # the audit records what arrived and, when converted, what it counted as
        detail = f"VS {vs}: {transaction.amount_cents} cents"
        if paid_cents != transaction.amount_cents:
            detail += f" {transaction.currency} = {paid_cents} cents primary"
        _event(session, transaction, "payment_matched", detail, registration)
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
        credited = paid_cents_in_primary(transaction, tournament)
        for registration in registrations:
            if registration.state != RegistrationState.RESERVED:
                continue
            registration.state = RegistrationState.PAID
            registration.paid_at = datetime.now(UTC)
            detail = f"manual link (rule {rule.id}): VS {registration.vs}"
            if credited is not None:
                registration.amount_paid_cents += credited
                detail += f" = {credited} cents primary"
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
    # the exact amount this link credited, so reverting removes exactly that
    credited = paid_cents_in_primary(transaction, tournament) if transaction is not None else None

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
        if credited is not None:
            registration.amount_paid_cents -= credited
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
