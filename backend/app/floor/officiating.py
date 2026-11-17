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

from app.floor import people, planning, setup
from app.floor.engine import officials as engine
from app.floor.engine.model import Activity, Stage
from app.floor.models import (
    FloorAssignment,
    FloorOfficial,
    FloorPlan,
    FloorPool,
    FloorPoolMember,
    FloorSettings,
)
from app.floor.pools import draw_of
from app.floor.roster import Roster
from app.floor.setup import Tournament


@dataclass(frozen=True)
class Inputs:
    plan: FloorPlan
    context: planning.Context
    activities: list[Activity]
    blocks: list[engine.Block]
    officials: list[engine.Official]


def inputs(session: Session, tournament: Tournament, roster: Roster) -> Inputs | None:
    """Everything the assignment reads, or None without a published plan or
    with officials not planned (spec floor-officials, Officials are planned
    only when asked for)."""
    tid = tournament.id
    if not planned(session, tid):
        return None
    plan = planning.published(session, tid)
    if plan is None:
        return None
    try:
        context = planning.build(session, tournament, roster)
    except planning.SetupIncomplete:
        return None
    activities = planning.activities_of(session, plan, context)
    seen = setup.effective(session, tournament)
    needs: dict[tuple[int, Stage], int] = {}
    for d, f in seen.formats.items():
        needs[(d, "pool")] = f.referees_pool
        needs[(d, "elim")] = f.referees_elim
    pause = {d: f.pause_between_pools for d, f in seen.formats.items()}
    raw_blocks = engine.blocks(activities, pause, needs)

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
            stage=b.stage,
            clubs=frozenset(
                club
                for activity in b.activities
                for key in pool_members.get(activity, [])
                if (club := known[key].club if key in known else None)
            ),
        )
        for b in raw_blocks
    ]

    day_index = {day.id: context.index_of(day.date) for day in seen.days}
    officials = [
        engine.Official(
            id=row.id,
            disciplines=regular | reserve,
            reserve=reserve - regular,
            main=row.main,
            days=frozenset(i for d in available if (i := day_index.get(d)) is not None),
            club=known[row.person_key].club if row.person_key in known else None,
            blocked=_blocked(
                session, tid, roster, tournament, row.person_key, activities, pool_members
            ),
        )
        for row, regular, reserve, available in seen.officials
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


def planned(session: Session, tid: int) -> bool:
    """Whether "Plánovat rozhodčí" is on (spec floor-setup, Scope)."""
    row = session.get(FloorSettings, tid)
    return row is not None and row.plan_schedule and row.plan_officials


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
        engine.Pin(block=s.block_key, role=engine.REFEREE, slot=s.slot, official=s.official_id)
        for s in stored
        if s.pinned and s.official_id is not None and s.block_key in keys
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
    """Blocks with their referees, the main place, reserve places, blocks
    without a main referee, the unfilled, the club conflicts, and pins whose
    block is gone."""
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
    people = {o.id: o for o in found.officials}
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
                "stage": block.stage,
                "without_main": _without_main(seats, people),
                "seats": [
                    {
                        "id": s.id,
                        "role": s.role,
                        "slot": s.slot,
                        "main_place": s.slot == 0,
                        "official_id": s.official_id,
                        "name": names.get(s.official_id) if s.official_id is not None else None,
                        "pinned": s.pinned,
                        "reserve": s.official_id is not None
                        and s.official_id in people
                        and block.discipline in people[s.official_id].reserve,
                        "main": s.official_id is not None
                        and s.official_id in people
                        and people[s.official_id].main,
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


def _without_main(seats: list[FloorAssignment], people: dict[int, engine.Official]) -> bool:
    seated = [s.official_id for s in seats if s.official_id is not None]
    return bool(seated) and not any(people[i].main for i in seated if i in people)


def without_main(session: Session, tid: int) -> int:
    """Blocks staffed with no main referee among them, for the `plan` badge:
    tolerated, but stated (owner decision 2026-11-17)."""
    if not planned(session, tid):
        return 0
    main = {
        o.id: o.main
        for o in session.scalars(select(FloorOfficial).where(FloorOfficial.tournament_id == tid))
    }
    seated: dict[str, list[int]] = {}
    for block, official in session.execute(
        select(FloorAssignment.block_key, FloorAssignment.official_id).where(
            FloorAssignment.tournament_id == tid, FloorAssignment.official_id.is_not(None)
        )
    ).tuples():
        if official is not None:
            seated.setdefault(block, []).append(official)
    return sum(1 for ids in seated.values() if not any(main.get(i, False) for i in ids))


def unfilled(session: Session, tid: int) -> int:
    """Seats with nobody on them, for the `plan` badge."""
    if not planned(session, tid):
        return 0
    return len(
        list(
            session.scalars(
                select(FloorAssignment.id).where(
                    FloorAssignment.tournament_id == tid, FloorAssignment.official_id.is_(None)
                )
            )
        )
    )


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
            place = "hlavní" if seat.slot == 0 else ""
            if kind == "official" and seat.official_id == subject:
                rows.append(
                    [day, span, pistes.get(block.piste, ""), names.get(block.discipline, ""), place]
                )
            elif kind == "piste" and block.piste == subject:
                who = officials.get(seat.official_id, "—") if seat.official_id is not None else "—"
                rows.append([day, span, names.get(block.discipline, ""), place, who])
    if kind == "official":
        return officials.get(subject, ""), ["Den", "Čas", "Planš", "Disciplína", "Místo"], rows
    return pistes.get(subject, ""), ["Den", "Čas", "Disciplína", "Místo", "Rozhodčí"], rows
