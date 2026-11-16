"""The floor's one door into the office (spec floor-roster; design
add-floor-boundary D1, D6).

The only floor file that imports office modules. It builds the port in
`app.floor.roster` from the same replay the public roster reads, narrowed by the
same public steps `entrants.rosters()` takes, so the floor's seated entrants are
the public roster's. It reads and never writes.

It also hands `api.py` the request dependencies that resolve a tournament from
its slug, so that the router names no office module.
"""

from sqlalchemy.orm import Session

from app import entrants, exporttables, rules, sheet
from app.floor.roster import FloorDiscipline, IndividualEntry, Person, Roster, TeamEntry
from app.models import DisciplineKind, Tournament
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.rules import Row

__all__ = ["FencerDep", "SessionDep", "TournamentDep", "roster"]


def _individual(person: str, slug: str, row: Row) -> IndividualEntry:
    return IndividualEntry(
        person=person,
        discipline=slug,
        rating=(row.get("ratings") or {}).get(slug),
        rank=(row.get("ranks") or {}).get(slug),
        # the registration's settled state, as the replay states it (design D4)
        paid=bool(row.get("paid")),
    )


def _confirmed_hr_id(row: Row) -> int | None:
    return row.get("hr_id") if row.get("match_verdict") == "confirmed" else None


def _member_number(key: str) -> int:
    return int(key.removeprefix("mem:"))


def _anchors(registered: dict[str, Row], members: dict[str, Row]) -> dict[str, str]:
    """Each row id to the row id of the person it is (design D2).

    Rows from different populations — a registration-backed row and member
    rows, or several member rows — are one person when all carry one confirmed
    HEMA Ratings identifier. The anchor is the registration-backed row, else the
    lowest member id. Two registration-backed rows sharing an identifier are a
    duplicate the office's dedup resolves, so that identifier joins nothing."""
    by_hr: dict[int, tuple[list[str], list[str]]] = {}
    for population, rows in ((0, registered), (1, members)):
        for key, row in rows.items():
            hr_id = _confirmed_hr_id(row)
            if hr_id is not None:
                by_hr.setdefault(hr_id, ([], []))[population].append(key)
    anchor = {key: key for key in (*registered, *members)}
    for regs, mems in by_hr.values():
        if len(regs) > 1 or len(regs) + len(mems) < 2:
            continue
        target = regs[0] if regs else min(mems, key=_member_number)
        for key in (*regs, *mems):
            anchor[key] = target
    return anchor


def roster(session: Session, tournament: Tournament) -> Roster:
    """The tournament's seated entrants, per discipline, as the floor knows them."""
    replayed, _ = rules.replay(
        sheet.base_rows(session, tournament),
        rules.active_rules(session, tournament),
        sheet.rating_lookup(session, tournament),
    )
    rows = list(replayed.values())
    live = entrants.live_registration_ids(session, tournament)
    removed = entrants.removed_registration_ids(session, tournament)

    disciplines: list[FloorDiscipline] = []
    # row id → the row as the public individual roster reads it (HEMA Ratings'
    # club and nationality first), for every row holding a seated entry
    registered: dict[str, Row] = {}
    individuals: list[tuple[str, str, Row]] = []
    for discipline in tournament.disciplines:
        disciplines.append(
            FloorDiscipline(
                slug=discipline.slug,
                name=discipline.name,
                kind="team" if discipline.kind is DisciplineKind.TEAM else "individual",
            )
        )
        if discipline.kind is DisciplineKind.TEAM:
            continue
        tab = exporttables.Tab(kind=exporttables.DISCIPLINE, key=discipline.slug, label="")
        for row in exporttables.table_rows(rows, tab):
            if row.get("registration_id") in live and discipline.slug in (
                row.get("disciplines") or []
            ):
                registered[row["id"]] = row
                individuals.append((row["id"], discipline.slug, row))

    # seated teams of live registrations, less those whose entering row the
    # organizer took out of the table, as the public roster leaves them out
    teams = [
        entry
        for entry in exporttables.team_entries(session, tournament)
        if entry.waitlist_position is None and entry.registration_id not in removed
    ]
    # a member as the public team roster reads it: the replayed row as it stands
    members: dict[str, Row] = {}
    for entry in teams:
        for key in entry.member_row_ids:
            row = replayed.get(key)
            if row is None:
                # `base_rows` projects every member of a live registration's team
                raise LookupError(f"team member row {key} is missing from the replay")
            members[key] = row

    anchor = _anchors(registered, members)
    persons: dict[str, Person] = {}
    for key in sorted(set(anchor.values())):
        row = registered.get(key) or members[key]
        persons[key] = Person(
            key=key,
            name=row["name"],
            club=row.get("club"),
            nationality=row.get("nationality"),
            hr_id=row.get("hr_id"),
        )

    return Roster(
        disciplines=tuple(disciplines),
        persons=tuple(persons.values()),
        individuals=tuple(_individual(anchor[key], slug, row) for key, slug, row in individuals),
        teams=tuple(
            TeamEntry(
                key=f"team:{entry.team_id}",
                discipline=entry.discipline,
                name=entry.name,
                members=tuple(anchor[key] for key in entry.member_row_ids),
                paid=entry.paid,
            )
            for entry in teams
        ),
    )
