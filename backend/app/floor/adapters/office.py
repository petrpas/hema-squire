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

from app import entrants, exporttables, rules, setup, sheet
from app.floor.roster import FloorDiscipline, IndividualEntry, Person, Roster, TeamEntry
from app.floor.setup import Tournament as SetupTournament
from app.list_counts import same_person
from app.models import DisciplineKind, Tournament
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.rules import Row

__all__ = ["FencerDep", "SessionDep", "TournamentDep", "has_floor", "roster", "setup_facts"]


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
    """The identifier the row's own record holds. A proposal from the matcher
    is not one: the office's public count reads only stored identifiers."""
    return row.get("hr_id") if row.get("match_verdict") == "confirmed" else None


def _member_number(key: str) -> int:
    return int(key.removeprefix("mem:"))


def _same(a: Row, b: Row) -> bool:
    return same_person(a["name"], _confirmed_hr_id(a), b["name"], _confirmed_hr_id(b))


def _anchors(
    registered: dict[str, Row], members: dict[str, Row], team_of: dict[str, int]
) -> dict[str, str]:
    """Each row id to the row id of the person it is (spec floor-roster; design
    add-floor-console D8).

    A member row joins a person by the office's own rule (`same_person`): the
    same stored identifier, or, where either has none, the same folded name.
    Registration-backed rows are never joined to each other, and two members of
    one team never become one person. Persons are tried in anchor order —
    registration-backed rows first, then member-only persons by lowest member
    id — and a member joins the first whose every row it is the same person as,
    so no person ends up holding two different identifiers."""
    groups: list[list[str]] = [[key] for key in registered]
    rows = {**registered, **members}
    for key in sorted(members, key=_member_number):
        row = members[key]
        team = team_of[key]
        for group in groups:
            if any(team_of.get(other) == team for other in group):
                continue
            if all(_same(row, rows[other]) for other in group):
                group.append(key)
                break
        else:
            groups.append([key])
    return {key: group[0] for group in groups for key in group}


def _disciplines(tournament: Tournament) -> tuple[FloorDiscipline, ...]:
    return tuple(
        FloorDiscipline(
            id=discipline.id,
            slug=discipline.slug,
            name=discipline.name,
            kind="team" if discipline.kind is DisciplineKind.TEAM else "individual",
        )
        for discipline in tournament.disciplines
    )


def has_floor(tournament: Tournament) -> bool:
    """A discipline-less event has no tournament day (spec floor-console)."""
    return not tournament.is_event


def setup_facts(tournament: Tournament) -> SetupTournament:
    """What floor Setup reads of the tournament, without a replay."""
    return SetupTournament(
        id=tournament.id,
        date=tournament.date,
        disciplines=_disciplines(tournament),
        timezone=setup.zone_for(tournament).key,
    )


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

    disciplines = _disciplines(tournament)
    # row id → the row as the public individual roster reads it (HEMA Ratings'
    # club and nationality first), for every row holding a seated entry
    registered: dict[str, Row] = {}
    individuals: list[tuple[str, str, Row]] = []
    for discipline in tournament.disciplines:
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
    team_of: dict[str, int] = {}
    for entry in teams:
        for key in entry.member_row_ids:
            row = replayed.get(key)
            if row is None:
                # `base_rows` projects every member of a live registration's team
                raise LookupError(f"team member row {key} is missing from the replay")
            members[key] = row
            team_of[key] = entry.team_id

    anchor = _anchors(registered, members, team_of)
    joined: dict[str, list[Row]] = {}
    for key, target in anchor.items():
        rows_of = joined.setdefault(target, [])
        row = registered.get(key) or members[key]
        # the anchor's own row first
        rows_of.insert(0 if key == target else len(rows_of), row)
    persons: dict[str, Person] = {}
    for key in sorted(joined):
        row = joined[key][0]
        persons[key] = Person(
            key=key,
            name=row["name"],
            club=row.get("club"),
            nationality=row.get("nationality"),
            hr_id=row.get("hr_id"),
        )

    return Roster(
        date=tournament.date,
        timezone=setup.zone_for(tournament).key,
        disciplines=disciplines,
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
