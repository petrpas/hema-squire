"""Discipline seat/queue counts. Shared by the registration availability
endpoint (registrations.py) and the fencer-facing open-tournaments list
(tournaments.py) — kept here, not in either router, to avoid a circular
import between the two.

A team discipline is counted in teams, never in fencers: `taken_seats`/
`queue_length` and `taken_team_slots`/`team_queue_length` are mutually
exclusive by `discipline.kind` (design team-disciplines D1/2.6) — calling the
wrong pair for a discipline's kind is a programming error, asserted below."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Discipline,
    DisciplineKind,
    Registration,
    RegistrationDiscipline,
    RegistrationState,
    Team,
)


def taken_seats(session: Session, discipline: Discipline) -> int:
    """Capacity is consumed by paid registrations and unexpired reservations."""
    assert discipline.kind == DisciplineKind.INDIVIDUAL
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
    assert discipline.kind == DisciplineKind.INDIVIDUAL
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


def taken_team_slots(
    session: Session, discipline: Discipline, *, exclude_registration_id: int | None = None
) -> int:
    """A team discipline's capacity is consumed by teams on paid registrations
    and teams on unexpired reservations — the same predicate `taken_seats`
    applies to fencers, applied to teams instead.

    `exclude_registration_id`, when given, omits that registration's own
    teams from the count — used when recomputing an amendment's waitlist
    status, so a registration's existing teams are not counted against
    themselves (design team-disciplines 4.3)."""
    assert discipline.kind == DisciplineKind.TEAM
    conditions = [
        Team.discipline_id == discipline.id,
        Team.waitlisted.is_(False),
        (Registration.state == RegistrationState.PAID)
        | (
            (Registration.state == RegistrationState.RESERVED)
            & (
                (Registration.expires_at.is_(None))
                | (Registration.expires_at > datetime.now(UTC))
            )
        ),
    ]
    if exclude_registration_id is not None:
        conditions.append(Team.registration_id != exclude_registration_id)
    return (
        session.scalar(select(func.count()).select_from(Team).join(Registration).where(*conditions))
        or 0
    )


def team_queue_length(session: Session, discipline: Discipline) -> int:
    assert discipline.kind == DisciplineKind.TEAM
    return (
        session.scalar(
            select(func.count())
            .select_from(Team)
            .join(Registration)
            .where(
                Team.discipline_id == discipline.id,
                Team.waitlisted.is_(True),
                Registration.state == RegistrationState.RESERVED,
            )
        )
        or 0
    )
