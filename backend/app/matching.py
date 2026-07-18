"""Automatic payment matching: strictly VS-first, amount within the
tournament's tolerance. Never by payer name or amount alone."""

import re
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import emails
from app.mail import Mailer
from app.models import (
    BankTransaction,
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

        if registration.state != RegistrationState.RESERVED:
            _finish(transaction, "flagged", f"registration_{registration.state.value}")
            _event(
                session, transaction, "match_conflict",
                f"VS {vs}: registration is {registration.state.value}", registration,
            )
            result.flagged += 1
            continue

        due_cents = registration.total_amount * 100
        tolerance = due_cents * tournament.amount_tolerance_percent / 100
        if abs(transaction.amount_cents - due_cents) > tolerance:
            _finish(transaction, "flagged", "amount_out_of_tolerance")
            _event(
                session, transaction, "amount_mismatch",
                f"VS {vs}: paid {transaction.amount_cents} of {due_cents} cents",
                registration,
            )
            result.flagged += 1
            continue

        registration.state = RegistrationState.PAID
        registration.paid_at = datetime.now(UTC)
        transaction.matched_registration_id = registration.id
        _finish(transaction, "matched", "auto_vs")
        _event(
            session, transaction, "payment_matched",
            f"VS {vs}: {transaction.amount_cents} cents", registration,
        )
        result.matched += 1
        session.flush()
        emails.send_payment_received(mailer, tournament, registration.fencer, registration)

    session.commit()
    return result
