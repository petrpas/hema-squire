"""Check-in at the desk (spec floor-checkin; design add-floor-checkin).

Arrival is per person, withdrawal per entry, lineups per team, and closing
per discipline: a gate that freezes the discipline's snapshot and pins its N
for the planner. Nothing here writes to the office.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.floor import gates, people, planning, steps
from app.floor.engine.model import Choice
from app.floor.engine.structure import pool_counts, pool_sizes
from app.floor.engine.variants import evaluate
from app.floor.models import (
    FloorArrival,
    FloorLineup,
    FloorLocalPerson,
    FloorPin,
    FloorPlanActivity,
    FloorSnapshot,
    FloorSnapshotEntrant,
    FloorWithdrawal,
)
from app.floor.roster import FloorDiscipline, Roster
from app.floor.setup import Tournament

GATE = "checkin"
# how long before a discipline's first activity open check-in starts to wait
SOON = timedelta(minutes=30)


class Refused(Exception):
    def __init__(self, code: str, detail: object = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(code)


def gate_name(discipline: int) -> str:
    return f"{GATE}:{discipline}"


def closed(session: Session, tid: int, discipline: int) -> bool:
    return people.snapshot(session, tid, discipline) is not None


def _discipline_of_entry(entry_key: str, roster: Roster) -> int | None:
    if entry_key.startswith("team:"):
        team = next((t for t in roster.teams if t.key == entry_key), None)
        if team is None:
            return None
        return next((d.id for d in roster.disciplines if d.slug == team.discipline), None)
    _, _, discipline = entry_key.rpartition("@")
    return int(discipline) if discipline.isdigit() else None


# ------------------------------------------------------------ the desk


def arrive(session: Session, tid: int, person_key: str, by: int | None, now: datetime) -> None:
    """Idempotent: a second desk ticking the same person changes nothing."""
    if session.scalar(
        select(FloorArrival.id).where(
            FloorArrival.tournament_id == tid, FloorArrival.person_key == person_key
        )
    ):
        return
    session.add(FloorArrival(tournament_id=tid, person_key=person_key, at=now, by=by))
    try:
        session.flush()
    except IntegrityError:
        session.rollback()


def leave(session: Session, tid: int, person_key: str) -> None:
    session.execute(
        delete(FloorArrival).where(
            FloorArrival.tournament_id == tid, FloorArrival.person_key == person_key
        )
    )


def withdraw(
    session: Session, tid: int, roster: Roster, entry_key: str, by: int | None, now: datetime
) -> None:
    discipline = _discipline_of_entry(entry_key, roster)
    if discipline is None:
        raise Refused("entry_not_found")
    if closed(session, tid, discipline):
        raise Refused("checkin_closed")
    if entry_key in people.withdrawn(session, tid):
        return
    session.add(FloorWithdrawal(tournament_id=tid, entry_key=entry_key, at=now, by=by))
    session.flush()


def undo_withdrawal(session: Session, tid: int, roster: Roster, entry_key: str) -> None:
    discipline = _discipline_of_entry(entry_key, roster)
    if discipline is not None and closed(session, tid, discipline):
        raise Refused("checkin_closed")
    session.execute(
        delete(FloorWithdrawal).where(
            FloorWithdrawal.tournament_id == tid, FloorWithdrawal.entry_key == entry_key
        )
    )


def add_local(
    session: Session, tid: int, name: str, club: str | None, nationality: str | None
) -> str:
    row = FloorLocalPerson(tournament_id=tid, name=name, club=club, nationality=nationality)
    session.add(row)
    session.flush()
    return f"{people.LOCAL}{row.id}"


def lineup_errors(
    session: Session, tid: int, roster: Roster, team_key: str, keys: list[str]
) -> list[dict]:
    team = next((t for t in roster.teams if t.key == team_key), None)
    if team is None:
        return [{"field": "team_key", "code": "not_found"}]
    discipline = next(d for d in roster.disciplines if d.slug == team.discipline)
    if closed(session, tid, discipline.id):
        return [{"field": "person_keys", "code": "checkin_closed"}]
    errors: list[dict] = []
    known = people.persons(session, tid, roster)
    lo, hi = discipline.team_min or 1, discipline.team_max or len(keys) or 1
    if not lo <= len(keys) <= hi:
        errors.append(
            {"field": "person_keys", "code": "lineup_size", "params": {"min": lo, "max": hi}}
        )
    if len(set(keys)) != len(keys):
        errors.append({"field": "person_keys", "code": "duplicate"})
    stated = people.lineups(session, tid)
    for index, key in enumerate(keys):
        if key not in known:
            errors.append({"field": f"person_keys.{index}", "code": "unknown_person"})
            continue
        # one lineup per person per discipline
        for other in roster.teams:
            if other.key == team_key or other.discipline != team.discipline:
                continue
            if key in people.lineup_of(other, stated):
                errors.append({"field": f"person_keys.{index}", "code": "in_another_lineup"})
    return errors


def set_lineup(session: Session, tid: int, team_key: str, keys: list[str]) -> None:
    session.execute(
        delete(FloorLineup).where(
            FloorLineup.tournament_id == tid, FloorLineup.team_key == team_key
        )
    )
    for ordinal, key in enumerate(keys, start=1):
        session.add(
            FloorLineup(tournament_id=tid, team_key=team_key, person_key=key, ordinal=ordinal)
        )
    session.flush()


# ------------------------------------------------------------ the close gate


def impact(
    session: Session, tournament: Tournament, roster: Roster, discipline: FloorDiscipline
) -> dict[str, object]:
    """What closing would do: N, the pool structure the published variant
    gives for it, and its day's end against the published plan."""
    tid = tournament.id
    found = people.present(session, tid, roster, discipline)
    n_pool = sum(len(team.members) for team in found) if discipline.kind == "team" else len(found)
    out: dict[str, object] = {"n": len(found), "n_pool": n_pool, "feasible": False}
    try:
        context = planning.build(session, tournament, roster)
    except planning.SetupIncomplete:
        return out
    facts = next((d for d in context.problem.disciplines if d.id == discipline.id), None)
    fmt_row = facts.format if facts is not None else None
    if fmt_row is None:
        return out
    ks = pool_counts(n_pool, fmt_row.pool_min, fmt_row.pool_max)
    if not ks:
        out.update({"range": [fmt_row.pool_min, fmt_row.pool_max]})
        return out
    current = planning.published(session, tid)
    chosen = {
        int(str(c["discipline_id"])): (int(str(c["k"])), str(c["day"]))
        for c in (current.variant if current is not None else [])
    }
    published_k = chosen.get(discipline.id, (None, None))[0]
    k = (
        published_k
        if published_k in ks
        else min(ks, key=lambda x: (abs(x - (published_k or x)), x))
    )
    out.update(
        {
            "feasible": True,
            "k": k,
            "sizes": list(pool_sizes(n_pool, k)),
            "published_k": published_k,
        }
    )
    if current is None or facts is None:
        return out
    changed = replace(
        context.problem,
        disciplines=tuple(
            replace(d, n_pool=n_pool, n_bracket=len(found)) if d.id == discipline.id else d
            for d in context.problem.disciplines
        ),
    )
    choices: list[Choice] = []
    for discipline_id, (published, day) in chosen.items():
        index = context.index_of(datetime.fromisoformat(day).date())
        if index is None or not any(d.id == discipline_id for d in changed.disciplines):
            return out
        choices.append(
            Choice(
                discipline=discipline_id,
                k=k if discipline_id == discipline.id else published,
                day=index,
            )
        )
    after = evaluate(changed, choices)
    day = chosen[discipline.id][1] if discipline.id in chosen else None
    if after is None or day is None:
        out.update({"day": day, "end_change": None})
        return out
    index = context.index_of(datetime.fromisoformat(day).date())
    new_end = dict(after.metrics.last_end).get(index if index is not None else -1)
    stored = current.metrics.get("last_end")
    old = stored.get(day) if isinstance(stored, dict) else None
    if new_end is None or not isinstance(old, str):
        out.update({"day": day, "end_change": None})
        return out
    out.update({"day": day, "end_change": new_end - planning.clock_minutes(old)})
    return out


def close(
    session: Session,
    tid: int,
    roster: Roster,
    discipline: FloorDiscipline,
    by: int | None,
    now: datetime,
) -> FloorSnapshot:
    if closed(session, tid, discipline.id):
        raise Refused("checkin_closed")
    found = people.present(session, tid, roster, discipline)
    snap = FloorSnapshot(
        tournament_id=tid, discipline_id=discipline.id, closed_at=now, closed_by=by, n=len(found)
    )
    session.add(snap)
    session.flush()
    for entrant in found:
        session.add(
            FloorSnapshotEntrant(
                snapshot_id=snap.id,
                entrant_key=entrant.key,
                kind=entrant.kind,
                name=entrant.name,
                club=entrant.club,
                nationality=entrant.nationality,
                hr_id=entrant.hr_id,
                rating=entrant.rating,
                rank=entrant.rank,
                members=list(entrant.members),
            )
        )
    session.add(
        FloorPin(
            tournament_id=tid,
            kind="n",
            target=str(discipline.id),
            value={"n": len(found)},
            gate=gate_name(discipline.id),
            created_at=now,
            created_by=by,
        )
    )
    session.flush()
    return snap


def reopen_preview(session: Session, tid: int, discipline: int) -> dict[str, list[str]]:
    return {
        "invalidated": ["n_pin", "snapshot", *gates.invalidated(session, GATE, tid, discipline)],
        "refusals": gates.refusals(session, GATE, tid, discipline),
    }


def reopen(session: Session, tid: int, discipline: int) -> None:
    snap = people.snapshot(session, tid, discipline)
    if snap is None:
        raise Refused("checkin_open")
    refusing = gates.refusals(session, GATE, tid, discipline)
    if refusing:
        raise Refused("results_recorded", refusing)
    gates.discard(session, GATE, tid, discipline)
    session.execute(delete(FloorSnapshotEntrant).where(FloorSnapshotEntrant.snapshot_id == snap.id))
    session.delete(snap)
    session.execute(
        delete(FloorPin).where(
            FloorPin.tournament_id == tid, FloorPin.gate == gate_name(discipline)
        )
    )
    session.flush()


# ------------------------------------------------------------ waiting and state


def first_starts(session: Session, tid: int) -> dict[int, datetime]:
    """Each discipline's first planned start in the published plan."""
    current = planning.published(session, tid)
    if current is None:
        return {}
    out: dict[int, datetime] = {}
    for discipline_id, starts_at in session.execute(
        select(FloorPlanActivity.discipline_id, FloorPlanActivity.starts_at).where(
            FloorPlanActivity.plan_id == current.id
        )
    ).tuples():
        if discipline_id not in out or starts_at < out[discipline_id]:
            out[discipline_id] = starts_at
    return out


def waiting(session: Session, tournament: Tournament, now: datetime) -> list[int]:
    """Disciplines whose check-in is open within 30 minutes of their first
    planned activity (spec floor-checkin, Check-in badges)."""
    soon: list[int] = []
    for discipline_id, start in first_starts(session, tournament.id).items():
        aware = start if start.tzinfo is not None else start.replace(tzinfo=UTC)
        if aware - now <= SOON and not closed(session, tournament.id, discipline_id):
            soon.append(discipline_id)
    return sorted(soon)


def _state(session: Session, tid: int, discipline: int) -> str:
    return "closed" if closed(session, tid, discipline) else "open"


steps.register("checkin", _state)


# ------------------------------------------------------------ the desk's view


def desk(session: Session, tid: int, roster: Roster) -> dict[str, object]:
    """Every person once, with their entries; the disciplines with their
    counts and state; the teams with their lineups."""
    known = people.persons(session, tid, roster)
    here = people.arrived(session, tid)
    gone = people.withdrawn(session, tid)
    stated = people.lineups(session, tid)
    by_slug = {d.slug: d for d in roster.disciplines}
    entries: dict[str, list[dict[str, object]]] = {}
    for entry in roster.individuals:
        discipline = by_slug[entry.discipline]
        key = people.entry_key(entry.person, discipline.id)
        entries.setdefault(entry.person, []).append(
            {
                "entry_key": key,
                "discipline_id": discipline.id,
                "team": None,
                "paid": entry.paid,
                "withdrawn": key in gone,
            }
        )
    teams: list[dict[str, object]] = []
    for team in roster.teams:
        discipline = by_slug[team.discipline]
        lineup = people.lineup_of(team, stated)
        for member in lineup:
            entries.setdefault(member, []).append(
                {
                    "entry_key": team.key,
                    "discipline_id": discipline.id,
                    "team": team.name,
                    "paid": team.paid,
                    "withdrawn": team.key in gone,
                }
            )
        arrived_members = [k for k in lineup if k in here]
        least = discipline.team_min or 1
        teams.append(
            {
                "key": team.key,
                "discipline_id": discipline.id,
                "name": team.name,
                "members": list(team.members),
                "lineup": list(lineup),
                "present": len(arrived_members) >= least and team.key not in gone,
                "short_by": max(least - len(arrived_members), 0),
                "withdrawn": team.key in gone,
            }
        )
    persons = [
        {
            "key": key,
            "name": known[key].name,
            "club": known[key].club,
            "nationality": known[key].nationality,
            "local": key.startswith(people.LOCAL),
            "arrived": key in here,
            "entries": entries[key],
        }
        for key in sorted(entries, key=lambda k: (known[k].name.casefold(), k))
        if key in known
    ]
    disciplines: list[dict[str, object]] = []
    for discipline in roster.disciplines:
        snap = people.snapshot(session, tid, discipline.id)
        disciplines.append(
            {
                "id": discipline.id,
                "slug": discipline.slug,
                "name": discipline.name,
                "kind": discipline.kind,
                "team_min": discipline.team_min,
                "team_max": discipline.team_max,
                "closed": snap is not None,
                "closed_at": snap.closed_at if snap is not None else None,
                "entered": len(people.live(session, tid, roster, discipline)),
                "present": len(people.present(session, tid, roster, discipline)),
                "n": snap.n if snap is not None else None,
            }
        )
    return {"persons": persons, "disciplines": disciplines, "teams": teams}
