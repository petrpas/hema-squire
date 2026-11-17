"""Officials on the published plan's blocks (spec floor-officials; design
add-floor-officials D2, D3).

Builds the engine's blocks and officials from the published plan, floor
Setup and who fences where, runs the assignment, and stores it. Pinned seats
survive every re-run; a pin whose block no longer exists is listed as
unmatched for the organizer to resolve.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.floor import people, planning
from app.floor.engine import officials as engine
from app.floor.engine.model import Activity, Role
from app.floor.models import (
    FloorAssignment,
    FloorDay,
    FloorFormat,
    FloorOfficial,
    FloorOfficialDay,
    FloorPlan,
    FloorPool,
    FloorPoolMember,
)
from app.floor.pools import draw_of
from app.floor.roster import Roster
from app.floor.setup import Tournament

ROLES: tuple[Role, ...] = ("referee", "judge", "table")


@dataclass(frozen=True)
class Inputs:
    plan: FloorPlan
    context: planning.Context
    activities: list[Activity]
    blocks: list[engine.Block]
    officials: list[engine.Official]


def inputs(session: Session, tournament: Tournament, roster: Roster) -> Inputs | None:
    """Everything the assignment reads, or None without a published plan."""
    tid = tournament.id
    plan = planning.published(session, tid)
    if plan is None:
        return None
    try:
        context = planning.build(session, tournament, roster)
    except planning.SetupIncomplete:
        return None
    activities = planning.activities_of(session, plan, context)
    formats = {
        f.discipline_id: f
        for f in session.scalars(select(FloorFormat).where(FloorFormat.tournament_id == tid))
    }
    needs: dict[int, tuple[tuple[Role, int], ...]] = {
        d: tuple(
            (role, int((f.staffing or {}).get(role, 0)))
            for role in ROLES
            if (f.staffing or {}).get(role)
        )
        for d, f in formats.items()
    }
    overhead = {d: f.slot_pool_overhead for d, f in formats.items()}
    raw_blocks = engine.blocks(activities, overhead, needs)

    # who fences where: the clubs of each pool, and each person's pools
    known = people.persons(session, tid, roster)
    pool_members: dict[str, list[str]] = {}
    for discipline in tournament.disciplines:
        draw = draw_of(session, tid, discipline.id)
        if draw is None or draw.announced_at is None:
            continue
        for pool, key in session.execute(
            select(FloorPool.activity_id, FloorPoolMember.entrant_key)
            .join(FloorPoolMember, FloorPoolMember.pool_id == FloorPool.id)
            .where(FloorPool.draw_id == draw.id)
        ).tuples():
            if pool is not None:
                pool_members.setdefault(pool, []).append(key)
    blocks = [
        engine.Block(
            key=b.key,
            discipline=b.discipline,
            piste=b.piste,
            day=b.day,
            start=b.start,
            end=b.end,
            needs=b.needs,
            activities=b.activities,
            clubs=frozenset(
                club
                for activity in b.activities
                for key in pool_members.get(activity, [])
                if (club := known[key].club if key in known else None)
            ),
        )
        for b in raw_blocks
    ]

    rows = list(session.scalars(select(FloorOfficial).where(FloorOfficial.tournament_id == tid)))
    days_of: dict[int, set[int]] = {}
    for official_id, day_id in session.execute(
        select(FloorOfficialDay.official_id, FloorOfficialDay.day_id).where(
            FloorOfficialDay.official_id.in_([o.id for o in rows])
        )
    ).tuples():
        days_of.setdefault(official_id, set()).add(day_id)
    day_index = {
        day.id: context.index_of(day.date)
        for day in session.scalars(select(FloorDay).where(FloorDay.tournament_id == tid))
    }
    officials = [
        engine.Official(
            id=row.id,
            roles=frozenset(row.roles),
            disciplines=frozenset(row.discipline_ids),
            days=frozenset(
                i for d in days_of.get(row.id, set()) if (i := day_index.get(d)) is not None
            ),
            club=known[row.person_key].club if row.person_key in known else None,
            blocked=_blocked(
                session, tid, roster, tournament, row.person_key, activities, pool_members
            ),
        )
        for row in rows
    ]
    return Inputs(plan, context, activities, blocks, officials)


def _blocked(
    session: Session,
    tid: int,
    roster: Roster,
    tournament: Tournament,
    person: str | None,
    activities: list[Activity],
    pool_members: dict[str, list[str]],
) -> tuple[tuple[int, int, int], ...]:
    """When the official fences: before a discipline's draw, every activity of
    a discipline they entered; after it, their own pool and the elimination."""
    if person is None:
        return ()
    spans: list[tuple[int, int, int]] = []
    for discipline in tournament.disciplines:
        found = people.entrants(session, tid, roster, discipline)
        enters = any(e.key == person or person in e.members for e in found)
        if not enters:
            continue
        draw = draw_of(session, tid, discipline.id)
        announced = draw is not None and draw.announced_at is not None
        for a in activities:
            if a.discipline != discipline.id:
                continue
            if not announced or a.kind == "bout" or person in pool_members.get(a.id, []):
                spans.append((a.day, a.start, a.end))
    return tuple(spans)


def _role(value: str) -> Role | None:
    """A stored role back as the engine's type."""
    for role in ROLES:
        if role == value:
            return role
    return None


def run(session: Session, tournament: Tournament, roster: Roster, now: datetime) -> None:
    """Assign afresh, keeping every pinned seat whose block still exists."""
    found = inputs(session, tournament, roster)
    if found is None:
        return
    tid = tournament.id
    stored = list(
        session.scalars(select(FloorAssignment).where(FloorAssignment.tournament_id == tid))
    )
    keys = {b.key for b in found.blocks}
    pins = [
        engine.Pin(block=s.block_key, role=role, slot=s.slot, official=s.official_id)
        for s in stored
        if s.pinned
        and s.official_id is not None
        and s.block_key in keys
        and (role := _role(s.role)) is not None
    ]
    result = engine.assign(found.blocks, found.officials, pins)
    # unmatched pins stay as they were, for the organizer to resolve
    session.execute(
        delete(FloorAssignment).where(
            FloorAssignment.tournament_id == tid,
            (FloorAssignment.pinned.is_(False)) | FloorAssignment.block_key.in_(keys),
        )
    )
    for seat in result.seats:
        session.add(
            FloorAssignment(
                tournament_id=tid,
                plan_id=found.plan.id,
                block_key=seat.block,
                role=seat.role,
                slot=seat.slot,
                official_id=seat.official,
                pinned=seat.pinned,
                created_at=now,
            )
        )
    session.flush()


class Refused(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def set_seat(
    session: Session,
    tournament: Tournament,
    roster: Roster,
    seat_id: int,
    official_id: int | None,
    pinned: bool,
) -> None:
    """Put an official on a seat, pinned or not; a hard rule refuses it, named."""
    seat = session.get(FloorAssignment, seat_id)
    if seat is None or seat.tournament_id != tournament.id:
        raise Refused("seat_not_found")
    if official_id is not None:
        found = inputs(session, tournament, roster)
        if found is None:
            raise Refused("plan_not_published")
        _check(session, found, seat, official_id)
    seat.official_id = official_id
    seat.pinned = pinned and official_id is not None
    session.flush()


def _check(session: Session, found: Inputs, seat: FloorAssignment, official_id: int) -> None:
    official = next((o for o in found.officials if o.id == official_id), None)
    block = next((b for b in found.blocks if b.key == seat.block_key), None)
    if official is None or block is None:
        raise Refused("seat_not_found")
    others = [
        b
        for b in found.blocks
        for s in session.scalars(
            select(FloorAssignment).where(
                FloorAssignment.tournament_id == seat.tournament_id,
                FloorAssignment.official_id == official_id,
                FloorAssignment.id != seat.id,
            )
        )
        if s.block_key == b.key
    ]
    rule = engine.hard_ok(official, block, seat.role, others)
    if rule is not None:
        raise Refused(rule)


def swap(session: Session, tournament: Tournament, roster: Roster, a_id: int, b_id: int) -> None:
    a, b = session.get(FloorAssignment, a_id), session.get(FloorAssignment, b_id)
    if (
        a is None
        or b is None
        or a.tournament_id != tournament.id
        or b.tournament_id != tournament.id
    ):
        raise Refused("seat_not_found")
    found = inputs(session, tournament, roster)
    if found is None:
        raise Refused("plan_not_published")
    first, second = a.official_id, b.official_id
    a.official_id, b.official_id = None, None
    session.flush()
    try:
        if second is not None:
            _check(session, found, a, second)
        if first is not None:
            _check(session, found, b, first)
    except Refused:
        a.official_id, b.official_id = first, second
        session.flush()
        raise
    a.official_id, b.official_id = second, first
    session.flush()


def view(session: Session, tournament: Tournament, roster: Roster) -> dict[str, object]:
    """Blocks × roles with names, the unfilled, the club conflicts, and pins
    whose block is gone."""
    found = inputs(session, tournament, roster)
    if found is None:
        return {"published": False, "blocks": [], "unmatched": [], "conflicts": []}
    stored = list(
        session.scalars(
            select(FloorAssignment).where(FloorAssignment.tournament_id == tournament.id)
        )
    )
    names = {
        o.id: o.name
        for o in session.scalars(
            select(FloorOfficial).where(FloorOfficial.tournament_id == tournament.id)
        )
    }
    clubs = {o.id: o.club for o in found.officials}
    keys = {b.key for b in found.blocks}
    out_blocks = []
    conflicts = []
    for block in found.blocks:
        seats = sorted(
            (s for s in stored if s.block_key == block.key), key=lambda s: (s.role, s.slot)
        )
        for s in seats:
            club = clubs.get(s.official_id) if s.official_id is not None else None
            if club and club in block.clubs:
                conflicts.append({"block": block.key, "official_id": s.official_id, "club": club})
        out_blocks.append(
            {
                "key": block.key,
                "discipline_id": block.discipline,
                "piste_id": block.piste,
                "day": found.context.dates[block.day].isoformat(),
                "start": planning.clock(block.start),
                "end": planning.clock(block.end),
                "activities": list(block.activities),
                "seats": [
                    {
                        "id": s.id,
                        "role": s.role,
                        "slot": s.slot,
                        "official_id": s.official_id,
                        "name": names.get(s.official_id) if s.official_id is not None else None,
                        "pinned": s.pinned,
                    }
                    for s in seats
                ],
            }
        )
    return {
        "published": True,
        "blocks": out_blocks,
        "unmatched": [
            {
                "id": s.id,
                "block": s.block_key,
                "role": s.role,
                "name": names.get(s.official_id or 0),
            }
            for s in stored
            if s.block_key not in keys
        ],
        "conflicts": conflicts,
    }


def unfilled(session: Session, tid: int) -> int:
    """Seats with nobody on them, for the `plan` badge."""
    return len(
        list(
            session.scalars(
                select(FloorAssignment.id).where(
                    FloorAssignment.tournament_id == tid, FloorAssignment.official_id.is_(None)
                )
            )
        )
    )


ROLE_NAMES = {"referee": "Rozhodčí", "judge": "Postranní", "table": "Zapisovatel"}


def print_rows(
    session: Session,
    tournament: Tournament,
    roster: Roster,
    kind: str,
    subject: int,
    pistes: dict[int, str],
) -> tuple[str, list[str], list[list[str]]]:
    """An official's rozpis or a piste's sheet: its title, headers and rows,
    in time order."""
    found = inputs(session, tournament, roster)
    if found is None:
        return "", [], []
    names = {d.id: d.name for d in tournament.disciplines}
    officials = {
        o.id: o.name
        for o in session.scalars(
            select(FloorOfficial).where(FloorOfficial.tournament_id == tournament.id)
        )
    }
    seats = list(
        session.scalars(
            select(FloorAssignment).where(FloorAssignment.tournament_id == tournament.id)
        )
    )
    rows: list[list[str]] = []
    for block in found.blocks:
        day = found.context.dates[block.day].isoformat()
        span = f"{planning.clock(block.start)}–{planning.clock(block.end)}"
        for seat in sorted(
            (s for s in seats if s.block_key == block.key), key=lambda s: (s.role, s.slot)
        ):
            role = ROLE_NAMES.get(seat.role, seat.role)
            if kind == "official" and seat.official_id == subject:
                rows.append(
                    [day, span, pistes.get(block.piste, ""), names.get(block.discipline, ""), role]
                )
            elif kind == "piste" and block.piste == subject:
                who = officials.get(seat.official_id, "—") if seat.official_id is not None else "—"
                rows.append([day, span, names.get(block.discipline, ""), role, who])
    if kind == "official":
        return officials.get(subject, ""), ["Den", "Čas", "Planš", "Disciplína", "Role"], rows
    return pistes.get(subject, ""), ["Den", "Čas", "Disciplína", "Role", "Rozhodčí"], rows
