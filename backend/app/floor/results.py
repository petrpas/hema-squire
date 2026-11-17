"""Results: the final standing, its export and print, and the publish gate
(spec floor-results; design add-floor-results D1, D4)."""

import csv
import io
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.floor import bracket as brackets
from app.floor import people, poolbouts, steps
from app.floor.engine import standing as engine
from app.floor.models import FloorBout, FloorPool, FloorPublishedResult
from app.floor.pools import Refused, draw_of
from app.floor.roster import FloorDiscipline, Roster


def placed(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> list[dict[str, object]] | None:
    """The final standing with name, club and nationality; None until the
    bracket is closed."""
    row = brackets.bracket_of(session, tid, discipline.id)
    if row is None or row.closed_at is None:
        return None
    bouts = []
    for bout in brackets.bouts_of(session, row):
        winner = brackets._winner(bout)  # pyright: ignore[reportPrivateUsage]  # the bracket's own rule for who won
        if winner is not None and bout.round is not None and bout.position is not None:
            bouts.append(
                engine.EliminationBout(bout.round, bout.position, bout.a_key, bout.b_key, winner)
            )
    seeds = {
        s.entrant_key: s.seed
        for s in brackets.slots_of(session, row).values()
        if s.round == 0 and s.entrant_key is not None and s.seed is not None
    }
    if discipline.kind == "team":
        ranking = brackets.seeded_entrants(session, tid, roster, discipline)
    else:
        ranking = [r.entrant_key for r in poolbouts.ranking(session, tid, discipline.id)]
    places = engine.standing(
        bouts, row.size.bit_length() - 1, seeds, ranking, third_place=row.third_place
    )
    known = people.persons(session, tid, roster)
    teams = {t.key: t.name for t in roster.teams}
    out: list[dict[str, object]] = []
    for p in places:
        person = known.get(p.key)
        out.append(
            {
                "place": p.place,
                "key": p.key,
                "name": person.name if person else teams.get(p.key, p.key),
                "club": person.club if person else None,
                "nationality": person.nationality if person else None,
            }
        )
    return out


def published(session: Session, tid: int, discipline: int) -> FloorPublishedResult | None:
    return session.scalar(
        select(FloorPublishedResult).where(
            FloorPublishedResult.tournament_id == tid,
            FloorPublishedResult.discipline_id == discipline,
        )
    )


def publish(session: Session, tid: int, discipline: int, by: int | None, now: datetime) -> None:
    """ "Zveřejnit výsledky": offered once the bracket is closed."""
    row = brackets.bracket_of(session, tid, discipline)
    if row is None or row.closed_at is None:
        raise Refused("bracket_open")
    if published(session, tid, discipline) is None:
        session.add(
            FloorPublishedResult(
                tournament_id=tid, discipline_id=discipline, published_at=now, published_by=by
            )
        )
        session.flush()


def withdraw(session: Session, tid: int, discipline: int) -> None:
    session.execute(
        delete(FloorPublishedResult).where(
            FloorPublishedResult.tournament_id == tid,
            FloorPublishedResult.discipline_id == discipline,
        )
    )


def csv_export(session: Session, tid: int, roster: Roster, discipline: FloorDiscipline) -> str:
    """The standing, then every bout with its pool or round, both entrants,
    the scores and the outcomes."""
    out = io.StringIO()
    writer = csv.writer(out)
    known = people.persons(session, tid, roster)
    teams = {t.key: t.name for t in roster.teams}

    def name(key: str) -> str:
        person = known.get(key)
        return person.name if person else teams.get(key, key)

    writer.writerow(["place", "name", "club", "nationality"])
    for row in placed(session, tid, roster, discipline) or []:
        writer.writerow([row["place"], row["name"], row["club"] or "", row["nationality"] or ""])
    writer.writerow([])
    writer.writerow(
        ["stage", "bout", "a", "b", "score_a", "score_b", "outcome_a", "outcome_b", "note"]
    )
    draw = draw_of(session, tid, discipline.id)
    numbers = (
        {
            p.id: p.number
            for p in session.scalars(select(FloorPool).where(FloorPool.draw_id == draw.id))
        }
        if draw is not None
        else {}
    )
    bouts = session.scalars(
        select(FloorBout)
        .where(
            FloorBout.tournament_id == tid,
            FloorBout.discipline_id == discipline.id,
            FloorBout.recorded_at.is_not(None),
        )
        .order_by(
            FloorBout.pool_id.is_(None), FloorBout.pool_id, FloorBout.round, FloorBout.ordinal
        )
    )
    for bout in bouts:
        stage = (
            f"pool {numbers.get(bout.pool_id, '?')}"
            if bout.pool_id is not None
            else f"round {(bout.round or 0) + 1}"
        )
        writer.writerow(
            [
                stage,
                bout.ordinal,
                name(bout.a_key),
                name(bout.b_key),
                bout.score_a,
                bout.score_b,
                bout.outcome_a,
                bout.outcome_b,
                bout.note or "",
            ]
        )
    return out.getvalue()


def _state(session: Session, tid: int, discipline: int) -> str:
    """Výsledky on `today`: waiting, or published."""
    return "published" if published(session, tid, discipline) is not None else "waiting"


steps.register("results", _state)
