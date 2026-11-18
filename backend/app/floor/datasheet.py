"""The Data sheet: the floor's own corrections laid over the floor roster
(spec floor-data; design floor-data-sheet D1–D4).

`apply` is pure: the office's roster and the floor's stored edits in, a
`Roster` of the same shape out. `roster` and `roster_of` are what every floor
reader calls, so a correction made on Data is what the desk, the snapshot,
the draw and the public pages read. Nothing here writes to the office.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.floor import checkin, people
from app.floor.adapters import office
from app.floor.adapters.office import HRFetcher, Tournament
from app.floor.models import (
    FloorLineup,
    FloorLocalPerson,
    FloorSheetEdit,
    FloorSheetEntry,
    FloorSheetFetch,
    FloorSheetRating,
    FloorSheetTeam,
    FloorWithdrawal,
)
from app.floor.roster import FloorDiscipline, IndividualEntry, Person, Roster, TeamEntry

TEAM = "floorteam:"
PERSON_FIELDS = ("name", "club", "nationality", "hr_id")
ENTRY_FIELDS = ("rating", "rank")
# the stored lengths of the person cells (models.FloorLocalPerson)
_LENGTHS = {"name": 200, "club": 200, "nationality": 80}

Figure = tuple[float | None, int | None]


@dataclass(frozen=True)
class AddedTeam:
    key: str
    discipline_id: int
    name: str
    # its lineup, person keys in order
    members: tuple[str, ...]


@dataclass(frozen=True)
class Edits:
    """Everything the floor stored over the roster for one tournament."""

    # (subject, field) -> value; a subject is a person key or an entry key
    cells: Mapping[tuple[str, str], object] = field(default_factory=dict)
    # (person key, discipline id) of individual entries added on the floor
    added: tuple[tuple[str, int], ...] = ()
    teams: tuple[AddedTeam, ...] = ()
    # every floor-only person, as stored
    locals: tuple[Person, ...] = ()
    # (discipline id, hr id) -> the floor's fetched figure
    fetched: Mapping[tuple[int, int], Figure] = field(default_factory=dict)


class Refused(Exception):
    def __init__(self, code: str, detail: object = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(code)


# ------------------------------------------------------------ the overlay


def _person(person: Person, cells: Mapping[tuple[str, str], object]) -> Person:
    def text(name: str, base: str | None) -> str | None:
        value = cells.get((person.key, name), base)
        return value if isinstance(value, str) else base

    name = text("name", person.name)
    return replace(
        person,
        name=name if name is not None else person.name,
        club=text("club", person.club),
        nationality=text("nationality", person.nationality),
        hr_id=_int(cells[(person.key, "hr_id")])
        if (person.key, "hr_id") in cells
        else person.hr_id,
    )


def figure(edits: Edits, entry: str, discipline: int, hr_id: int | None, base: Figure) -> Figure:
    """A cell resolves hand edit > floor fetch > roster (design D2)."""
    fetched = edits.fetched.get((discipline, hr_id)) if hr_id is not None else None
    rating, rank = fetched if fetched is not None else base
    if (entry, "rating") in edits.cells:
        rating = _float(edits.cells[(entry, "rating")])
    if (entry, "rank") in edits.cells:
        rank = _int(edits.cells[(entry, "rank")])
    return rating, rank


def _float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def apply(base: Roster, edits: Edits) -> Roster:
    """The roster as the Data sheet states it. An empty `Edits` returns an
    equal roster."""
    persons = {p.key: _person(p, edits.cells) for p in base.persons}
    for local in edits.locals:
        persons.setdefault(local.key, local)
    by_id = {d.id: d for d in base.disciplines}
    by_slug = {d.slug: d for d in base.disciplines}

    def hr_of(key: str) -> int | None:
        found = persons.get(key)
        return found.hr_id if found is not None else None

    individuals: list[IndividualEntry] = []
    entered: set[tuple[str, int]] = set()
    for entry in base.individuals:
        discipline = by_slug[entry.discipline]
        key = people.entry_key(entry.person, discipline.id)
        rating, rank = figure(
            edits, key, discipline.id, hr_of(entry.person), (entry.rating, entry.rank)
        )
        individuals.append(replace(entry, rating=rating, rank=rank))
        entered.add((entry.person, discipline.id))
    for person, discipline_id in edits.added:
        discipline = by_id.get(discipline_id)
        if (
            discipline is None
            or discipline.kind != "individual"
            or person not in persons
            or (person, discipline_id) in entered
        ):
            continue
        key = people.entry_key(person, discipline_id)
        rating, rank = figure(edits, key, discipline_id, hr_of(person), (None, None))
        individuals.append(
            IndividualEntry(
                person=person, discipline=discipline.slug, rating=rating, rank=rank, paid=False
            )
        )
        entered.add((person, discipline_id))

    def figures(team: TeamEntry, discipline: FloorDiscipline) -> tuple[Figure, ...]:
        return tuple(
            figure(
                edits,
                people.entry_key(member, discipline.id),
                discipline.id,
                hr_of(member),
                team.ratings[index] if index < len(team.ratings) else (None, None),
            )
            for index, member in enumerate(team.members)
        )

    teams = [replace(t, ratings=figures(t, by_slug[t.discipline])) for t in base.teams]
    for added in edits.teams:
        discipline = by_id.get(added.discipline_id)
        if discipline is None or discipline.kind != "team":
            continue
        members = tuple(m for m in added.members if m in persons)
        team = TeamEntry(
            key=added.key, discipline=discipline.slug, name=added.name, members=members, paid=False
        )
        teams.append(replace(team, ratings=figures(team, discipline)))

    return replace(
        base,
        persons=tuple(persons.values()),
        individuals=tuple(individuals),
        teams=tuple(teams),
    )


# ------------------------------------------------------------ reading


def load(session: Session, tid: int) -> Edits:
    cells = {
        (row.subject, row.field): row.value
        for row in session.scalars(
            select(FloorSheetEdit).where(FloorSheetEdit.tournament_id == tid)
        )
    }
    added = tuple(
        (row.person_key, row.discipline_id)
        for row in session.scalars(
            select(FloorSheetEntry)
            .where(FloorSheetEntry.tournament_id == tid)
            .order_by(FloorSheetEntry.id)
        )
    )
    stated = people.lineups(session, tid)
    teams = tuple(
        AddedTeam(
            key=f"{TEAM}{row.id}",
            discipline_id=row.discipline_id,
            name=row.name,
            members=stated.get(f"{TEAM}{row.id}", ()),
        )
        for row in session.scalars(
            select(FloorSheetTeam)
            .where(FloorSheetTeam.tournament_id == tid)
            .order_by(FloorSheetTeam.id)
        )
    )
    locals_ = tuple(
        people.local_person(row)
        for row in session.scalars(
            select(FloorLocalPerson)
            .where(FloorLocalPerson.tournament_id == tid)
            .order_by(FloorLocalPerson.id)
        )
    )
    fetched: dict[tuple[int, int], Figure] = {}
    for fetch, rating in session.execute(
        select(FloorSheetFetch, FloorSheetRating)
        .join(FloorSheetRating, FloorSheetRating.fetch_id == FloorSheetFetch.id)
        .where(FloorSheetFetch.tournament_id == tid)
    ).tuples():
        fetched[(fetch.discipline_id, rating.hr_id)] = (rating.rating, rating.rank)
    return Edits(cells=cells, added=added, teams=teams, locals=locals_, fetched=fetched)


def roster(session: Session, tournament: Tournament) -> Roster:
    """The tournament's entrants as the Data sheet states them: what every
    floor reader reads."""
    return apply(office.roster(session, tournament), load(session, tournament.id))


def roster_of(session: Session, tournament_id: int) -> Roster | None:
    base = office.roster_of(session, tournament_id)
    return apply(base, load(session, tournament_id)) if base is not None else None


# ------------------------------------------------------------ writing


def _discipline(sheet: Roster, discipline_id: int) -> FloorDiscipline:
    found = next((d for d in sheet.disciplines if d.id == discipline_id), None)
    if found is None:
        raise Refused("discipline_not_found")
    return found


def _open(session: Session, tid: int, discipline_id: int) -> None:
    if checkin.closed(session, tid, discipline_id):
        raise Refused("checkin_closed")


def entered_disciplines(session: Session, tid: int, sheet: Roster, person: str) -> set[int]:
    """The disciplines a person stands in on the sheet: their own entries, and
    the teams whose lineup holds them."""
    by_slug = {d.slug: d.id for d in sheet.disciplines}
    found = {by_slug[e.discipline] for e in sheet.individuals if e.person == person}
    stated = people.lineups(session, tid)
    for team in sheet.teams:
        if person in team.members or person in people.lineup_of(team, stated):
            found.add(by_slug[team.discipline])
    return found


def _clean(field_name: str, value: object) -> object:
    """The stored value of a cell, or None to return it to what lies beneath.
    Refuses what the cell cannot hold."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if field_name == "name":
            raise Refused("required")
        return None
    if field_name in _LENGTHS:
        if not isinstance(value, str) or len(value.strip()) > _LENGTHS[field_name]:
            raise Refused("invalid")
        if field_name == "nationality":
            return office.nationality_code(value.strip())
        return value.strip()
    if field_name in ("hr_id", "rank"):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value < 2**31:
            raise Refused("invalid")
        return value
    # rating
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value < 10**6:
        raise Refused("invalid")
    return float(value)


def set_cell(
    session: Session,
    tid: int,
    sheet: Roster,
    subject: str,
    field_name: str,
    value: object,
    by: int | None,
    now: datetime,
) -> None:
    """A hand correction, or with an empty value its removal (spec floor-data,
    The sheet is the floor's to correct)."""
    persons = {p.key for p in sheet.persons}
    if field_name in PERSON_FIELDS:
        if subject not in persons:
            raise Refused("subject_not_found")
        standing = entered_disciplines(session, tid, sheet, subject)
        # a person's cell holds across disciplines: refused only where every
        # one of them is frozen (design D6)
        if standing and all(checkin.closed(session, tid, d) for d in standing):
            raise Refused("checkin_closed")
    elif field_name in ENTRY_FIELDS:
        person, _, discipline = subject.rpartition("@")
        if not discipline.isdigit() or person not in persons:
            raise Refused("subject_not_found")
        if int(discipline) not in entered_disciplines(session, tid, sheet, person):
            raise Refused("subject_not_found")
        _open(session, tid, int(discipline))
    else:
        raise Refused("unknown_field")
    cleaned = _clean(field_name, value)

    if subject.startswith(people.LOCAL) and field_name in PERSON_FIELDS:
        # a floor-only person has nothing beneath: the row itself changes
        local = session.get(FloorLocalPerson, int(subject.removeprefix(people.LOCAL)))
        if local is None or local.tournament_id != tid:
            raise Refused("subject_not_found")
        setattr(local, field_name, cleaned)
        session.flush()
        return

    session.execute(
        delete(FloorSheetEdit).where(
            FloorSheetEdit.tournament_id == tid,
            FloorSheetEdit.subject == subject,
            FloorSheetEdit.field == field_name,
        )
    )
    if cleaned is not None:
        session.add(
            FloorSheetEdit(
                tournament_id=tid,
                subject=subject,
                field=field_name,
                value=cleaned,
                at=now,
                by=by,
            )
        )
    session.flush()


@dataclass(frozen=True)
class NewPerson:
    name: str
    club: str | None = None
    nationality: str | None = None
    hr_id: int | None = None


def _local(session: Session, tid: int, new: NewPerson) -> str:
    name = _clean("name", new.name)
    row = FloorLocalPerson(
        tournament_id=tid,
        name=str(name),
        club=_text(_clean("club", new.club)),
        nationality=_text(_clean("nationality", new.nationality)),
        hr_id=_int(_clean("hr_id", new.hr_id)),
    )
    session.add(row)
    session.flush()
    return f"{people.LOCAL}{row.id}"


def _bound(sheet: Roster, member: str | NewPerson) -> str | NewPerson:
    """A newcomer whose HEMA Ratings id someone on the floor already holds is
    that person, not a second one (the boundary's identity by hr_id); anyone
    else stays as named."""
    if isinstance(member, str) or member.hr_id is None:
        return member
    holder = next((p.key for p in sheet.persons if p.hr_id == member.hr_id), None)
    return holder if holder is not None else member


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def add_entry(
    session: Session,
    tid: int,
    sheet: Roster,
    discipline_id: int,
    person: str | NewPerson,
    by: int | None,
    now: datetime,
) -> str:
    """An individual entrant added on the floor; the person's key."""
    discipline = _discipline(sheet, discipline_id)
    if discipline.kind != "individual":
        raise Refused("team_discipline")
    _open(session, tid, discipline_id)
    person = _bound(sheet, person)
    if isinstance(person, str):
        if person not in {p.key for p in sheet.persons}:
            raise Refused("person_not_found")
        if any(e.person == person and e.discipline == discipline.slug for e in sheet.individuals):
            raise Refused("already_entered")
        key = person
    else:
        key = _local(session, tid, person)
    session.add(
        FloorSheetEntry(
            tournament_id=tid, person_key=key, discipline_id=discipline_id, at=now, by=by
        )
    )
    session.flush()
    return key


def remove_entry(session: Session, tid: int, discipline_id: int, person: str) -> None:
    """Deletes an entry added on the floor. An office entry is withdrawn."""
    _open(session, tid, discipline_id)
    row = session.scalar(
        select(FloorSheetEntry).where(
            FloorSheetEntry.tournament_id == tid,
            FloorSheetEntry.person_key == person,
            FloorSheetEntry.discipline_id == discipline_id,
        )
    )
    if row is None:
        raise Refused("not_added")
    session.delete(row)
    key = people.entry_key(person, discipline_id)
    _forget(session, tid, key)


def _forget(session: Session, tid: int, key: str) -> None:
    session.execute(
        delete(FloorWithdrawal).where(
            FloorWithdrawal.tournament_id == tid, FloorWithdrawal.entry_key == key
        )
    )
    session.execute(
        delete(FloorSheetEdit).where(
            FloorSheetEdit.tournament_id == tid, FloorSheetEdit.subject == key
        )
    )
    session.flush()


def add_team(
    session: Session,
    tid: int,
    sheet: Roster,
    discipline_id: int,
    name: str,
    members: list[str | NewPerson],
    by: int | None,
    now: datetime,
) -> str:
    """A team formed on the floor, its members its lineup; the team's key."""
    discipline = _discipline(sheet, discipline_id)
    if discipline.kind != "team":
        raise Refused("individual_discipline")
    _open(session, tid, discipline_id)
    cleaned = _clean("name", name)
    members = [_bound(sheet, m) for m in members]
    errors: list[dict] = []
    lo, hi = discipline.team_min or 1, discipline.team_max or max(len(members), 1)
    if not lo <= len(members) <= hi:
        errors.append({"field": "members", "code": "lineup_size", "params": {"min": lo, "max": hi}})
    known = {p.key for p in sheet.persons}
    existing = [m for m in members if isinstance(m, str)]
    if len(set(existing)) != len(existing):
        errors.append({"field": "members", "code": "duplicate"})
    stated = people.lineups(session, tid)
    taken = {
        member
        for team in sheet.teams
        if team.discipline == discipline.slug
        for member in people.lineup_of(team, stated)
    }
    for index, member in enumerate(members):
        if not isinstance(member, str):
            continue
        if member not in known:
            errors.append({"field": f"members.{index}", "code": "unknown_person"})
        elif member in taken:
            errors.append({"field": f"members.{index}", "code": "in_another_lineup"})
    if errors:
        raise Refused("invalid_team", errors)
    keys = [m if isinstance(m, str) else _local(session, tid, m) for m in members]
    row = FloorSheetTeam(
        tournament_id=tid, discipline_id=discipline_id, name=str(cleaned), at=now, by=by
    )
    session.add(row)
    session.flush()
    key = f"{TEAM}{row.id}"
    checkin.set_lineup(session, tid, key, keys)
    return key


def remove_team(session: Session, tid: int, team_key: str) -> None:
    """Deletes a team formed on the floor with its lineup."""
    if not team_key.startswith(TEAM) or not team_key.removeprefix(TEAM).isdigit():
        raise Refused("not_added")
    row = session.get(FloorSheetTeam, int(team_key.removeprefix(TEAM)))
    if row is None or row.tournament_id != tid:
        raise Refused("not_added")
    _open(session, tid, row.discipline_id)
    session.execute(
        delete(FloorLineup).where(
            FloorLineup.tournament_id == tid, FloorLineup.team_key == team_key
        )
    )
    session.delete(row)
    _forget(session, tid, team_key)


def discipline_hr_ids(
    sheet: Roster,
    discipline: FloorDiscipline,
    lineups: Mapping[str, tuple[str, ...]] | None = None,
) -> set[int]:
    """The HR ids of a discipline's entrants on the sheet, a team's members
    and the day's lineup among them."""
    persons = {p.key: p for p in sheet.persons}
    stated = lineups or {}
    keys = [e.person for e in sheet.individuals if e.discipline == discipline.slug]
    for team in sheet.teams:
        if team.discipline == discipline.slug:
            keys += [*team.members, *stated.get(team.key, ())]
    return {hr for key in keys if (p := persons.get(key)) is not None and (hr := p.hr_id)}


def refresh(
    session: Session,
    tournament: Tournament,
    sheet: Roster,
    discipline_id: int,
    fetcher: HRFetcher,
    now: datetime,
) -> dict[str, int]:
    """Fetches the discipline's entrants' figures into the floor (spec
    floor-data, The ratings are refreshed for one discipline). The office's
    snapshot is not written."""
    discipline = _discipline(sheet, discipline_id)
    _open(session, tournament.id, discipline_id)
    hr_ids = sorted(discipline_hr_ids(sheet, discipline, people.lineups(session, tournament.id)))
    found = office.fetch_discipline_ratings(tournament, discipline_id, hr_ids, fetcher)
    if found is None:
        raise Refused("fetch_failed")
    old = session.scalar(
        select(FloorSheetFetch).where(
            FloorSheetFetch.tournament_id == tournament.id,
            FloorSheetFetch.discipline_id == discipline_id,
        )
    )
    if old is not None:
        session.execute(delete(FloorSheetRating).where(FloorSheetRating.fetch_id == old.id))
        session.delete(old)
        session.flush()
    fetch = FloorSheetFetch(
        tournament_id=tournament.id, discipline_id=discipline_id, fetched_at=now, asked=hr_ids
    )
    session.add(fetch)
    session.flush()
    session.add_all(
        FloorSheetRating(fetch_id=fetch.id, hr_id=hr_id, rating=rating, rank=rank)
        for hr_id, (rating, rank) in found.items()
    )
    session.flush()
    return {"ratings": len(found), "fencers": len(hr_ids)}
