"""Pool bouts: recording, standings, the close gate, the call list and
progress (spec floor-pools; design add-floor-pools D3, D6)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.floor import gates, progress, steps
from app.floor.engine import pool_stats
from app.floor.engine.structure import advancing
from app.floor.models import FloorBout, FloorFormat, FloorPool, FloorPoolRanking
from app.floor.pools import Refused, bouts_of, draw_of, members_of, pools_of

OUTCOMES = ("win", "loss", "draw", "no")


@dataclass(frozen=True)
class Result:
    score_a: int
    score_b: int
    outcome_a: str
    outcome_b: str
    note: str | None = None


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def record(
    session: Session,
    tid: int,
    bout_id: int,
    result: Result,
    version: int,
    by: str,
    now: datetime,
    *,
    piste: int | None = None,
) -> FloorBout:
    """Record or correct a bout. `version` is the one the writer read; a stale
    one is refused, and the writer reads again. A piste screen records only
    its own piste's bouts."""
    bout = session.get(FloorBout, bout_id)
    if bout is None or bout.tournament_id != tid or bout.pool_id is None:
        raise Refused("bout_not_found")
    draw = draw_of(session, tid, bout.discipline_id)
    if draw is None or draw.announced_at is None:
        raise Refused("draw_not_announced")
    if draw.closed_at is not None:
        raise Refused("pools_closed")
    if piste is not None:
        pool = session.get(FloorPool, bout.pool_id)
        if pool is None or pool.piste_id != piste:
            raise Refused("not_this_piste")
    if bout.version != version:
        raise Refused("stale_version")
    if result.outcome_a not in OUTCOMES or result.outcome_b not in OUTCOMES:
        raise Refused("invalid_outcome")
    if result.outcome_a == result.outcome_b and result.outcome_a in ("win", "loss"):
        raise Refused("both_" + result.outcome_a)
    bout.score_a = result.score_a
    bout.score_b = result.score_b
    bout.outcome_a = result.outcome_a
    bout.outcome_b = result.outcome_b
    bout.note = result.note or None
    bout.recorded_at = now
    bout.recorded_by = by
    bout.version += 1
    session.flush()
    return bout


def as_results(bouts: Sequence[FloorBout]) -> list[pool_stats.BoutResult]:
    return [
        pool_stats.BoutResult(
            a=b.a_key,
            b=b.b_key,
            score_a=b.score_a or 0,
            score_b=b.score_b or 0,
            outcome_a="win" if b.outcome_a == "win" else "loss",
            outcome_b="win" if b.outcome_b == "win" else "loss",
            note=b.note,
        )
        for b in bouts
        if b.recorded_at is not None
    ]


def state(session: Session, tid: int, discipline: int) -> str:
    """waiting | running | complete | closed (spec floor-pools)."""
    draw = draw_of(session, tid, discipline)
    if draw is None or draw.announced_at is None:
        return "waiting"
    if draw.closed_at is not None:
        return "closed"
    bouts = bouts_of(session, tid, discipline)
    if bouts and all(b.recorded_at is not None for b in bouts):
        return "complete"
    return "running"


def standings(session: Session, tid: int, discipline: int) -> dict[str, object]:
    """Each pool's standings and warnings, and the overall ranking."""
    draw = draw_of(session, tid, discipline)
    if draw is None:
        return {"pools": [], "ranking": [], "warnings": []}
    bouts = bouts_of(session, tid, discipline)
    pools = pools_of(session, draw)
    composition = [(p.number, [m.entrant_key for m in members_of(session, p)]) for p in pools]
    out_pools: list[dict[str, object]] = []
    for pool, (number, keys) in zip(pools, composition, strict=True):
        mine = as_results([b for b in bouts if b.pool_id == pool.id])
        out_pools.append(
            {"number": number, "stats": [_stats_json(s) for s in pool_stats.compute(keys, mine)]}
        )
    everyone = [key for _, keys in composition for key in keys]
    ranking = [_stats_json(s) for s in pool_stats.compute(everyone, as_results(bouts))]
    warnings = [
        {
            "pool": w.pool,
            "code": w.code,
            "subject": w.subject,
            "expected": w.expected,
            "found": w.found,
        }
        for w in pool_stats.check(composition, as_results(bouts))
        # a pool not yet fenced is not inconsistent; it is pending
        if not (w.code == "no_results")
    ]
    return {"pools": out_pools, "ranking": ranking, "warnings": warnings}


def _stats_json(stats: pool_stats.Stats) -> dict[str, object]:
    return {
        "key": stats.key,
        "v": stats.v,
        "m": stats.m,
        "vm": round(stats.vm, 4),
        "ts": stats.ts,
        "tr": stats.tr,
        "ind": stats.ind,
    }


def close_preview(session: Session, tid: int, discipline: int) -> dict[str, object]:
    """The ranking, the advancing count and who advances (spec floor-pools,
    Closing the pools is a gate)."""
    ranking = standings(session, tid, discipline)["ranking"]
    fmt = session.scalar(select(FloorFormat).where(FloorFormat.discipline_id == discipline))
    total = len(ranking) if isinstance(ranking, list) else 0
    count = advancing(total, fmt.advance if fmt is not None else None)
    return {"ranking": ranking, "advance": count}


def close(session: Session, tid: int, discipline: int, by: int | None, now: datetime) -> None:
    if state(session, tid, discipline) != "complete":
        raise Refused("pools_incomplete")
    draw = draw_of(session, tid, discipline)
    if draw is None:
        raise Refused("no_draw")
    ranking = standings(session, tid, discipline)["ranking"]
    for place, row in enumerate(ranking if isinstance(ranking, list) else [], start=1):
        session.add(
            FloorPoolRanking(
                tournament_id=tid,
                discipline_id=discipline,
                entrant_key=str(row["key"]),
                place=place,
                stats={k: v for k, v in row.items() if k != "key"},
            )
        )
    draw.closed_at = now
    draw.closed_by = by
    session.flush()


def reopen(session: Session, tid: int, discipline: int) -> None:
    draw = draw_of(session, tid, discipline)
    if draw is None or draw.closed_at is None:
        raise Refused("pools_open")
    refusing = gates.refusals(session, "pools", tid, discipline)
    if refusing:
        raise Refused("results_recorded", refusing)
    gates.discard(session, "pools", tid, discipline)
    session.execute(
        delete(FloorPoolRanking).where(
            FloorPoolRanking.tournament_id == tid, FloorPoolRanking.discipline_id == discipline
        )
    )
    draw.closed_at = None
    draw.closed_by = None
    session.flush()


def ranking(session: Session, tid: int, discipline: int) -> list[FloorPoolRanking]:
    """The frozen ranking, best first; empty until the pools close."""
    return list(
        session.scalars(
            select(FloorPoolRanking)
            .where(
                FloorPoolRanking.tournament_id == tid, FloorPoolRanking.discipline_id == discipline
            )
            .order_by(FloorPoolRanking.place)
        )
    )


def _started(session: Session, pool: FloorPool) -> bool:
    return (
        session.scalar(
            select(FloorBout.id).where(
                FloorBout.pool_id == pool.id, FloorBout.recorded_at.is_not(None)
            )
        )
        is not None
    )


def call_list(session: Session, tid: int, discipline: int) -> list[dict[str, object]]:
    """The next wave's pools that have not started, their fencers by pool,
    piste and planned start (spec floor-pools, A call list)."""
    draw = draw_of(session, tid, discipline)
    if draw is None or draw.announced_at is None:
        return []
    waiting = [p for p in pools_of(session, draw) if not _started(session, p)]
    if not waiting:
        return []
    wave = min(p.wave for p in waiting)
    out: list[dict[str, object]] = []
    for pool in sorted(
        (p for p in waiting if p.wave == wave),
        key=lambda p: (p.planned_start or datetime.max.replace(tzinfo=UTC), p.number),
    ):
        out.append(
            {
                "pool": pool.number,
                "wave": pool.wave,
                "piste_id": pool.piste_id,
                "planned_start": pool.planned_start,
                "members": [m.entrant_key for m in members_of(session, pool)],
            }
        )
    return out


# ------------------------------------------------------------ registrations


def _started_pools(session: Session, tid: int, now: datetime) -> set[str]:
    """Activity ids of pools whose first bout is recorded."""
    found: set[str] = set()
    rows = session.execute(
        select(FloorPool.activity_id)
        .join(FloorBout, FloorBout.pool_id == FloorPool.id)
        .where(FloorBout.tournament_id == tid, FloorBout.recorded_at.is_not(None))
    ).scalars()
    for activity in rows:
        if activity is not None:
            found.add(activity)
    return found


def _slip(session: Session, tid: int, discipline: int) -> int | None:
    """The latest started pool's first recorded bout against its planned
    start, in minutes."""
    draw = draw_of(session, tid, discipline)
    if draw is None:
        return None
    latest: tuple[datetime, int] | None = None
    for pool in pools_of(session, draw):
        if pool.planned_start is None:
            continue
        first = session.scalar(
            select(FloorBout.recorded_at)
            .where(FloorBout.pool_id == pool.id, FloorBout.recorded_at.is_not(None))
            .order_by(FloorBout.recorded_at)
        )
        if first is None:
            continue
        planned = _aware(pool.planned_start)
        minutes = int((_aware(first) - planned).total_seconds() // 60)
        if latest is None or planned > latest[0]:
            latest = (planned, minutes)
    return latest[1] if latest is not None else None


progress.register(_started_pools)
progress.register_slip(_slip)
steps.register("pools", state)
