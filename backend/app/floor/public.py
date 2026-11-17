"""The floor's public answers for a tournament's detail page (spec
floor-public; design add-floor-results D2, D3).

Behind the office's own public guard, re-exported by the adapter: a
published, non-cancelled tournament. The detail page asks which tabs exist
and renders what comes back; the rules of what is public live here.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from sqlalchemy import select

from app.floor import people, planning, progress, results
from app.floor.adapters.office import (
    OptionalFencerDep,
    SessionDep,
    TournamentDep,
    has_floor,
    person_key_for,
    require_public,
    roster,
    setup_facts,
)
from app.floor.models import FloorBout, FloorDraw, FloorPlanActivity, FloorPool, FloorPoolMember
from app.floor.setup import read_pistes

router = APIRouter(prefix="/api/tournaments", tags=["floor"])


def _local(when: datetime, zone: ZoneInfo) -> tuple[str, str]:
    """An instant stored in UTC (naive from SQLite) as the zone's date and time."""
    aware = when if when.tzinfo is not None else when.replace(tzinfo=UTC)
    moment = aware.astimezone(zone)
    return moment.date().isoformat(), moment.strftime("%H:%M")


@router.get("/{slug}/floor/public")
def floor_public_summary(tournament: TournamentDep, session: SessionDep) -> dict[str, bool]:
    """Which floor tabs the detail page offers: Program once a plan is
    published, Výsledky once any discipline's results are."""
    require_public(tournament)
    if not has_floor(tournament):
        return {"program": False, "results": False}
    any_results = any(
        results.published(session, tournament.id, d.id) is not None
        for d in setup_facts(tournament).disciplines
    )
    return {
        "program": planning.published(session, tournament.id) is not None,
        "results": any_results,
    }


@router.get("/{slug}/floor/public/program")
def floor_public_program(tournament: TournamentDep, session: SessionDep) -> list[dict[str, object]]:
    """The published plan by discipline: its pools' and rounds' planned
    times in the tournament's zone, and the slip. Never the working plan,
    officials, check-in or payments."""
    require_public(tournament)
    if not has_floor(tournament):
        return []
    plan = planning.published(session, tournament.id)
    if plan is None:
        return []
    facts = setup_facts(tournament)
    zone = ZoneInfo(facts.timezone)
    pistes = {p.id: p.name for p in read_pistes(session, tournament.id) if p.id is not None}
    out: list[dict[str, object]] = []
    for discipline in facts.disciplines:
        rows = session.scalars(
            select(FloorPlanActivity)
            .where(
                FloorPlanActivity.plan_id == plan.id,
                FloorPlanActivity.discipline_id == discipline.id,
            )
            .order_by(FloorPlanActivity.starts_at)
        ).all()
        items = []
        for row in rows:
            # a plan made without a schedule has no programme to show
            if row.starts_at is None or row.ends_at is None or row.piste_id is None:
                continue
            day, start = _local(row.starts_at, zone)
            _, end = _local(row.ends_at, zone)
            items.append(
                {
                    "kind": row.kind,
                    "round": row.round,
                    "ordinal": row.ordinal,
                    "final": row.final,
                    "day": day,
                    "start": start,
                    "end": end,
                    "piste": pistes.get(row.piste_id, ""),
                }
            )
        if not items:
            continue
        out.append(
            {
                "discipline": discipline.name,
                "slug": discipline.slug,
                "slip": progress.slip(session, tournament.id, discipline.id),
                "items": items,
            }
        )
    return out


@router.get("/{slug}/floor/public/results")
def floor_public_results(tournament: TournamentDep, session: SessionDep) -> list[dict[str, object]]:
    """The published standings, with name, club and nationality, as the
    public roster names entrants."""
    require_public(tournament)
    if not has_floor(tournament):
        return []
    found = roster(session, tournament)
    out: list[dict[str, object]] = []
    for discipline in setup_facts(tournament).disciplines:
        if results.published(session, tournament.id, discipline.id) is None:
            continue
        standing = results.placed(session, tournament.id, found, discipline) or []
        out.append(
            {
                "discipline": discipline.name,
                "slug": discipline.slug,
                "standing": [{k: v for k, v in row.items() if k != "key"} for row in standing],
            }
        )
    return out


@router.get("/{slug}/floor/public/itinerary")
def floor_public_itinerary(
    tournament: TournamentDep, session: SessionDep, fencer: OptionalFencerDep
) -> list[dict[str, object]]:
    """The signed-in fencer's own pools and bracket bouts with piste and
    planned time; nobody else's, and nothing without a sign-in."""
    require_public(tournament)
    if fencer is None or not has_floor(tournament):
        return []
    key = person_key_for(session, tournament, fencer)
    if key is None:
        return []
    facts = setup_facts(tournament)
    zone = ZoneInfo(facts.timezone)
    names = {d.id: d.name for d in facts.disciplines}
    pistes = {p.id: p.name for p in read_pistes(session, tournament.id) if p.id is not None}
    out: list[dict[str, object]] = []
    for pool, discipline_id in session.execute(
        select(FloorPool, FloorDraw.discipline_id)
        .join(FloorDraw, FloorDraw.id == FloorPool.draw_id)
        .join(FloorPoolMember, FloorPoolMember.pool_id == FloorPool.id)
        .where(
            FloorDraw.tournament_id == tournament.id,
            FloorDraw.announced_at.is_not(None),
            FloorPoolMember.entrant_key == key,
        )
    ).tuples():
        day, start = _local(pool.planned_start, zone) if pool.planned_start else ("", "")
        out.append(
            {
                "discipline": names.get(discipline_id, ""),
                "kind": "pool",
                "number": pool.number,
                "piste": pistes.get(pool.piste_id or 0, ""),
                "day": day,
                "start": start,
            }
        )
    teams = {
        t.key
        for d in facts.disciplines
        if d.kind == "team"
        for t in people.entrants(session, tournament.id, roster(session, tournament), d)
        if key in t.members
    }
    mine = {key} | teams
    for bout in session.scalars(
        select(FloorBout).where(
            FloorBout.tournament_id == tournament.id,
            FloorBout.bracket_id.is_not(None),
            FloorBout.recorded_at.is_(None),
        )
    ):
        if bout.a_key in mine or bout.b_key in mine:
            out.append(
                {
                    "discipline": names.get(bout.discipline_id, ""),
                    "kind": "bout",
                    "number": (bout.round or 0) + 1,
                    "piste": pistes.get(bout.piste_id or 0, ""),
                    "day": "",
                    "start": "",
                }
            )
    return out
