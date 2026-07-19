"""Discipline seat/queue counts. Shared by the registration availability
endpoint (registrations.py) and the fencer-facing open-tournaments list
(tournaments.py) — kept here, not in either router, to avoid a circular
import between the two."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Discipline, Registration, RegistrationDiscipline, RegistrationState


def taken_seats(session: Session, discipline: Discipline) -> int:
    """Capacity is consumed by paid registrations and unexpired reservations."""
    return (
        session.scalar(
            select(func.count())
            .select_from(RegistrationDiscipline)
            .join(Registration)
            .where(
                RegistrationDiscipline.discipline_id == discipline.id,
                RegistrationDiscipline.is_substitute.is_(False),
                (Registration.state == RegistrationState.PAID)
                | (
                    (Registration.state == RegistrationState.RESERVED)
                    & (
                        (Registration.expires_at.is_(None))
                        | (Registration.expires_at > datetime.now(UTC))
                    )
                ),
            )
        )
        or 0
    )


def queue_length(session: Session, discipline: Discipline) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(RegistrationDiscipline)
            .join(Registration)
            .where(
                RegistrationDiscipline.discipline_id == discipline.id,
                RegistrationDiscipline.is_substitute.is_(True),
                Registration.state == RegistrationState.RESERVED,
            )
        )
        or 0
    )
