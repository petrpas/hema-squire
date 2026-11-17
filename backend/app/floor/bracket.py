"""The elimination (spec floor-bracket; design add-floor-bracket D2–D4).

Proposed from the closed pool ranking, frozen by "Potvrdit postup". A
recorded bout places its winner in the next round in the same transaction;
a correction that would change a winner is refused once the bout it fed is
recorded. The bracket closes when its final, and third-place bout, are in.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.floor import gates, people, planning, poolbouts, progress, steps
from app.floor.engine import bracket as engine
from app.floor.engine.structure import advancing
from app.floor.models import (
    FloorBout,
    FloorBracket,
    FloorBracketSlot,
    FloorFormat,
    FloorPlanActivity,
)
from app.floor.poolbouts import Result
from app.floor.pools import Refused, draw_of
from app.floor.roster import FloorDiscipline, Roster

GATE = "bracket"
THIRD = 1


def bracket_of(session: Session, tid: int, discipline: int) -> FloorBracket | None:
    return session.scalar(
        select(FloorBracket).where(
            FloorBracket.tournament_id == tid, FloorBracket.discipline_id == discipline
        )
    )


def slots_of(session: Session, bracket: FloorBracket) -> dict[tuple[int, int], FloorBracketSlot]:
    return {
        (s.round, s.position): s
        for s in session.scalars(
            select(FloorBracketSlot).where(FloorBracketSlot.bracket_id == bracket.id)
        )
    }


def bouts_of(session: Session, bracket: FloorBracket) -> list[FloorBout]:
    return list(
        session.scalars(
            select(FloorBout)
            .where(FloorBout.bracket_id == bracket.id)
            .order_by(FloorBout.round, FloorBout.position)
        )
    )


# ------------------------------------------------------------ who, in what order


def seeded_entrants(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> list[str]:
    """Entrant keys in seed order from the frozen pool ranking: persons as
    ranked, or teams by the average place of their best k members."""
    ranking = poolbouts.ranking(session, tid, discipline.id)
    if discipline.kind != "team":
        return [row.entrant_key for row in ranking]
    place = {row.entrant_key: row.place for row in ranking}
    k = discipline.team_min or 1
    figures: list[engine.TeamFigure] = []
    for team in people.entrants(session, tid, roster, discipline):
        figure = engine.team_figure(team.key, [place[m] for m in team.members if m in place], k)
        if figure is not None:
            figures.append(figure)
    return engine.seed_teams(figures)


def _shape(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> tuple[list[str], int, int, bool]:
    draw = draw_of(session, tid, discipline.id)
    if draw is None or draw.closed_at is None:
        raise Refused("pools_open")
    keys = seeded_entrants(session, tid, roster, discipline)
    fmt = session.scalar(select(FloorFormat).where(FloorFormat.discipline_id == discipline.id))
    count = (
        len(keys)
        if discipline.kind == "team"
        else advancing(len(keys), fmt.advance if fmt is not None else None)
    )
    if count < 2:
        raise Refused("too_few")
    size = 2
    while size < count:
        size *= 2
    return keys[:count], size, count, bool(fmt.third_place) if fmt is not None else False


def propose(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> dict[str, object]:
    """The seeded bracket before it is confirmed: its size, who advances and
    their first-round slots."""
    keys, size, count, _ = _shape(session, tid, roster, discipline)
    return {
        "size": size,
        "advancing": count,
        "slots": [
            {
                "position": slot.position,
                "seed": slot.seed,
                "key": keys[slot.seed - 1] if slot.seed is not None else None,
            }
            for slot in engine.first_round(size, count)
        ],
    }


# ------------------------------------------------------------ the gate


def _planned(session: Session, tid: int, discipline: int) -> dict[str, int]:
    """The published plan's elimination activities' pistes, by activity id."""
    current = planning.published(session, tid)
    if current is None:
        return {}
    return dict(
        session.execute(
            select(FloorPlanActivity.activity_id, FloorPlanActivity.piste_id).where(
                FloorPlanActivity.plan_id == current.id,
                FloorPlanActivity.discipline_id == discipline,
                FloorPlanActivity.kind == "bout",
            )
        )
        .tuples()
        .all()
    )


def activity_id(slug: str, bracket: FloorBracket, bout: FloorBout, session: Session) -> str:
    """The plan's id for an elimination bout: "SB:r2:1", "SB:third"."""
    if bout.round == engine.rounds(bracket.size) - 1 and bout.position == THIRD:
        return f"{slug}:third"
    same = [
        b
        for b in bouts_of(session, bracket)
        if b.round == bout.round
        and not (b.round == engine.rounds(bracket.size) - 1 and b.position == THIRD)
    ]
    ordinal = 1 + sorted(b.position or 0 for b in same).index(bout.position or 0)
    return f"{slug}:r{(bout.round or 0) + 1}:{ordinal}"


def confirm(
    session: Session,
    tid: int,
    roster: Roster,
    discipline: FloorDiscipline,
    by: int | None,
    now: datetime,
) -> FloorBracket:
    """ "Potvrdit postup": freeze the seeded bracket, pass the byes through,
    and write the first bouts."""
    if bracket_of(session, tid, discipline.id) is not None:
        raise Refused("bracket_confirmed")
    keys, size, count, third = _shape(session, tid, roster, discipline)
    row = FloorBracket(
        tournament_id=tid,
        discipline_id=discipline.id,
        size=size,
        advancing=count,
        third_place=third and size >= 4,
        confirmed_at=now,
        confirmed_by=by,
    )
    session.add(row)
    session.flush()
    for slot in engine.first_round(size, count):
        session.add(
            FloorBracketSlot(
                bracket_id=row.id,
                round=0,
                position=slot.position,
                entrant_key=keys[slot.seed - 1] if slot.seed is not None else None,
                seed=slot.seed,
                bye=slot.seed is None,
            )
        )
    session.flush()
    slots = slots_of(session, row)
    # a bye's opponent goes straight through
    for match in range(size // 2):
        a, b = slots[(0, 2 * match)], slots[(0, 2 * match + 1)]
        if a.bye or b.bye:
            through = b if a.bye else a
            _put(session, row, 1, match, through.entrant_key, through.seed)
    _write_bouts(session, row, discipline)
    return row


def _put(
    session: Session,
    bracket: FloorBracket,
    round_: int,
    position: int,
    key: str | None,
    seed: int | None,
) -> None:
    slot = slots_of(session, bracket).get((round_, position))
    if slot is None:
        session.add(
            FloorBracketSlot(
                bracket_id=bracket.id, round=round_, position=position, entrant_key=key, seed=seed
            )
        )
    else:
        slot.entrant_key = key
        slot.seed = seed
    session.flush()


def _write_bouts(session: Session, bracket: FloorBracket, discipline: FloorDiscipline) -> None:
    """A bout for every match whose two slots are filled and that has none;
    an unrecorded bout follows a slot that changed."""
    slots = slots_of(session, bracket)
    existing = {(b.round, b.position): b for b in bouts_of(session, bracket)}
    planned = _planned(session, bracket.tournament_id, discipline.id)
    last = engine.rounds(bracket.size) - 1
    for round_ in range(last + 1):
        for match in range(bracket.size // 2 ** (round_ + 1)):
            a = slots.get((round_, 2 * match))
            b = slots.get((round_, 2 * match + 1))
            if a is None or b is None or a.bye or b.bye or not a.entrant_key or not b.entrant_key:
                continue
            _bout(
                session,
                bracket,
                discipline,
                existing,
                planned,
                round_,
                match,
                a.entrant_key,
                b.entrant_key,
            )
    if bracket.third_place and last >= 1:
        losers = [_loser(session, existing.get((last - 1, m))) for m in (0, 1)]
        if losers[0] and losers[1]:
            _bout(
                session, bracket, discipline, existing, planned, last, THIRD, losers[0], losers[1]
            )
    session.flush()


def _bout(
    session: Session,
    bracket: FloorBracket,
    discipline: FloorDiscipline,
    existing: dict[tuple[int | None, int | None], FloorBout],
    planned: dict[str, int],
    round_: int,
    position: int,
    a: str,
    b: str,
) -> None:
    bout = existing.get((round_, position))
    if bout is None:
        bout = FloorBout(
            tournament_id=bracket.tournament_id,
            discipline_id=discipline.id,
            bracket_id=bracket.id,
            round=round_,
            position=position,
            ordinal=position + 1,
            a_key=a,
            b_key=b,
            version=0,
        )
        session.add(bout)
        session.flush()
        bout.piste_id = planned.get(activity_id(discipline.slug, bracket, bout, session))
        existing[(round_, position)] = bout
    elif bout.recorded_at is None:
        bout.a_key, bout.b_key = a, b


def _winner(bout: FloorBout | None) -> str | None:
    if bout is None or bout.recorded_at is None:
        return None
    a_wins = bout.outcome_a == "win" or bout.outcome_b == "no"
    return bout.a_key if a_wins else bout.b_key


def _loser(session: Session, bout: FloorBout | None) -> str | None:
    winner = _winner(bout)
    if bout is None or winner is None:
        return None
    return bout.b_key if winner == bout.a_key else bout.a_key


# ------------------------------------------------------------ recording


def record(
    session: Session,
    tid: int,
    bout_id: int,
    result: Result,
    version: int,
    by: str,
    now: datetime,
    discipline: FloorDiscipline,
    *,
    piste: int | None = None,
) -> FloorBout:
    bout = session.get(FloorBout, bout_id)
    if bout is None or bout.tournament_id != tid or bout.bracket_id is None:
        raise Refused("bout_not_found")
    bracket = session.get(FloorBracket, bout.bracket_id)
    if bracket is None:
        raise Refused("bout_not_found")
    if piste is not None and bout.piste_id != piste:
        raise Refused("not_this_piste")
    if bout.version != version:
        raise Refused("stale_version")
    if "draw" in (result.outcome_a, result.outcome_b):
        raise Refused("draw_refused")
    no_a, no_b = result.outcome_a == "no", result.outcome_b == "no"
    if no_a and no_b:
        raise Refused("draw_refused")
    if (no_a or no_b) and not result.note:
        raise Refused("walkover_note")
    wins_a = result.outcome_a == "win" or no_b
    wins_b = result.outcome_b == "win" or no_a
    if wins_a == wins_b:
        raise Refused("winner_required")
    new_winner = bout.a_key if wins_a else bout.b_key
    old_winner = _winner(bout)
    if old_winner is not None and old_winner != new_winner:
        fed = _fed(session, bracket, bout)
        if fed:
            raise Refused("next_recorded", fed)
    bout.score_a, bout.score_b = result.score_a, result.score_b
    bout.outcome_a, bout.outcome_b = result.outcome_a, result.outcome_b
    bout.note = result.note or None
    bout.recorded_at, bout.recorded_by = now, by
    bout.version += 1
    session.flush()
    last = engine.rounds(bracket.size) - 1
    if bout.round is not None and bout.position is not None and bout.round < last:
        seed = slots_of(session, bracket).get(
            (bout.round, 2 * bout.position if new_winner == bout.a_key else 2 * bout.position + 1)
        )
        _put(
            session,
            bracket,
            bout.round + 1,
            bout.position,
            new_winner,
            seed.seed if seed else None,
        )
    _write_bouts(session, bracket, discipline)
    _close_if_done(session, bracket, now)
    return bout


def _fed(session: Session, bracket: FloorBracket, bout: FloorBout) -> list[str]:
    """Recorded bouts that this bout's result fed: the next round's, and the
    third place where a semifinal is corrected."""
    if bout.round is None or bout.position is None:
        return []
    last = engine.rounds(bracket.size) - 1
    found: list[str] = []
    for other in bouts_of(session, bracket):
        if other.recorded_at is None:
            continue
        if other.round == bout.round + 1 and other.position == engine.feeds(bout.position):
            found.append(f"r{(other.round or 0) + 1}:{(other.position or 0) + 1}")
        if bout.round == last - 1 and other.round == last and other.position == THIRD:
            found.append("third")
    return found


def _close_if_done(session: Session, bracket: FloorBracket, now: datetime) -> None:
    last = engine.rounds(bracket.size) - 1
    bouts = {(b.round, b.position): b for b in bouts_of(session, bracket)}
    final = bouts.get((last, 0))
    third = bouts.get((last, THIRD))
    done = (
        final is not None
        and final.recorded_at is not None
        and (not bracket.third_place or (third is not None and third.recorded_at is not None))
    )
    bracket.closed_at = now if done else None
    session.flush()


def state(session: Session, tid: int, discipline: int) -> str:
    """waiting | seeded | running | closed (spec floor-bracket)."""
    bracket = bracket_of(session, tid, discipline)
    if bracket is None:
        return "waiting"
    if bracket.closed_at is not None:
        return "closed"
    if any(b.recorded_at is not None for b in bouts_of(session, bracket)):
        return "running"
    return "seeded"


def recorded(session: Session, tid: int, discipline: int) -> list[str]:
    bracket = bracket_of(session, tid, discipline)
    if bracket is None:
        return []
    return [
        f"r{(b.round or 0) + 1}:{(b.position or 0) + 1}"
        for b in bouts_of(session, bracket)
        if b.recorded_at is not None
    ]


def discard(session: Session, tid: int, discipline: int) -> None:
    bracket = bracket_of(session, tid, discipline)
    if bracket is None:
        return
    session.execute(delete(FloorBout).where(FloorBout.bracket_id == bracket.id))
    session.execute(delete(FloorBracketSlot).where(FloorBracketSlot.bracket_id == bracket.id))
    session.delete(bracket)
    session.flush()


def reopen(session: Session, tid: int, discipline: int) -> None:
    """Unconfirm the advancement; refused once any bout has a result."""
    if bracket_of(session, tid, discipline) is None:
        raise Refused("bracket_not_confirmed")
    refusing = recorded(session, tid, discipline)
    if refusing:
        raise Refused("results_recorded", refusing)
    discard(session, tid, discipline)


def _started(session: Session, tid: int, now: datetime) -> set[str]:
    found: set[str] = set()
    for bracket in session.scalars(select(FloorBracket).where(FloorBracket.tournament_id == tid)):
        # the plan spells activity ids with the discipline's slug
        some = session.scalar(
            select(FloorPlanActivity.activity_id).where(
                FloorPlanActivity.discipline_id == bracket.discipline_id
            )
        )
        if some is None:
            continue
        slug = some.split(":")[0]
        for bout in bouts_of(session, bracket):
            if bout.recorded_at is not None:
                found.add(activity_id(slug, bracket, bout, session))
    return found


gates.register(
    "pools",
    gates.Hook(
        describe=lambda session, tid, d: ["bracket"] if bracket_of(session, tid, d) else [],
        discard=discard,
        refuse=recorded,
    ),
)
progress.register(_started)
steps.register("bracket", state)
