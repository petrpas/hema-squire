"""Periodic payment lifecycle processing: Fio polling, reminders, expiries.

The processing functions are pure sync logic over a session; the background
loop (started from the app lifespan) and the organizer endpoint both call them.
"""

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import bank, emails, matching
from app.config import settings
from app.db import SessionLocal
from app.mail import Mailer, get_mailer
from app.models import PaymentEvent, Registration, RegistrationState, Tournament

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def process_reminders(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Remind unpaid reservations that reached the tournament's reminder day."""
    threshold = _now() - timedelta(days=tournament.reminder_day)
    due = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            Registration.expires_at.is_not(None),
            Registration.reminded_at.is_(None),
            Registration.registered_at <= threshold,
        )
    ).all()
    for registration in due:
        registration.reminded_at = _now()
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="reminder_sent",
                detail=f"VS {registration.vs}",
            )
        )
        emails.send_payment_reminder(mailer, tournament, registration.fencer, registration)
    session.commit()
    return len(due)


def process_expiries(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Expire unpaid reservations past their window, freeing capacity.

    A partial payment does not extend the window (design harden-payment-
    matching Decision 3) — a reservation holding one expires on schedule like
    any other, but distinctly: a separate audit event and a branched notice,
    since the organizer is left holding money for a reservation that no
    longer exists."""
    overdue = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            Registration.expires_at.is_not(None),
            Registration.expires_at <= _now(),
        )
    ).all()
    for registration in overdue:
        registration.state = RegistrationState.EXPIRED
        holding_payment = (
            registration.amount_paid_cents > 0 or (registration.amount_paid_eur_cents or 0) > 0
        )
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="expired_holding_payment" if holding_payment else "reservation_expired",
                detail=f"VS {registration.vs}",
            )
        )
        emails.send_reservation_expired(
            mailer, tournament, registration.fencer, registration,
            holding_payment=holding_payment,
        )
    session.commit()
    return len(overdue)


def run_tournament_tick(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    fio_client: bank.FioClient | None = None,
) -> dict[str, int]:
    result: dict[str, int] = {}
    if fio_client is not None and tournament.fio_token:
        today = date.today()
        transactions = fio_client.fetch(
            tournament.fio_token, today - timedelta(days=14), today
        )
        ingested = bank.ingest(session, tournament, "fio_api", transactions)
        matched = matching.match_new_transactions(session, tournament, mailer)
        matching.apply_payment_links(session, tournament, mailer)
        result |= {"polled_new": ingested.new, "matched": matched.matched}
    # Expire first: a reservation past its window must not receive a reminder.
    result["expired"] = process_expiries(session, tournament, mailer)
    result["reminders"] = process_reminders(session, tournament, mailer)
    return result


def run_tick() -> None:
    """One scheduler pass over all current tournaments, with real dependencies."""
    mailer = get_mailer()
    fio_client = bank.get_fio_client()
    with SessionLocal() as session:
        tournaments = session.scalars(
            select(Tournament).where(Tournament.date >= date.today())
        ).all()
        for tournament in tournaments:
            try:
                run_tournament_tick(session, tournament, mailer, fio_client)
            except Exception:
                logger.exception("scheduler tick failed for %s", tournament.slug)


async def scheduler_loop() -> None:
    while True:
        await asyncio.sleep(settings.scheduler_interval_seconds)
        try:
            await asyncio.to_thread(run_tick)
        except Exception:
            logger.exception("scheduler tick crashed")
