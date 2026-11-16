"""Floor Setup: days, pistes, formats, officials and parameters (spec
floor-setup; design add-floor-console D3).

Each section is read with its defaults and saved whole, after every field of
it is checked: a save is refused with field-level errors, never partially
stored. Disciplines and persons come from the roster port, so nothing here
reads an office table.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.errors import FieldValidationError
from app.floor.models import (
    FloorDay,
    FloorFormat,
    FloorOfficial,
    FloorOfficialDay,
    FloorPiste,
    FloorPisteDay,
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
    Staffing,
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


# ------------------------------------------------------------ days


def _stored_days(session: Session, tid: int) -> list[FloorDay]:
    return list(
        session.scalars(
            select(FloorDay).where(FloorDay.tournament_id == tid).order_by(FloorDay.date)
        )
    )


def _default_day(tournament: Tournament) -> DayIO:
    return DayIO(date=tournament.date, start=DEFAULT_START, end=DEFAULT_END, breaks=[])


def read_days(session: Session, tournament: Tournament) -> DaysOut:
    stored = _stored_days(session, tournament.id)
    if not stored:
        return DaysOut(stored=False, days=[_default_day(tournament)])
    return DaysOut(
        stored=True,
        days=[
            DayIO(
                date=day.date,
                start=_clock(day.start),
                end=_clock(day.end),
                breaks=[BreakIO(start=a, end=b) for a, b in day.breaks],
            )
            for day in stored
        ],
    )


def _day_errors(days: Sequence[DayIO]) -> list[dict]:
    errors: list[dict] = []
    seen: set[date] = set()
    for i, day in enumerate(days):
        if day.date in seen:
            errors.append({"field": f"{i}.date", "code": "duplicate"})
        seen.add(day.date)
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


def save_days(session: Session, tournament: Tournament, days: Sequence[DayIO]) -> None:
    """Replace the days. A day kept by its date keeps its id, so the pistes and
    officials available on it stay so; a day dropped takes their availability
    on it along."""
    errors = _day_errors(days)
    if errors:
        raise FieldValidationError(errors)
    stored = {day.date: day for day in _stored_days(session, tournament.id)}
    wanted = {day.date: day for day in days}
    for gone in stored.keys() - wanted.keys():
        row = stored[gone]
        session.execute(delete(FloorPisteDay).where(FloorPisteDay.day_id == row.id))
        session.execute(delete(FloorOfficialDay).where(FloorOfficialDay.day_id == row.id))
        session.delete(row)
    for when, day in wanted.items():
        row = stored.get(when) or FloorDay(tournament_id=tournament.id, date=when)
        row.start = _time(day.start)
        row.end = _time(day.end)
        row.breaks = [[b.start, b.end] for b in sorted(day.breaks, key=lambda b: b.start)]
        session.add(row)
    session.flush()


def _day_ids(session: Session, tournament: Tournament) -> dict[date, int]:
    """The stored days by date. A section naming days before any day was saved
    names the offered default, so it is stored first."""
    stored = _stored_days(session, tournament.id)
    if not stored:
        save_days(session, tournament, [_default_day(tournament)])
        stored = _stored_days(session, tournament.id)
    return {day.date: day.id for day in stored}


def _unknown_days(field: str, wanted: Sequence[date], known: dict[date, int]) -> list[dict]:
    return [
        {"field": f"{field}.{j}", "code": "unknown_day"}
        for j, when in enumerate(wanted)
        if when not in known
    ]


# ------------------------------------------------------------ pistes


def read_pistes(session: Session, tid: int) -> list[PisteOut]:
    pistes = session.scalars(
        select(FloorPiste).where(FloorPiste.tournament_id == tid).order_by(FloorPiste.ordinal)
    ).all()
    days = dict(
        session.execute(select(FloorDay.id, FloorDay.date).where(FloorDay.tournament_id == tid))
        .tuples()
        .all()
    )
    available: dict[int, list[date]] = {}
    for piste_id, day_id in session.execute(
        select(FloorPisteDay.piste_id, FloorPisteDay.day_id).where(
            FloorPisteDay.piste_id.in_([p.id for p in pistes])
        )
    ).tuples():
        available.setdefault(piste_id, []).append(days[day_id])
    return [
        PisteOut(
            id=p.id,
            name=p.name,
            reserve=p.reserve,
            tag=p.tag,
            days=sorted(available.get(p.id, [])),
        )
        for p in pistes
    ]


def _owned(session: Session, model: type[FloorPiste] | type[FloorOfficial], tid: int) -> dict:
    return {row.id: row for row in session.scalars(select(model).where(model.tournament_id == tid))}


def save_pistes(session: Session, tournament: Tournament, pistes: Sequence[PisteIn]) -> None:
    """Replace the pistes, in the order given."""
    known_days = _day_ids(session, tournament)
    stored: dict[int, FloorPiste] = _owned(session, FloorPiste, tournament.id)
    errors: list[dict] = []
    names: set[str] = set()
    for i, piste in enumerate(pistes):
        folded = piste.name.casefold()
        if folded in names:
            errors.append({"field": f"{i}.name", "code": "duplicate"})
        names.add(folded)
        if piste.id is not None and piste.id not in stored:
            errors.append({"field": f"{i}.id", "code": "not_found"})
        errors += _unknown_days(f"{i}.days", piste.days, known_days)
    if errors:
        raise FieldValidationError(errors)

    kept = {p.id for p in pistes if p.id is not None}
    gone = [row.id for pid, row in stored.items() if pid not in kept]
    if gone:
        session.execute(delete(FloorPisteDay).where(FloorPisteDay.piste_id.in_(gone)))
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
        row.reserve = piste.reserve
        row.tag = piste.tag or None
        session.add(row)
        session.flush()
        session.execute(delete(FloorPisteDay).where(FloorPisteDay.piste_id == row.id))
        for when in set(piste.days):
            session.add(FloorPisteDay(piste_id=row.id, day_id=known_days[when]))
    session.flush()


# ------------------------------------------------------------ formats


def _default_format(discipline: FloorDiscipline) -> FormatIn:
    return FormatIn(
        discipline_id=discipline.id,
        pool_min=5,
        pool_max=7,
        advance=None,
        third_place=False,
        staffing=None,
        slot_pool_bout=4,
        slot_elim_bout=6,
        slot_pool_overhead=5,
        slot_team_match=25 if discipline.kind == "team" else None,
    )


def _missing(stored: bool, staffing: Staffing | None) -> list[str]:
    if not stored:
        return ["format"]
    return [] if staffing is not None else ["staffing"]


def read_formats(session: Session, tournament: Tournament) -> list[FormatOut]:
    stored = {
        row.discipline_id: row
        for row in session.scalars(
            select(FloorFormat).where(FloorFormat.tournament_id == tournament.id)
        )
    }
    out: list[FormatOut] = []
    for discipline in tournament.disciplines:
        row = stored.get(discipline.id)
        if row is None:
            fmt = _default_format(discipline)
            out.append(FormatOut(**fmt.model_dump(), stored=False, missing=_missing(False, None)))
            continue
        staffing = Staffing(**row.staffing) if row.staffing is not None else None
        out.append(
            FormatOut(
                discipline_id=discipline.id,
                pool_min=row.pool_min,
                pool_max=row.pool_max,
                advance=row.advance,
                third_place=row.third_place,
                staffing=staffing,
                slot_pool_bout=row.slot_pool_bout,
                slot_elim_bout=row.slot_elim_bout,
                slot_pool_overhead=row.slot_pool_overhead,
                slot_team_match=row.slot_team_match,
                stored=True,
                missing=_missing(True, staffing),
            )
        )
    return out


def save_formats(session: Session, tournament: Tournament, formats: Sequence[FormatIn]) -> None:
    """Store the formats given; disciplines not named keep theirs."""
    by_id = {d.id: d for d in tournament.disciplines}
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
        if fmt.staffing is not None and fmt.staffing.referee < 1:
            errors.append({"field": f"{i}.staffing.referee", "code": "referee_required"})
        if discipline.kind == "team" and fmt.slot_team_match is None:
            errors.append({"field": f"{i}.slot_team_match", "code": "required"})
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
        row.pool_min = fmt.pool_min
        row.pool_max = fmt.pool_max
        row.advance = fmt.advance
        row.third_place = fmt.third_place
        row.staffing = fmt.staffing.model_dump() if fmt.staffing is not None else None
        row.slot_pool_bout = fmt.slot_pool_bout
        row.slot_elim_bout = fmt.slot_elim_bout
        row.slot_pool_overhead = fmt.slot_pool_overhead
        team = by_id[fmt.discipline_id].kind == "team"
        row.slot_team_match = fmt.slot_team_match if team else None
        session.add(row)
    session.flush()


# ------------------------------------------------------------ officials


def read_officials(session: Session, tid: int, person_keys: set[str]) -> list[OfficialOut]:
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
    available: dict[int, list[date]] = {}
    for official_id, day_id in session.execute(
        select(FloorOfficialDay.official_id, FloorOfficialDay.day_id).where(
            FloorOfficialDay.official_id.in_([o.id for o in officials])
        )
    ).tuples():
        available.setdefault(official_id, []).append(days[day_id])
    return [
        OfficialOut.model_validate(
            {
                "id": o.id,
                "name": o.name,
                "person_key": o.person_key,
                # the stored list was validated on save; this reads it back typed
                "roles": o.roles,
                "discipline_ids": o.discipline_ids,
                "days": sorted(available.get(o.id, [])),
                "link_lost": o.person_key is not None and o.person_key not in person_keys,
            }
        )
        for o in officials
    ]


def save_officials(
    session: Session,
    tournament: Tournament,
    officials: Sequence[OfficialIn],
    person_keys: set[str],
) -> None:
    """Replace the officials, in the order given. A link may only be made to a
    person on the roster; one already stored is kept even once its person has
    left, and stated as lost rather than dropped."""
    known_days = _day_ids(session, tournament)
    stored: dict[int, FloorOfficial] = _owned(session, FloorOfficial, tournament.id)
    disciplines = {d.id for d in tournament.disciplines}
    errors: list[dict] = []
    for i, official in enumerate(officials):
        previous = stored.get(official.id) if official.id is not None else None
        if official.id is not None and previous is None:
            errors.append({"field": f"{i}.id", "code": "not_found"})
        if not official.roles:
            errors.append({"field": f"{i}.roles", "code": "required"})
        key = official.person_key
        if (
            key is not None
            and key not in person_keys
            and (previous is None or previous.person_key != key)
        ):
            errors.append({"field": f"{i}.person_key", "code": "unknown_person"})
        errors += [
            {"field": f"{i}.discipline_ids.{j}", "code": "unknown_discipline"}
            for j, discipline_id in enumerate(official.discipline_ids)
            if discipline_id not in disciplines
        ]
        errors += _unknown_days(f"{i}.days", official.days, known_days)
    if errors:
        raise FieldValidationError(errors)

    kept = {o.id for o in officials if o.id is not None}
    gone = [oid for oid in stored if oid not in kept]
    if gone:
        session.execute(delete(FloorOfficialDay).where(FloorOfficialDay.official_id.in_(gone)))
        session.execute(delete(FloorOfficial).where(FloorOfficial.id.in_(gone)))
    for ordinal, official in enumerate(officials, start=1):
        row = (
            stored[official.id]
            if official.id is not None
            else FloorOfficial(tournament_id=tournament.id)
        )
        row.name = official.name
        row.person_key = official.person_key
        row.roles = sorted(set(official.roles))
        row.discipline_ids = sorted(set(official.discipline_ids))
        row.ordinal = ordinal
        session.add(row)
        session.flush()
        session.execute(delete(FloorOfficialDay).where(FloorOfficialDay.official_id == row.id))
        for when in set(official.days):
            session.add(FloorOfficialDay(official_id=row.id, day_id=known_days[when]))
    session.flush()


# ------------------------------------------------------------ parameters


def read_params(session: Session, tid: int) -> ParamsIO:
    """The stored document over the defaults. A key the code no longer knows
    is ignored on read; a save refuses one."""
    row = session.get(FloorSettings, tid)
    stored = row.params if row is not None else {}
    known = {k: v for k, v in stored.items() if k in ParamsIO.model_fields}
    return ParamsIO.model_validate(known)


def save_params(session: Session, tid: int, params: ParamsIO) -> None:
    row = session.get(FloorSettings, tid) or FloorSettings(tournament_id=tid)
    row.params = params.model_dump()
    session.add(row)
    session.flush()


# ------------------------------------------------------------ waiting


def setup_missing(session: Session, tournament: Tournament) -> list[str]:
    """What floor Setup names incomplete (spec floor-console, A badge means
    something here is waiting for you): no day stated, no piste, and each
    discipline without a format or without its staffing."""
    missing: list[str] = []
    if not _stored_days(session, tournament.id):
        missing.append("days")
    if not session.scalar(select(FloorPiste.id).where(FloorPiste.tournament_id == tournament.id)):
        missing.append("pistes")
    for fmt in read_formats(session, tournament):
        missing += [f"{what}:{fmt.discipline_id}" for what in fmt.missing]
    return missing
