"""One discipline's Data sheet as the tab draws it (spec floor-data; design
floor-data-sheet D6, D8): rows in seeding order with what marks each cell,
live before check-in closes and the snapshot after."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.floor import datasheet, people
from app.floor.datasheet import ENTRY_FIELDS, PERSON_FIELDS, Edits
from app.floor.models import FloorSheetFetch, FloorSnapshotEntrant
from app.floor.roster import FloorDiscipline, Person, Roster

Row = dict[str, object]


def _edited(edits: Edits, person: str, entry: str) -> list[str]:
    return [f for f in PERSON_FIELDS if (person, f) in edits.cells] + [
        f for f in ENTRY_FIELDS if (entry, f) in edits.cells
    ]


def _person_row(
    person: Person | None,
    key: str,
    discipline: int,
    figure: tuple[float | None, int | None],
    edits: Edits,
) -> Row:
    entry = people.entry_key(key, discipline)
    return {
        "person": key,
        "entry_key": entry,
        "name": person.name if person is not None else key,
        "club": person.club if person is not None else None,
        "nationality": person.nationality if person is not None else None,
        "hr_id": person.hr_id if person is not None else None,
        "rating": figure[0],
        "rank": figure[1],
        "local": key.startswith(people.LOCAL),
        "edited": _edited(edits, key, entry),
    }


def _order(rows: list[Row]) -> list[Row]:
    """Rated by the draw's seeding key, then the unrated by name."""

    def rating(row: Row) -> float | None:
        value = row["rating"]
        return float(value) if isinstance(value, int | float) else None

    def rank(row: Row) -> int | None:
        value = row["rank"]
        return value if isinstance(value, int) else None

    rated = [r for r in rows if rating(r) is not None]
    unrated = [r for r in rows if rating(r) is None]
    rated.sort(key=lambda r: people.seeding_key(rating(r), rank(r), str(r["person"])))
    unrated.sort(key=lambda r: (str(r["name"]).casefold(), str(r["person"])))
    return rated + unrated


def view(session: Session, tid: int, sheet: Roster, discipline: FloorDiscipline) -> dict:
    edits = datasheet.load(session, tid)
    persons = people.persons(session, tid, sheet)
    gone = people.withdrawn(session, tid)
    added = set(edits.added)
    added_teams = {t.key for t in edits.teams}
    snap = people.snapshot(session, tid, discipline.id)
    individuals = [e for e in sheet.individuals if e.discipline == discipline.slug]
    teams = [t for t in sheet.teams if t.discipline == discipline.slug]
    paid_of = {e.person: e.paid for e in individuals} | {t.key: t.paid for t in teams}

    def member_rows(keys: tuple[str, ...], figures: dict[str, tuple[float | None, int | None]]):
        return [
            _person_row(persons.get(k), k, discipline.id, figures.get(k) or substitute(k), edits)
            for k in keys
        ]

    def substitute(key: str) -> tuple[float | None, int | None]:
        """A lineup member the team's roster does not list: the floor's own
        figures over nothing."""
        found = persons.get(key)
        hr_id = found.hr_id if found is not None else None
        return datasheet.figure(
            edits, people.entry_key(key, discipline.id), discipline.id, hr_id, (None, None)
        )

    def team_figures(key: str) -> dict[str, tuple[float | None, int | None]]:
        team = next((t for t in teams if t.key == key), None)
        if team is None:
            return {}
        return dict(zip(team.members, team.ratings, strict=False))

    rows: list[Row] = []
    team_rows: list[Row] = []
    if snap is not None:
        frozen = session.scalars(
            select(FloorSnapshotEntrant)
            .where(FloorSnapshotEntrant.snapshot_id == snap.id)
            .order_by(FloorSnapshotEntrant.id)
        )
        for row in frozen:
            if row.kind == "team":
                team_rows.append(
                    {
                        "key": row.entrant_key,
                        "name": row.name,
                        "paid": paid_of.get(row.entrant_key),
                        "withdrawn": False,
                        "added": row.entrant_key in added_teams,
                        "members": member_rows(tuple(row.members), team_figures(row.entrant_key)),
                    }
                )
                continue
            frozen_person = Person(
                key=row.entrant_key,
                name=row.name,
                club=row.club,
                nationality=row.nationality,
                hr_id=row.hr_id,
            )
            out = _person_row(
                frozen_person, row.entrant_key, discipline.id, (row.rating, row.rank), edits
            )
            out.update(
                paid=paid_of.get(row.entrant_key),
                withdrawn=False,
                added=(row.entrant_key, discipline.id) in added,
                # the snapshot is frozen: nothing on it is the sheet's to mark
                edited=[],
            )
            rows.append(out)
    else:
        for entry in individuals:
            out = _person_row(
                persons.get(entry.person),
                entry.person,
                discipline.id,
                (entry.rating, entry.rank),
                edits,
            )
            out.update(
                paid=entry.paid,
                withdrawn=str(out["entry_key"]) in gone,
                added=(entry.person, discipline.id) in added,
            )
            rows.append(out)
        stated = people.lineups(session, tid)
        for team in teams:
            figures = dict(zip(team.members, team.ratings, strict=False))
            team_rows.append(
                {
                    "key": team.key,
                    "name": team.name,
                    "paid": team.paid,
                    "withdrawn": team.key in gone,
                    "added": team.key in added_teams,
                    "members": member_rows(people.lineup_of(team, stated), figures),
                }
            )

    fetch = session.scalar(
        select(FloorSheetFetch).where(
            FloorSheetFetch.tournament_id == tid, FloorSheetFetch.discipline_id == discipline.id
        )
    )
    bound = datasheet.discipline_hr_ids(sheet, discipline, people.lineups(session, tid))
    missing = len(bound - set(fetch.asked)) if fetch is not None else len(bound)
    fetched_at: datetime | None = fetch.fetched_at if fetch is not None else None
    counted = team_rows if discipline.kind == "team" else rows
    return {
        "discipline": {
            "id": discipline.id,
            "slug": discipline.slug,
            "name": discipline.name,
            "kind": discipline.kind,
            "team_min": discipline.team_min,
            "team_max": discipline.team_max,
        },
        "closed_at": snap.closed_at if snap is not None else None,
        "fetched_at": fetched_at,
        "missing": missing,
        "count": sum(1 for r in counted if not r["withdrawn"]),
        "rows": _order(rows),
        "teams": team_rows,
        "persons": [
            {"key": p.key, "name": p.name, "club": p.club}
            for p in sorted(persons.values(), key=lambda p: (p.name.casefold(), p.key))
        ],
    }
