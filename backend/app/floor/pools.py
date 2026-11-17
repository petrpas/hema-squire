"""The draw and its gate (spec floor-draw; design add-floor-pools D2, D3).

A discipline's pools are drawn from its check-in snapshot over the published
plan's pools and waves, with the adopted solver. Before the draw is
announced the organizer may swap and redraw; announcing freezes it, writes
its bouts in sheet order and pins its pools for the planner.
"""

import random
import secrets
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.floor import gates, people, planning
from app.floor.engine import draw as engine
from app.floor.engine.model import Activity
from app.floor.engine.pool_order import order
from app.floor.engine.variants import waves
from app.floor.models import (
    FloorBout,
    FloorDraw,
    FloorPin,
    FloorPlanActivity,
    FloorPool,
    FloorPoolMember,
    FloorPoolRanking,
    FloorSettings,
)
from app.floor.roster import FloorDiscipline, Roster

GATE = "draw"


class Refused(Exception):
    def __init__(self, code: str, detail: object = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(code)


def gate_name(discipline: int) -> str:
    return f"{GATE}:{discipline}"


def draw_of(session: Session, tid: int, discipline: int) -> FloorDraw | None:
    return session.scalar(
        select(FloorDraw).where(
            FloorDraw.tournament_id == tid, FloorDraw.discipline_id == discipline
        )
    )


def pools_of(session: Session, draw: FloorDraw) -> list[FloorPool]:
    return list(
        session.scalars(
            select(FloorPool).where(FloorPool.draw_id == draw.id).order_by(FloorPool.number)
        )
    )


def members_of(session: Session, pool: FloorPool) -> list[FloorPoolMember]:
    return list(
        session.scalars(
            select(FloorPoolMember)
            .where(FloorPoolMember.pool_id == pool.id)
            .order_by(FloorPoolMember.ordinal)
        )
    )


def bouts_of(session: Session, tid: int, discipline: int) -> list[FloorBout]:
    return list(
        session.scalars(
            select(FloorBout)
            .where(
                FloorBout.tournament_id == tid,
                FloorBout.discipline_id == discipline,
                FloorBout.pool_id.is_not(None),
            )
            .order_by(FloorBout.pool_id, FloorBout.ordinal)
        )
    )


# ------------------------------------------------------------ inputs


@dataclass(frozen=True)
class PlannedPool:
    activity_id: str
    wave: int
    piste: int
    start: datetime


def planned_pools(session: Session, tid: int, discipline: int) -> list[PlannedPool]:
    """The published plan's pools of the discipline, by wave then number."""
    current = planning.published(session, tid)
    if current is None:
        return []
    rows = session.scalars(
        select(FloorPlanActivity).where(
            FloorPlanActivity.plan_id == current.id,
            FloorPlanActivity.discipline_id == discipline,
            FloorPlanActivity.kind == "pool",
        )
    ).all()
    activities = [
        Activity(
            id=r.activity_id,
            discipline=discipline,
            kind="pool",
            ordinal=r.ordinal,
            round=0,
            piste=r.piste_id,
            day=0,
            start=int(r.starts_at.timestamp() // 60),
            end=int(r.ends_at.timestamp() // 60),
        )
        for r in rows
    ]
    wave_of = waves(activities, discipline)
    by_id = {r.activity_id: r for r in rows}
    found = [PlannedPool(a.id, wave_of[a.id], a.piste, by_id[a.id].starts_at) for a in activities]
    return sorted(found, key=lambda p: (p.wave, p.start, p.activity_id))


def _parallel(session: Session, tid: int, discipline: int) -> tuple[set[int], set[int]]:
    """The plan's parallel waves of this discipline (1-based), and the other
    disciplines they run beside."""
    current = planning.published(session, tid)
    parallel: set[int] = set()
    beside: set[int] = set()
    for entry in current.exclusions if current is not None else []:
        if int(str(entry["a"])) != discipline:
            continue
        waves_listed = entry.get("parallel_waves")
        if isinstance(waves_listed, list):
            parallel.update(int(str(w)) for w in waves_listed)
            beside.add(int(str(entry["b"])))
    return parallel, beside


def participants(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> list[people.Entrant]:
    """Who fences the pools: the snapshot's entrants, or for a team
    discipline the arrived members of its present teams (spec floor-draw)."""
    found = people.entrants(session, tid, roster, discipline)
    if discipline.kind != "team":
        return found
    known = people.persons(session, tid, roster)
    out: list[people.Entrant] = []
    for team in found:
        for key in team.members:
            person = known.get(key)
            out.append(
                people.Entrant(
                    key=key,
                    kind="person",
                    name=person.name if person else key,
                    club=person.club if person else None,
                    nationality=person.nationality if person else None,
                    hr_id=person.hr_id if person else None,
                    rating=None,
                    rank=None,
                    paid=True,
                )
            )
    return out


def seeded(entrants: list[people.Entrant], seed: int) -> list[people.Entrant]:
    """Rated first by rating, rank breaking ties; the unrated after, in an
    order the stored seed fixes (spec floor-draw, Seeds come from the snapshot)."""
    rated = sorted(
        (e for e in entrants if e.rating is not None),
        key=lambda e: (-(e.rating or 0.0), e.rank if e.rank is not None else 10**9, e.key),
    )
    unrated = sorted((e for e in entrants if e.rating is None), key=lambda e: e.key)
    # deterministic on purpose: the stored seed must reproduce the draw, and
    # the seed itself comes from `secrets`
    random.Random(seed).shuffle(unrated)  # noqa: S311
    return rated + unrated


def _weights(session: Session, tid: int) -> engine.Weights:
    row = session.get(FloorSettings, tid)
    params = row.params if row is not None else {}
    club = params.get("club_weight", 10)
    nationality = params.get("nationality_weight", 3)
    return engine.Weights(
        club=float(club) if isinstance(club, int | float) else 10.0,
        nationality=float(nationality) if isinstance(nationality, int | float) else 3.0,
    )


# ------------------------------------------------------------ drawing


def _solve(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline, seed: int
) -> tuple[list[list[engine.PoolFencer]], engine.Score, list[PlannedPool], engine.Weights]:
    planned = planned_pools(session, tid, discipline.id)
    if not planned:
        raise Refused("plan_not_published")
    entrants = seeded(participants(session, tid, roster, discipline), seed)
    if len(entrants) < 2:
        raise Refused("too_few")
    parallel, beside = _parallel(session, tid, discipline.id)
    in_beside: set[str] = set()
    for other in roster.disciplines:
        if other.id in beside:
            for e in participants(session, tid, roster, other):
                in_beside.add(e.key)
    wave_numbers = sorted({p.wave for p in planned})
    config = engine.PoolConfig(
        num_pools=len(planned),
        wave_sizes=tuple(sum(1 for p in planned if p.wave == w) for w in wave_numbers),
        parallel_waves=tuple(i for i, w in enumerate(wave_numbers) if w in parallel),
    )
    fencers = [
        engine.PoolFencer(
            key=e.key,
            seed=index,
            nationality=e.nationality,
            club=e.club,
            other_disciplines=("parallel",) if e.key in in_beside else (),
        )
        for index, e in enumerate(entrants, start=1)
    ]
    weights = _weights(session, tid)
    pools, score = engine.solve(fencers, config, weights)
    return pools, score, planned, weights


def _score_json(score: engine.Score) -> dict[str, float]:
    return {
        "snake": round(score.snake_deviation, 6),
        "club": round(score.club, 6),
        "nationality": round(score.nationality, 6),
        "wave": round(score.wave, 6),
        "total": round(score.total, 6),
    }


def make(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline, seed: int | None = None
) -> FloorDraw:
    """Draw the discipline's pools, replacing an unannounced draw."""
    if people.snapshot(session, tid, discipline.id) is None:
        raise Refused("checkin_open")
    existing = draw_of(session, tid, discipline.id)
    if existing is not None and existing.announced_at is not None:
        raise Refused("draw_announced")
    drawn_seed = seed if seed is not None else secrets.randbits(62)
    pools, score, planned, weights = _solve(session, tid, roster, discipline, drawn_seed)
    if existing is not None:
        _delete_pools(session, existing)
        session.delete(existing)
        session.flush()
    row = FloorDraw(
        tournament_id=tid,
        discipline_id=discipline.id,
        seed=drawn_seed,
        weights={"club": weights.club, "nationality": weights.nationality},
        score=_score_json(score),
        previous_score=None,
    )
    session.add(row)
    session.flush()
    for number, (fencers, plan) in enumerate(zip(pools, planned, strict=True), start=1):
        pool = FloorPool(
            draw_id=row.id,
            number=number,
            wave=plan.wave,
            activity_id=plan.activity_id,
            piste_id=plan.piste,
            planned_start=plan.start,
        )
        session.add(pool)
        session.flush()
        for ordinal, fencer in enumerate(sorted(fencers, key=lambda f: f.seed), start=1):
            session.add(
                FloorPoolMember(
                    pool_id=pool.id, entrant_key=fencer.key, ordinal=ordinal, seed=fencer.seed
                )
            )
    session.flush()
    return row


def _delete_pools(session: Session, draw: FloorDraw) -> None:
    pool_ids = [p.id for p in pools_of(session, draw)]
    if pool_ids:
        session.execute(delete(FloorBout).where(FloorBout.pool_id.in_(pool_ids)))
        session.execute(delete(FloorPoolMember).where(FloorPoolMember.pool_id.in_(pool_ids)))
        session.execute(delete(FloorPool).where(FloorPool.id.in_(pool_ids)))


def _assignment(
    session: Session, draw: FloorDraw, discipline: FloorDiscipline, tid: int, roster: Roster
) -> tuple[list[list[engine.PoolFencer]], engine.PoolConfig, list[FloorPool]]:
    pools = pools_of(session, draw)
    entrants = {e.key: e for e in participants(session, tid, roster, discipline)}
    parallel, beside = _parallel(session, tid, discipline.id)
    in_beside: set[str] = set()
    for other in roster.disciplines:
        if other.id in beside:
            in_beside.update(e.key for e in participants(session, tid, roster, other))
    wave_numbers = sorted({p.wave for p in pools})
    config = engine.PoolConfig(
        num_pools=len(pools),
        wave_sizes=tuple(sum(1 for p in pools if p.wave == w) for w in wave_numbers),
        parallel_waves=tuple(i for i, w in enumerate(wave_numbers) if w in parallel),
    )
    assignment = [
        [
            engine.PoolFencer(
                key=m.entrant_key,
                seed=m.seed,
                nationality=entrants[m.entrant_key].nationality
                if m.entrant_key in entrants
                else None,
                club=entrants[m.entrant_key].club if m.entrant_key in entrants else None,
                other_disciplines=("parallel",) if m.entrant_key in in_beside else (),
            )
            for m in members_of(session, pool)
        ]
        for pool in pools
    ]
    return assignment, config, pools


def swap(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline, a: str, b: str
) -> FloorDraw:
    """Swap two fencers of an unannounced draw; the score is recomputed and
    the previous one kept beside it."""
    draw = draw_of(session, tid, discipline.id)
    if draw is None:
        raise Refused("no_draw")
    if draw.announced_at is not None:
        raise Refused("draw_announced")
    assignment, config, pools = _assignment(session, draw, discipline, tid, roster)
    where: dict[str, tuple[int, int]] = {}
    for p, fencers in enumerate(assignment):
        for i, f in enumerate(fencers):
            where[f.key] = (p, i)
    if a not in where or b not in where:
        raise Refused("not_in_draw")
    (pa, ia), (pb, ib) = where[a], where[b]
    fa, fb = assignment[pa][ia], assignment[pb][ib]
    n = config.num_pools
    if engine.seed_tier(fa.seed, n) == 0 or engine.seed_tier(fb.seed, n) == 0:
        raise Refused("locked_seed")
    if (fa.other_disciplines and config.is_parallel(config.wave_of_pool(pb))) or (
        fb.other_disciplines and config.is_parallel(config.wave_of_pool(pa))
    ):
        raise Refused("wave")
    assignment[pa][ia], assignment[pb][ib] = fb, fa
    weights = engine.Weights(
        club=float(draw.weights.get("club", 10.0)),
        nationality=float(draw.weights.get("nationality", 3.0)),
    )
    draw.previous_score = dict(draw.score)
    draw.score = _score_json(engine.score(assignment, weights, config))
    for fencers, pool in zip(assignment, pools, strict=True):
        session.execute(delete(FloorPoolMember).where(FloorPoolMember.pool_id == pool.id))
        session.flush()
        for ordinal, fencer in enumerate(sorted(fencers, key=lambda f: f.seed), start=1):
            session.add(
                FloorPoolMember(
                    pool_id=pool.id, entrant_key=fencer.key, ordinal=ordinal, seed=fencer.seed
                )
            )
    session.flush()
    return draw


def announce(
    session: Session, tid: int, discipline: FloorDiscipline, by: int | None, now: datetime
) -> None:
    """Freeze the draw, write its bouts in sheet order, pin its pools."""
    if people.snapshot(session, tid, discipline.id) is None:
        raise Refused("checkin_open")
    draw = draw_of(session, tid, discipline.id)
    if draw is None:
        raise Refused("no_draw")
    if draw.announced_at is not None:
        raise Refused("draw_announced")
    pools = pools_of(session, draw)
    for pool in pools:
        members = members_of(session, pool)
        for ordinal, (left, right) in enumerate(order(len(members)), start=1):
            session.add(
                FloorBout(
                    tournament_id=tid,
                    discipline_id=discipline.id,
                    pool_id=pool.id,
                    ordinal=ordinal,
                    a_key=members[left - 1].entrant_key,
                    b_key=members[right - 1].entrant_key,
                    version=0,
                )
            )
    draw.announced_at = now
    draw.announced_by = by
    session.add(
        FloorPin(
            tournament_id=tid,
            kind="pools",
            target=str(discipline.id),
            value={"pools": len(pools)},
            gate=gate_name(discipline.id),
            created_at=now,
            created_by=by,
        )
    )
    session.flush()


def recorded(session: Session, tid: int, discipline: int) -> list[str]:
    """The discipline's bouts that carry a result, named for a refusal."""
    out: list[str] = []
    pools = {}
    draw = draw_of(session, tid, discipline)
    if draw is not None:
        pools = {p.id: p.number for p in pools_of(session, draw)}
    for bout in bouts_of(session, tid, discipline):
        if bout.recorded_at is not None and bout.pool_id is not None:
            out.append(f"{pools.get(bout.pool_id, '?')}:{bout.ordinal}")
    return out


def reopen_preview(session: Session, tid: int, discipline: int) -> dict[str, list[str]]:
    return {
        "invalidated": ["sheets", "call_list", "pools_pin"],
        "refusals": recorded(session, tid, discipline),
    }


def reopen(session: Session, tid: int, discipline: int) -> None:
    """Unannounce: the bouts and the pin go, the pools stay to adjust."""
    draw = draw_of(session, tid, discipline)
    if draw is None or draw.announced_at is None:
        raise Refused("draw_not_announced")
    refusing = recorded(session, tid, discipline)
    if refusing:
        raise Refused("results_recorded", refusing)
    pool_ids = [p.id for p in pools_of(session, draw)]
    session.execute(delete(FloorBout).where(FloorBout.pool_id.in_(pool_ids)))
    session.execute(
        delete(FloorPin).where(
            FloorPin.tournament_id == tid, FloorPin.gate == gate_name(discipline)
        )
    )
    draw.announced_at = None
    draw.announced_by = None
    session.flush()


def discard(session: Session, tid: int, discipline: int) -> None:
    """Reopening check-in throws the draw away, unannounced or not."""
    draw = draw_of(session, tid, discipline)
    if draw is None:
        return
    _delete_pools(session, draw)
    session.execute(
        delete(FloorPoolRanking).where(
            FloorPoolRanking.tournament_id == tid, FloorPoolRanking.discipline_id == discipline
        )
    )
    session.execute(
        delete(FloorPin).where(
            FloorPin.tournament_id == tid, FloorPin.gate == gate_name(discipline)
        )
    )
    session.delete(draw)
    session.flush()


gates.register(
    "checkin",
    gates.Hook(
        describe=lambda session, tid, d: ["draw"] if draw_of(session, tid, d) is not None else [],
        discard=discard,
        refuse=recorded,
    ),
)
