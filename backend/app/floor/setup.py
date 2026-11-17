"""Floor Setup: scope, days, pistes, formats, officials, parameters and the
plan's preferences (spec floor-setup; design add-floor-console D3, design
rework-floor-setup D2–D7).

Each section is read with its defaults and saved whole, after every field of
it is checked: a save is refused with field-level errors, never partially
stored. Disciplines and persons come from the roster port, so nothing here
reads an office table.

What scope hides stays stored. `effective` is the one view every reader
(badges, planner, officials) takes, with what scope hides left out.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, time

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.errors import FieldValidationError
from app.floor.models import (
    FloorAssignment,
    FloorDay,
    FloorDisciplineDay,
    FloorFormat,
    FloorOfficial,
    FloorOfficialDay,
    FloorOfficialDiscipline,
    FloorPiste,
    FloorPisteDiscipline,
    FloorSettings,
)
from app.floor.roster import FloorDiscipline
from app.floor.schemas import (
    BreakIO,
    DayIO,
    DaysOut,
    FormatIn,
    FormatOut,
    OfficialIn,
    OfficialOut,
    ParamsIO,
    PisteIn,
    PisteOut,
    PreferencesIO,
    ScopeIO,
    ServesIO,
)

DEFAULT_START = "09:00"
DEFAULT_END = "19:00"


@dataclass(frozen=True)
class Tournament:
    """What Setup needs to know of the tournament, from the roster port."""

    id: int
    date: date
    disciplines: tuple[FloorDiscipline, ...]
    # the IANA zone its wall-clock times are read in
    timezone: str = "Europe/Prague"


def _clock(value: time) -> str:
    return value.strftime("%H:%M")


def _time(clock: str) -> time:
    return time.fromisoformat(clock)


def _settings(session: Session, tid: int) -> FloorSettings:
    return session.get(FloorSettings, tid) or FloorSettings(
        tournament_id=tid, params={}, plan_schedule=True, multi_day=False, plan_officials=False
    )


# ------------------------------------------------------------ scope


def read_scope(session: Session, tid: int) -> ScopeIO:
    row = session.get(FloorSettings, tid)
    if row is None:
        return ScopeIO()
    return ScopeIO(
        plan_schedule=row.plan_schedule,
        multi_day=row.multi_day,
        plan_officials=row.plan_officials,
    )


def save_scope(session: Session, tid: int, scope: ScopeIO) -> None:
    """Officials and several days need the schedule; one day is refused while
    several are stated (spec floor-setup, Scope decides what is planned)."""
    errors: list[dict] = []
    if scope.plan_officials and not scope.plan_schedule:
        errors.append({"field": "plan_officials", "code": "needs_schedule"})
    if scope.multi_day and not scope.plan_schedule:
        errors.append({"field": "multi_day", "code": "needs_schedule"})
    if not scope.multi_day and len(_stored_days(session, tid)) > 1:
        errors.append({"field": "multi_day", "code": "several_days"})
    if errors:
        raise FieldValidationError(errors)
    row = _settings(session, tid)
    row.plan_schedule = scope.plan_schedule
    row.multi_day = scope.multi_day
    row.plan_officials = scope.plan_officials
    session.add(row)
    session.flush()


# ------------------------------------------------------------ days


def _stored_days(session: Session, tid: int) -> list[FloorDay]:
    return list(
        session.scalars(
            select(FloorDay).where(FloorDay.tournament_id == tid).order_by(FloorDay.date)
        )
    )


def _default_day(tournament: Tournament) -> DayIO:
    return DayIO(
        date=tournament.date,
        start=DEFAULT_START,
        end=DEFAULT_END,
        breaks=[],
        discipline_ids=[d.id for d in tournament.disciplines],
    )


def _stored_discipline_days(session: Session, tournament: Tournament) -> dict[int, int]:
    """Discipline id → day id, as stored."""
    ids = [d.id for d in tournament.disciplines]
    return dict(
        session.execute(
            select(FloorDisciplineDay.discipline_id, FloorDisciplineDay.day_id).where(
                FloorDisciplineDay.discipline_id.in_(ids)
            )
        )
        .tuples()
        .all()
    )


def discipline_days(session: Session, tournament: Tournament) -> dict[int, int]:
    """Discipline id → day id, as the floor reads it: on a one-day tournament
    every discipline is on its day; otherwise as ticked, a dayless discipline
    absent."""
    days = _stored_days(session, tournament.id)
    if not days:
        return {}
    if not read_scope(session, tournament.id).multi_day:
        return {d.id: days[0].id for d in tournament.disciplines}
    known = {day.id for day in days}
    return {
        d: day for d, day in _stored_discipline_days(session, tournament).items() if day in known
    }


def read_days(session: Session, tournament: Tournament) -> DaysOut:
    stored = _stored_days(session, tournament.id)
    if not stored:
        return DaysOut(stored=False, days=[_default_day(tournament)])
    on = discipline_days(session, tournament)
    order = [d.id for d in tournament.disciplines]
    return DaysOut(
        stored=True,
        days=[
            DayIO(
                date=day.date,
                start=_clock(day.start),
                end=_clock(day.end),
                breaks=[BreakIO(start=a, end=b) for a, b in day.breaks],
                discipline_ids=[d for d in order if on.get(d) == day.id],
            )
            for day in stored
        ],
    )


def _day_errors(days: Sequence[DayIO], known: set[int], multi_day: bool) -> list[dict]:
    errors: list[dict] = []
    if not days:
        errors.append({"field": "days", "code": "required"})
    if len(days) > 1 and not multi_day:
        errors.append({"field": "days", "code": "single_day"})
    seen: set[date] = set()
    placed: set[int] = set()
    for i, day in enumerate(days):
        if day.date in seen:
            errors.append({"field": f"{i}.date", "code": "duplicate"})
        seen.add(day.date)
        for j, discipline_id in enumerate(day.discipline_ids):
            if discipline_id not in known:
                errors.append({"field": f"{i}.discipline_ids.{j}", "code": "unknown_discipline"})
            elif discipline_id in placed:
                errors.append({"field": f"{i}.discipline_ids.{j}", "code": "two_days"})
            placed.add(discipline_id)
        if day.start >= day.end:
            errors.append({"field": f"{i}.end", "code": "end_not_after_start"})
            continue
        spans = sorted((b.start, b.end, j) for j, b in enumerate(day.breaks))
        previous_end: str | None = None
        for start, end, j in spans:
            if start >= end:
                errors.append({"field": f"{i}.breaks.{j}.end", "code": "end_not_after_start"})
            elif start < day.start or end > day.end:
                errors.append({"field": f"{i}.breaks.{j}", "code": "break_outside_day"})
            elif previous_end is not None and start < previous_end:
                errors.append({"field": f"{i}.breaks.{j}", "code": "breaks_overlap"})
            previous_end = end if previous_end is None else max(previous_end, end)
    return errors


def _take_over_order_errors(
    sources: Mapping[int, int | None], on: Mapping[int, date], field_of: Mapping[int, str]
) -> list[dict]:
    """A target held before its source cannot seed from it."""
    errors: list[dict] = []
    for target, source in sources.items():
        if source is None or target not in on or source not in on:
            continue
        if on[target] < on[source] and target in field_of:
            errors.append({"field": field_of[target], "code": "before_source"})
    return errors


def _sources(session: Session, tid: int) -> dict[int, int | None]:
    return dict(
        session.execute(
            select(FloorFormat.discipline_id, FloorFormat.takes_pools_from).where(
                FloorFormat.tournament_id == tid
            )
        )
        .tuples()
        .all()
    )


def save_days(session: Session, tournament: Tournament, days: Sequence[DayIO]) -> None:
    """Replace the days and which discipline each holds. A day kept by its
    date keeps its id, so the officials available on it stay so; a day
    dropped takes their availability on it, and its disciplines' day, along."""
    multi_day = read_scope(session, tournament.id).multi_day
    known = {d.id for d in tournament.disciplines}
    errors = _day_errors(days, known, multi_day)
    if not errors and multi_day:
        on = {d: day.date for day in days for d in day.discipline_ids}
        field_of = {
            d: f"{i}.discipline_ids.{j}"
            for i, day in enumerate(days)
            for j, d in enumerate(day.discipline_ids)
        }
        errors = _take_over_order_errors(_sources(session, tournament.id), on, field_of)
    if errors:
        raise FieldValidationError(errors)
    _write_days(session, tournament, days, multi_day)


def _write_days(
    session: Session, tournament: Tournament, days: Sequence[DayIO], multi_day: bool
) -> None:
    stored = {day.date: day for day in _stored_days(session, tournament.id)}
    wanted = {day.date: day for day in days}
    ids = [d.id for d in tournament.disciplines]
    session.execute(delete(FloorDisciplineDay).where(FloorDisciplineDay.discipline_id.in_(ids)))
    for gone in stored.keys() - wanted.keys():
        row = stored[gone]
        session.execute(delete(FloorOfficialDay).where(FloorOfficialDay.day_id == row.id))
        session.delete(row)
    session.flush()
    for when, day in wanted.items():
        row = stored.get(when) or FloorDay(tournament_id=tournament.id, date=when)
        row.start = _time(day.start)
        row.end = _time(day.end)
        row.breaks = [[b.start, b.end] for b in sorted(day.breaks, key=lambda b: b.start)]
        session.add(row)
        session.flush()
        # one day holds them all; the ticks are kept for when several days return
        held = ids if not multi_day else day.discipline_ids
        for discipline_id in dict.fromkeys(held):
            session.add(FloorDisciplineDay(discipline_id=discipline_id, day_id=row.id))
    session.flush()


def _day_ids(session: Session, tournament: Tournament) -> dict[date, int]:
    """The stored days by date. A section naming days before any day was saved
    names the offered default, so it is stored first."""
    stored = _stored_days(session, tournament.id)
    if not stored:
        _write_days(session, tournament, [_default_day(tournament)], multi_day=False)
        stored = _stored_days(session, tournament.id)
    return {day.date: day.id for day in stored}


def _unknown_days(field: str, wanted: Sequence[date], known: dict[date, int]) -> list[dict]:
    return [
        {"field": f"{field}.{j}", "code": "unknown_day"}
        for j, when in enumerate(wanted)
        if when not in known
    ]


# ------------------------------------------------------------ serving


def _serves_errors(field: str, serves: Sequence[ServesIO], known: set[int]) -> list[dict]:
    errors: list[dict] = []
    seen: set[int] = set()
    for j, served in enumerate(serves):
        if served.discipline_id not in known:
            errors.append({"field": f"{field}.{j}", "code": "unknown_discipline"})
        elif served.discipline_id in seen:
            errors.append({"field": f"{field}.{j}", "code": "duplicate"})
        seen.add(served.discipline_id)
    return errors


def _serves_of(
    session: Session,
    model: type[FloorPisteDiscipline] | type[FloorOfficialDiscipline],
    ids: list[int],
) -> dict[int, list[ServesIO]]:
    owner = (
        FloorPisteDiscipline.piste_id
        if model is FloorPisteDiscipline
        else FloorOfficialDiscipline.official_id
    )
    out: dict[int, list[ServesIO]] = {}
    for owner_id, discipline_id, reserve in session.execute(
        select(owner, model.discipline_id, model.reserve)
        .where(owner.in_(ids))
        .order_by(owner, model.discipline_id)
    ).tuples():
        out.setdefault(owner_id, []).append(ServesIO(discipline_id=discipline_id, reserve=reserve))
    return out


# ------------------------------------------------------------ pistes


def read_pistes(session: Session, tid: int) -> list[PisteOut]:
    pistes = session.scalars(
        select(FloorPiste).where(FloorPiste.tournament_id == tid).order_by(FloorPiste.ordinal)
    ).all()
    serves = _serves_of(session, FloorPisteDiscipline, [p.id for p in pistes])
    return [PisteOut(id=p.id, name=p.name, serves=serves.get(p.id, [])) for p in pistes]


def _owned(session: Session, model: type[FloorPiste] | type[FloorOfficial], tid: int) -> dict:
    return {row.id: row for row in session.scalars(select(model).where(model.tournament_id == tid))}


def save_pistes(session: Session, tournament: Tournament, pistes: Sequence[PisteIn]) -> None:
    """Replace the pistes, in the order given, with the disciplines each serves."""
    stored: dict[int, FloorPiste] = _owned(session, FloorPiste, tournament.id)
    known = {d.id for d in tournament.disciplines}
    errors: list[dict] = []
    names: set[str] = set()
    for i, piste in enumerate(pistes):
        folded = piste.name.casefold()
        if folded in names:
            errors.append({"field": f"{i}.name", "code": "duplicate"})
        names.add(folded)
        if piste.id is not None and piste.id not in stored:
            errors.append({"field": f"{i}.id", "code": "not_found"})
        errors += _serves_errors(f"{i}.serves", piste.serves, known)
    if errors:
        raise FieldValidationError(errors)

    kept = {p.id for p in pistes if p.id is not None}
    gone = [row.id for pid, row in stored.items() if pid not in kept]
    if gone:
        session.execute(delete(FloorPisteDiscipline).where(FloorPisteDiscipline.piste_id.in_(gone)))
        session.execute(delete(FloorPiste).where(FloorPiste.id.in_(gone)))
    # names are unique per tournament: park the kept ones first, so a swap of
    # two names does not trip the constraint half way
    for row in stored.values():
        if row.id in kept:
            row.name = f"\x00{row.id}"
    session.flush()
    for ordinal, piste in enumerate(pistes, start=1):
        row = stored[piste.id] if piste.id is not None else FloorPiste(tournament_id=tournament.id)
        row.name = piste.name
        row.ordinal = ordinal
        session.add(row)
        session.flush()
        session.execute(delete(FloorPisteDiscipline).where(FloorPisteDiscipline.piste_id == row.id))
        for served in piste.serves:
            session.add(
                FloorPisteDiscipline(
                    piste_id=row.id, discipline_id=served.discipline_id, reserve=served.reserve
                )
            )
    session.flush()


# ------------------------------------------------------------ formats


def _default_format(discipline: FloorDiscipline) -> FormatIn:
    team = discipline.kind == "team"
    return FormatIn(
        discipline_id=discipline.id,
        pool_min=5,
        pool_max=7,
        advance=None,
        third_place=True,
        referees_pool=1,
        referees_elim=1,
        slot_pool_bout=4,
        slot_elim_bout=6,
        pause_between_pools=10,
        slot_team_match=25 if team else None,
        # starting values (owner decision 2026-11-17); a team's are stated
        points_pool=5,
        points_elim=None if team else 7,
        points_final=None if team else 7,
    )


def same_weapon(a: FloorDiscipline, b: FloorDiscipline) -> bool:
    return a.weapon.strip().casefold() == b.weapon.strip().casefold()


def _take_over_code(
    target: FloorDiscipline,
    source_id: int | None,
    by_id: Mapping[int, FloorDiscipline],
    sources: Mapping[int, int | None],
) -> str | None:
    """Why a take-over cannot stand, or None (spec floor-setup, A discipline
    may take over another discipline's pool results)."""
    if source_id is None:
        return None
    source = by_id.get(source_id)
    if source is None:
        return "unknown_discipline"
    if source.id == target.id:
        return "self"
    if not same_weapon(target, source):
        return "other_weapon"
    if sources.get(source.id) is not None:
        return "source_takes_over"
    return None


def read_formats(session: Session, tournament: Tournament) -> list[FormatOut]:
    stored = {
        row.discipline_id: row
        for row in session.scalars(
            select(FloorFormat).where(FloorFormat.tournament_id == tournament.id)
        )
    }
    by_id = {d.id: d for d in tournament.disciplines}
    sources = {d: row.takes_pools_from for d, row in stored.items()}
    out: list[FormatOut] = []
    for discipline in tournament.disciplines:
        row = stored.get(discipline.id)
        if row is None:
            fmt = _default_format(discipline)
            out.append(FormatOut(**fmt.model_dump(), stored=False, missing=["format"]))
            continue
        broken = _take_over_code(discipline, row.takes_pools_from, by_id, sources)
        out.append(
            FormatOut(
                discipline_id=discipline.id,
                pool_min=row.pool_min,
                pool_max=row.pool_max,
                advance=row.advance,
                third_place=row.third_place,
                referees_pool=row.referees_pool,
                referees_elim=row.referees_elim,
                slot_pool_bout=row.slot_pool_bout,
                slot_elim_bout=row.slot_elim_bout,
                pause_between_pools=row.pause_between_pools,
                slot_team_match=row.slot_team_match,
                points_pool=row.points_pool,
                points_elim=row.points_elim,
                points_final=row.points_final,
                points_team_bout=row.points_team_bout,
                points_team_final=row.points_team_final,
                takes_pools_from=row.takes_pools_from,
                stored=True,
                missing=["take_over"] if broken is not None else [],
            )
        )
    return out


def save_formats(session: Session, tournament: Tournament, formats: Sequence[FormatIn]) -> None:
    """Store the formats given; disciplines not named keep theirs."""
    by_id = {d.id: d for d in tournament.disciplines}
    sources = _sources(session, tournament.id)
    sources.update({f.discipline_id: f.takes_pools_from for f in formats})
    errors: list[dict] = []
    seen: set[int] = set()
    for i, fmt in enumerate(formats):
        discipline = by_id.get(fmt.discipline_id)
        if discipline is None:
            errors.append({"field": f"{i}.discipline_id", "code": "unknown_discipline"})
            continue
        if fmt.discipline_id in seen:
            errors.append({"field": f"{i}.discipline_id", "code": "duplicate"})
        seen.add(fmt.discipline_id)
        if fmt.pool_min > fmt.pool_max:
            errors.append(
                {"field": f"{i}.pool_min", "code": "above_max", "params": {"max": fmt.pool_max}}
            )
        team = discipline.kind == "team"
        if team and fmt.slot_team_match is None:
            errors.append({"field": f"{i}.slot_team_match", "code": "required"})
        for name in ("points_elim", "points_final"):
            if team and getattr(fmt, name) is not None:
                errors.append({"field": f"{i}.{name}", "code": "team_discipline"})
        for name in ("points_team_bout", "points_team_final"):
            if not team and getattr(fmt, name) is not None:
                errors.append({"field": f"{i}.{name}", "code": "individual_discipline"})
        code = _take_over_code(discipline, fmt.takes_pools_from, by_id, sources)
        if code is None and fmt.takes_pools_from is not None:
            # someone else takes over from this one: a chain, refused here too
            if any(src == discipline.id for t, src in sources.items() if t != discipline.id):
                code = "source_takes_over"
        if code is not None:
            errors.append({"field": f"{i}.takes_pools_from", "code": code})
    if not errors and read_scope(session, tournament.id).multi_day:
        days = {day.id: day.date for day in _stored_days(session, tournament.id)}
        on = {
            d: days[day]
            for d, day in _stored_discipline_days(session, tournament).items()
            if day in days
        }
        field_of = {f.discipline_id: f"{i}.takes_pools_from" for i, f in enumerate(formats)}
        errors = _take_over_order_errors(sources, on, field_of)
    if errors:
        raise FieldValidationError(errors)

    stored = {
        row.discipline_id: row
        for row in session.scalars(
            select(FloorFormat).where(FloorFormat.tournament_id == tournament.id)
        )
    }
    for fmt in formats:
        row = stored.get(fmt.discipline_id) or FloorFormat(
            tournament_id=tournament.id, discipline_id=fmt.discipline_id
        )
        team = by_id[fmt.discipline_id].kind == "team"
        row.pool_min = fmt.pool_min
        row.pool_max = fmt.pool_max
        row.advance = fmt.advance
        row.third_place = fmt.third_place
        row.referees_pool = fmt.referees_pool
        row.referees_elim = fmt.referees_elim
        row.slot_pool_bout = fmt.slot_pool_bout
        row.slot_elim_bout = fmt.slot_elim_bout
        row.pause_between_pools = fmt.pause_between_pools
        row.slot_team_match = fmt.slot_team_match if team else None
        row.points_pool = fmt.points_pool
        row.points_elim = None if team else fmt.points_elim
        row.points_final = None if team else fmt.points_final
        row.points_team_bout = fmt.points_team_bout if team else None
        row.points_team_final = fmt.points_team_final if team else None
        row.takes_pools_from = fmt.takes_pools_from
        session.add(row)
    session.flush()


def team_total(points_per_bout: int, team_min: int | None) -> int:
    """A team match's total: points per bout times k² bouts, k the minimum
    team size (owner decision 2026-11-17)."""
    k = team_min or 3
    return points_per_bout * k * k


# ------------------------------------------------------------ officials


def read_officials(session: Session, tid: int, persons: Mapping[str, str]) -> list[OfficialOut]:
    """`persons` maps a roster key to the person's name. A link that resolves
    reads the person's current name; a lost one keeps the stored name."""
    officials = session.scalars(
        select(FloorOfficial)
        .where(FloorOfficial.tournament_id == tid)
        .order_by(FloorOfficial.ordinal)
    ).all()
    days = dict(
        session.execute(select(FloorDay.id, FloorDay.date).where(FloorDay.tournament_id == tid))
        .tuples()
        .all()
    )
    ids = [o.id for o in officials]
    available: dict[int, list[date]] = {}
    for official_id, day_id in session.execute(
        select(FloorOfficialDay.official_id, FloorOfficialDay.day_id).where(
            FloorOfficialDay.official_id.in_(ids)
        )
    ).tuples():
        available.setdefault(official_id, []).append(days[day_id])
    serves = _serves_of(session, FloorOfficialDiscipline, ids)
    out: list[OfficialOut] = []
    for o in officials:
        linked = persons.get(o.person_key) if o.person_key is not None else None
        out.append(
            OfficialOut(
                id=o.id,
                name=linked if linked is not None else o.name,
                person_key=o.person_key,
                main=o.main,
                serves=serves.get(o.id, []),
                days=sorted(available.get(o.id, [])),
                link_lost=o.person_key is not None and linked is None,
            )
        )
    return out


def save_officials(
    session: Session,
    tournament: Tournament,
    officials: Sequence[OfficialIn],
    persons: Mapping[str, str],
) -> None:
    """Replace the officials, in the order given. A link may only be made to a
    person on the roster, and names the official by that person's name; one
    already stored is kept even once its person has left, and stated as lost
    rather than dropped."""
    known_days = _day_ids(session, tournament)
    stored: dict[int, FloorOfficial] = _owned(session, FloorOfficial, tournament.id)
    disciplines = {d.id for d in tournament.disciplines}
    errors: list[dict] = []
    names: list[str] = []
    for i, official in enumerate(officials):
        previous = stored.get(official.id) if official.id is not None else None
        if official.id is not None and previous is None:
            errors.append({"field": f"{i}.id", "code": "not_found"})
        key = official.person_key
        kept_link = previous is not None and previous.person_key == key
        if key is not None and key not in persons and not kept_link:
            errors.append({"field": f"{i}.person_key", "code": "unknown_person"})
        name = persons.get(key, "") if key is not None else ""
        if not name and key is not None and previous is not None and kept_link:
            name = previous.name
        name = name or official.name
        if not name:
            errors.append({"field": f"{i}.name", "code": "required"})
        names.append(name)
        errors += _serves_errors(f"{i}.serves", official.serves, disciplines)
        errors += _unknown_days(f"{i}.days", official.days, known_days)
    if errors:
        raise FieldValidationError(errors)

    kept = {o.id for o in officials if o.id is not None}
    gone = [oid for oid in stored if oid not in kept]
    if gone:
        # a removed official's places become unfilled, to be run again
        session.execute(
            update(FloorAssignment)
            .where(FloorAssignment.official_id.in_(gone))
            .values(official_id=None, pinned=False)
        )
        session.execute(delete(FloorOfficialDay).where(FloorOfficialDay.official_id.in_(gone)))
        session.execute(
            delete(FloorOfficialDiscipline).where(FloorOfficialDiscipline.official_id.in_(gone))
        )
        session.execute(delete(FloorOfficial).where(FloorOfficial.id.in_(gone)))
    for ordinal, (official, name) in enumerate(zip(officials, names, strict=True), start=1):
        row = (
            stored[official.id]
            if official.id is not None
            else FloorOfficial(tournament_id=tournament.id)
        )
        row.name = name
        row.person_key = official.person_key
        row.main = official.main
        row.ordinal = ordinal
        session.add(row)
        session.flush()
        session.execute(delete(FloorOfficialDay).where(FloorOfficialDay.official_id == row.id))
        session.execute(
            delete(FloorOfficialDiscipline).where(FloorOfficialDiscipline.official_id == row.id)
        )
        for when in set(official.days):
            session.add(FloorOfficialDay(official_id=row.id, day_id=known_days[when]))
        for served in official.serves:
            session.add(
                FloorOfficialDiscipline(
                    official_id=row.id, discipline_id=served.discipline_id, reserve=served.reserve
                )
            )
    session.flush()


# ------------------------------------------------------------ parameters and preferences


def _known(model: type[ParamsIO] | type[PreferencesIO], stored: Mapping[str, object]) -> dict:
    return {k: v for k, v in stored.items() if k in model.model_fields}


def read_params(session: Session, tid: int) -> ParamsIO:
    """The stored document over the defaults. A key the code no longer knows
    is ignored on read; a save refuses one."""
    return ParamsIO.model_validate(_known(ParamsIO, _settings(session, tid).params or {}))


def read_preferences(session: Session, tid: int) -> PreferencesIO:
    return PreferencesIO.model_validate(_known(PreferencesIO, _settings(session, tid).params or {}))


def _merge(session: Session, tid: int, values: dict[str, object]) -> None:
    """Each section writes its own keys only (design rework-floor-setup D7)."""
    row = _settings(session, tid)
    row.params = {**(row.params or {}), **values}
    session.add(row)
    session.flush()


def save_params(session: Session, tid: int, params: ParamsIO) -> None:
    _merge(session, tid, params.model_dump())


def save_preferences(session: Session, tid: int, preferences: PreferencesIO) -> None:
    _merge(session, tid, preferences.model_dump())


# ------------------------------------------------------------ the effective view


@dataclass(frozen=True)
class ServedBy:
    """Who serves a discipline: owner ids, regular and reserve."""

    regular: frozenset[int] = frozenset()
    reserve: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Effective:
    """Setup as the floor reads it, with what scope hides left out."""

    scope: ScopeIO
    days: tuple[FloorDay, ...]
    # discipline id → day id
    day_of: Mapping[int, int]
    formats: Mapping[int, FloorFormat]
    # piste id → (regular disciplines, reserve disciplines); only pistes that
    # serve something
    pistes: tuple[tuple[FloorPiste, frozenset[int], frozenset[int]], ...] = ()
    # official id → (row, regular disciplines, reserve disciplines, day ids)
    officials: tuple[tuple[FloorOfficial, frozenset[int], frozenset[int], frozenset[int]], ...] = (
        field(default_factory=tuple)
    )


def _split(serves: Sequence[ServesIO]) -> tuple[frozenset[int], frozenset[int]]:
    return (
        frozenset(s.discipline_id for s in serves if not s.reserve),
        frozenset(s.discipline_id for s in serves if s.reserve),
    )


def effective(session: Session, tournament: Tournament) -> Effective:
    tid = tournament.id
    scope = read_scope(session, tid)
    days = tuple(_stored_days(session, tid))
    formats = {
        row.discipline_id: row
        for row in session.scalars(select(FloorFormat).where(FloorFormat.tournament_id == tid))
    }
    if not scope.plan_schedule:
        return Effective(scope=scope, days=(), day_of={}, formats=formats)
    day_of = discipline_days(session, tournament)
    piste_rows = list(
        session.scalars(
            select(FloorPiste).where(FloorPiste.tournament_id == tid).order_by(FloorPiste.ordinal)
        )
    )
    piste_serves = _serves_of(session, FloorPisteDiscipline, [p.id for p in piste_rows])
    pistes = []
    for piste in piste_rows:
        regular, reserve = _split(piste_serves.get(piste.id, []))
        if regular or reserve:
            pistes.append((piste, regular, reserve))
    officials = []
    if scope.plan_officials:
        rows = list(
            session.scalars(
                select(FloorOfficial)
                .where(FloorOfficial.tournament_id == tid)
                .order_by(FloorOfficial.ordinal)
            )
        )
        serves = _serves_of(session, FloorOfficialDiscipline, [o.id for o in rows])
        days_of: dict[int, set[int]] = {}
        for official_id, day_id in session.execute(
            select(FloorOfficialDay.official_id, FloorOfficialDay.day_id).where(
                FloorOfficialDay.official_id.in_([o.id for o in rows])
            )
        ).tuples():
            days_of.setdefault(official_id, set()).add(day_id)
        every_day = frozenset(day.id for day in days)
        for row in rows:
            regular, reserve = _split(serves.get(row.id, []))
            available = frozenset(days_of.get(row.id, set())) if scope.multi_day else every_day
            officials.append((row, regular, reserve, available))
    return Effective(
        scope=scope,
        days=days,
        day_of=day_of,
        formats=formats,
        pistes=tuple(pistes),
        officials=tuple(officials),
    )


# ------------------------------------------------------------ waiting


def setup_missing(session: Session, tournament: Tournament) -> list[str]:
    """What floor Setup names incomplete (spec floor-console, A badge means
    something here is waiting for you), by what scope shows: each discipline
    without a format or with a broken take-over; with the schedule, no day
    stated, a dayless discipline and a discipline no piste serves as
    regular."""
    missing: list[str] = []
    seen = effective(session, tournament)
    if seen.scope.plan_schedule:
        if not seen.days:
            missing.append("days")
        served = {d for _, regular, _ in seen.pistes for d in regular}
        for discipline in tournament.disciplines:
            if seen.days and discipline.id not in seen.day_of:
                missing.append(f"day:{discipline.id}")
            if discipline.id not in served:
                missing.append(f"piste:{discipline.id}")
    for fmt in read_formats(session, tournament):
        missing += [f"{what}:{fmt.discipline_id}" for what in fmt.missing]
    return missing
