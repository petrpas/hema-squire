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


def live_registration():
    """The registration still exists: reserved within its validity window, or
    paid. Cancelled and expired registrations are neither.

    One definition, asked by everything that counts a placement — a seat
    against capacity and a place in the queue alike. Counting a queue from
    reserved registrations alone was only ever correct while a queued
    registration could never be paid, which stopped being true once a
    submission could seat one discipline and queue another (design D3): a
    fencer who paid for their seat would drop out of the queue they were
    waiting in and hand their position to somebody else."""
    return (Registration.state == RegistrationState.PAID) | (
        (Registration.state == RegistrationState.RESERVED)
        & (
            (Registration.expires_at.is_(None))
            | (Registration.expires_at > datetime.now(UTC))
        )
    )


def full_disciplines(session: Session, disciplines: list[Discipline]) -> set[str]:
    """Which of `disciplines` have no free place right now, by slug.

    The one expression of the placement rule: an entry is a substitute when its
    own discipline is full at the moment it is placed, independently of every
    other discipline in the same submission (spec: registration, "Capacity and
    substitutes"). `register` and `amend` both ask this rather than each
    deciding for itself — they had already drifted once, `register` deciding in
    bulk for the whole submission while `amend` decided per entry, and the
    drift was invisible because each side read reasonably on its own.

    Individual disciplines only; a team discipline's capacity is counted in
    teams and answered by `_team_waitlist_flags`."""
    return {
        d.slug
        for d in disciplines
        if d.kind == DisciplineKind.INDIVIDUAL and taken_seats(session, d) >= d.capacity
    }


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
                live_registration(),
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
                live_registration(),
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
        live_registration(),
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
                live_registration(),
            )
        )
        or 0
    )
