"""Discipline seat/queue counts. Shared by the registration availability
endpoint (registrations.py) and the fencer-facing open-tournaments list
(tournaments.py) — kept here, not in either router, to avoid a circular
import between the two.

A team discipline is counted in teams, never in fencers: `taken_seats`/
`queue_length` and `taken_team_slots`/`team_queue_length` are mutually
exclusive by `discipline.kind` (design team-disciplines D1/2.6) — calling the
wrong pair for a discipline's kind is a programming error, asserted below."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Discipline,
    DisciplineKind,
    Registration,
    RegistrationDiscipline,
    RegistrationState,
    Team,
    Tournament,
)
from app.setup import seating_has_settled


def live_registration():
    """The registration still exists: reserved within its validity window, or
    paid for. Cancelled and expired registrations are neither.

    Both halves are now inside the reserved state, because `PAID` left the
    enum: a paid registration is a reserved one whose money is in, and the
    settled derivation is what says so. A settled registration counts whatever
    its window says, exactly as the paid state used to.

    One definition, asked by everything that counts a placement — a seat
    against capacity and a place in the queue alike. Counting a queue from
    reserved registrations alone was only ever correct while a queued
    registration could never be paid, which stopped being true once a
    submission could seat one discipline and queue another (design D3): a
    fencer who paid for their seat would drop out of the queue they were
    waiting in and hand their position to somebody else."""
    return (Registration.state == RegistrationState.RESERVED) & (
        Registration.settled
        | (Registration.expires_at.is_(None))
        | (Registration.expires_at > datetime.now(UTC))
    )


QUEUE_ORDER = (RegistrationDiscipline.queued_since, Registration.registered_at, Registration.id)
"""The substitute queue's order: the placement's queue moment, then the
registration time, then the registration. The moment is the registration time
for a placement queued at registration and the moment of demotion for one moved
there for non-payment (spec seating-queue); registrations demoted together share
it and so fall back to the order they registered in. Every reader of queue
order sorts by this, so the position a fencer is shown and the order the
organizer's view lists them in cannot disagree."""


def queued_before(entry: RegistrationDiscipline) -> ColumnElement[bool]:
    """Whether a placement in the selection sits ahead of `entry` in
    `QUEUE_ORDER`. Spelled out rather than as a row-value comparison, which not
    every database this runs on accepts with bound parameters."""
    moment, registered_at, registration_id = QUEUE_ORDER
    registration = entry.registration
    return or_(
        moment < entry.queued_since,
        and_(
            moment == entry.queued_since,
            or_(
                registered_at < registration.registered_at,
                and_(
                    registered_at == registration.registered_at, registration_id < registration.id
                ),
            ),
        ),
    )


def queue_position(session: Session, entry: RegistrationDiscipline) -> int:
    """Where a substitute placement stands in its discipline's queue, counted
    over live placements in `QUEUE_ORDER`."""
    earlier = session.scalar(
        select(func.count())
        .select_from(RegistrationDiscipline)
        .join(Registration)
        .where(
            RegistrationDiscipline.discipline_id == entry.discipline_id,
            RegistrationDiscipline.is_substitute.is_(True),
            live_registration(),
            queued_before(entry),
        )
    )
    return (earlier or 0) + 1


def team_waitlist_position(session: Session, team: Team) -> int:
    """Where a waitlisted team stands on its discipline's waitlist: entry order,
    except that a team demoted for non-payment waits from the moment it was
    demoted — `(waitlisted_since, id)`, as the console's team view lists them."""
    earlier = session.scalar(
        select(func.count())
        .select_from(Team)
        .join(Registration)
        .where(
            Team.discipline_id == team.discipline_id,
            Team.waitlisted.is_(True),
            live_registration(),
            or_(
                Team.waitlisted_since < team.waitlisted_since,
                and_(Team.waitlisted_since == team.waitlisted_since, Team.id < team.id),
            ),
        )
    )
    return (earlier or 0) + 1


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
    teams and answered by `team_waitlist_flags`."""
    return {
        d.slug
        for d in disciplines
        if d.kind == DisciplineKind.INDIVIDUAL and taken_seats(session, d) >= d.capacity
    }


def queued_on_entry(
    session: Session, tournament: Tournament, disciplines: list[Discipline], now: datetime
) -> set[str]:
    """Which of a new submission's individual disciplines are placed in the
    queue rather than a seat, by slug: each full one — and, once seating has
    settled, every one, free places or not (spec registration, Registration
    after seating has settled).

    The placement every new registration is given, whichever road it arrives
    by: the fencer's own submission and an organizer's hand entry ask this
    rather than each deciding, so an entry at the door is placed exactly as a
    submission is (design manual-entry-registers D1)."""
    if seating_has_settled(tournament, now):
        return {d.slug for d in disciplines}
    return full_disciplines(session, disciplines)


def _require_kind(discipline: Discipline, kind: DisciplineKind) -> None:
    """These counts are per-kind: a team discipline's capacity is consumed by
    teams and an individual's by registrations, and the queries below are not
    interchangeable. A caller reaching the wrong one is a programming error, so
    it raises rather than returning a number that would be quietly wrong."""
    if discipline.kind != kind:
        raise AssertionError(f"{discipline.slug} is a {discipline.kind} discipline, not {kind}")


def taken_seats(session: Session, discipline: Discipline) -> int:
    """Capacity is consumed by paid registrations and unexpired reservations."""
    _require_kind(discipline, DisciplineKind.INDIVIDUAL)
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
    _require_kind(discipline, DisciplineKind.INDIVIDUAL)
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
    _require_kind(discipline, DisciplineKind.TEAM)
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
    _require_kind(discipline, DisciplineKind.TEAM)
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


def team_waitlist_flags(
    session: Session,
    team_entries: Sequence[tuple[Discipline, object]],
    *,
    exclude_registration_id: int | None = None,
) -> list[bool]:
    """One waitlisted flag per team entry, in submission order, assigning
    remaining capacity sequentially so two teams entered into the same
    discipline in one submission are not both charged into the same last-open
    slot. `exclude_registration_id` excludes a registration's own current
    teams from the count, so recomputing on amendment does not count a team
    against itself (design team-disciplines 4.3)."""
    counts: dict[int, int] = {}
    flags = []
    for discipline, _ in team_entries:
        if discipline.id not in counts:
            counts[discipline.id] = taken_team_slots(
                session, discipline, exclude_registration_id=exclude_registration_id
            )
        taken = counts[discipline.id]
        waitlisted = taken >= discipline.capacity
        counts[discipline.id] = taken if waitlisted else taken + 1
        flags.append(waitlisted)
    return flags
