"""The Export phase's band of tables.

The band is derived from the tournament rather than declared: a fencer table,
one table per discipline — individual and team alike — and one per extra-item
category the tournament offers at least one item in (spec export-tables, The
Export phase is a band of tables). A tournament selling parking is exported as
completely as one selling T-shirts, and a category nobody offers has no table
at all.

A team discipline's tab is a list of teams with their fighters beneath each,
because the thing being seeded is a team and a flat list would hide which four
numbers belong together (design D11). It is the only tab whose rows are of two
kinds, and `team_rows` is where that is stated.

Narrowing and ordering live here rather than in the console because two
surfaces read them: the console's tabs and the spreadsheet the export writes.
The one order this module does not produce is the seeding order — rating
descending, which a discipline tab takes when the organizer ticks it.
That tick is the reader's own state and never leaves the screen, so the
console sorts for it over the rows this module hands back.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.availability import live_teams
from app.models import (
    ACTION_CATEGORIES,
    Discipline,
    DisciplineKind,
    ExtraCategory,
    RegistrationsKeptBy,
    Tournament,
)
from app.rules import Row

FENCERS = "fencers"
DISCIPLINE = "discipline"
CATEGORY = "category"
# the band's last tab, whose table is `exportsummary`'s rather than a
# narrowing of the fencer table
SUMMARY = "summary"
# after it, the revenue: `exportrevenue`'s table, again not a narrowing of the
# fencer table
REVENUE = "revenue"

# goods before programme, as `frontend/src/extraItems.ts` orders them: what a
# fencer takes home first, what happens at the tournament second
_CATEGORY_ORDER = [c for c in ExtraCategory if c not in ACTION_CATEGORIES] + [
    c for c in ExtraCategory if c in ACTION_CATEGORIES
]


@dataclass(frozen=True)
class Tab:
    """One table of the band.

    `key` names what the table is of — a discipline's slug, a category's
    value — and is empty for the fencer table, which is of the whole
    tournament. `line` is the label a discipline tab's capacity line carries:
    a queue boundary where the tournament's mode creates substitute
    placements, a bare capacity mark where it does not, so a reader is never
    left inferring it from a setting they may not know about.

    `teams` marks a discipline tab whose population is teams rather than
    fencers: its rows are of two kinds, its capacity and its counts are in
    teams, and it offers no seeding tick (spec export-tables). A tab that
    happens to hold no team is still one — the shape of a tab follows the
    discipline, never its contents.
    """

    kind: str
    key: str
    label: str
    capacity: int | None = None
    line: str | None = None
    teams: bool = False


def _line_kind(tournament: Tournament) -> str:
    """What a discipline tab's line means on this tournament.

    Manual mode keeps the list outside Squire and demotes nobody to a queue
    (spec tournament-mode), so its line marks where capacity falls and names no
    fencer as queued.
    """
    return "queue" if tournament.registrations_kept_by is RegistrationsKeptBy.SQUIRE else "capacity"


def individual_disciplines(tournament: Tournament) -> list[Discipline]:
    """The tournament's individual disciplines, in its own discipline order."""
    return [d for d in tournament.disciplines if d.kind is DisciplineKind.INDIVIDUAL]


def band_disciplines(tournament: Tournament) -> list[Discipline]:
    """Every discipline the band carries a tab for, in the tournament's own
    order: individual and team alike.

    A team discipline has one because its fighters carry ratings and rating and
    rank are stated on a discipline tab and nowhere else — fetched with no tab
    to show them, they would be unreadable (design, Context).
    """
    return list(tournament.disciplines)


def offered_categories(tournament: Tournament) -> list[ExtraCategory]:
    """The extra-item categories this tournament has at least one item in."""
    offered = {item.category for item in tournament.extra_items}
    return [category for category in _CATEGORY_ORDER if category in offered]


def tabs(tournament: Tournament) -> list[Tab]:
    band = [Tab(kind=FENCERS, key="", label=FENCERS)]
    line = _line_kind(tournament)
    band += [
        Tab(
            kind=DISCIPLINE,
            key=discipline.slug,
            label=discipline.name or discipline.slug,
            capacity=discipline.capacity,
            line=line,
            teams=discipline.kind is DisciplineKind.TEAM,
        )
        for discipline in band_disciplines(tournament)
    ]
    band += [
        Tab(kind=CATEGORY, key=category.value, label=category.value)
        for category in offered_categories(tournament)
    ]
    # every tournament has one, whatever it offers: disciplines alone are
    # something to total
    band.append(Tab(kind=SUMMARY, key="", label=SUMMARY))
    # and a free tournament still has entries to total, at zero
    band.append(Tab(kind=REVENUE, key="", label=REVENUE))
    return band


def find_tab(tournament: Tournament, kind: str, key: str) -> Tab | None:
    return next((tab for tab in tabs(tournament) if tab.kind == kind and tab.key == key), None)


def _paid_first(rows: list[Row]) -> list[Row]:
    """Paid rows first, each group keeping the projection's own order — which
    is registration order. A stable sort, so the second key needs no
    expression."""
    return sorted(rows, key=lambda row: not row.get("paid"))


def _hr_first(row: Row) -> Row:
    """The row as the export states it: where it is bound to a HEMA Ratings
    profile, the profile's nationality and club stand over the ones the fencer
    gave. What HR records is what the tournament's tooling downstream
    reconciles against, and a club the fencer left blank is often one HR knows.
    A value HR does not carry leaves the fencer's own standing."""
    if row.get("hr_id") is None:
        return row
    return {
        **row,
        "nationality": row.get("hr_nationality") or row.get("nationality"),
        "club": row.get("hr_club") or row.get("club"),
    }


@dataclass(frozen=True)
class TeamEntry:
    """One team of a team discipline, as that discipline's tab lists it.

    `member_row_ids` is how the tab finds this team's fighters among the
    projected rows: by the member's own row id, never by the team's name, since
    nothing stops a registration entering two teams of one name (design
    team-disciplines D9). `team_id` is the team's own identity, for the same
    reason: it is what the tab's row is keyed by.
    """

    team_id: int
    discipline: str
    name: str
    entering_fencer: str
    team_min: int
    team_max: int
    paid: bool
    waitlist_position: int | None
    member_row_ids: tuple[str, ...]


def team_entries(session: Session, tournament: Tournament) -> list[TeamEntry]:
    """Every team of every team discipline, in the order its tab lists them:
    the seated teams first by paid then the moment the team entered, and the
    waitlisted below them in waitlist order (spec export-tables, A discipline
    tab is a seeding roster).

    Reads the database, unlike the rest of this module: a team is not a row of
    the fencer projection, and what a tab states about one — its entering
    fencer, its member count against the discipline's bounds, its waitlist
    place and the standing of the registration it was entered on — lives on the
    team itself.
    """
    entries: list[TeamEntry] = []
    for discipline in tournament.disciplines:
        if discipline.kind is not DisciplineKind.TEAM:
            continue
        teams = live_teams(session, discipline)
        waiting = 0
        seated: list[TeamEntry] = []
        waitlisted: list[TeamEntry] = []
        for team in teams:
            if team.waitlisted:
                waiting += 1
            entry = TeamEntry(
                team_id=team.id,
                discipline=discipline.slug,
                name=team.name,
                entering_fencer=team.registration.fencer.display_name,
                # a team discipline always carries both bounds on write; read as
                # no bound rather than refuse the tab
                team_min=discipline.team_min or 0,
                team_max=discipline.team_max or 0,
                # a team is paid for once, on the registration it was entered on
                paid=team.registration.settled,
                waitlist_position=waiting if team.waitlisted else None,
                member_row_ids=tuple(f"mem:{member.id}" for member in team.members),
            )
            (waitlisted if team.waitlisted else seated).append(entry)
        # `live_teams` hands them back in waitlist order, which for a seated
        # team is entry order; paid first over it, stably
        entries += sorted(seated, key=lambda entry: not entry.paid)
        entries += waitlisted
    return entries


def team_row(entry: TeamEntry) -> Row:
    """A team as a row of its discipline's tab.

    It carries the team's own facts under `_team` and the cells it shares with
    a fighter — a name, and the paid mark, which belongs to the team because a
    team is paid for once. No nationality, club, identifier, rating or rank: a
    team has none, and nothing here computes one from its fighters' (design
    D10).
    """
    return {
        # keyed by the team's own identity, never by its name: a registration
        # may enter two teams of one name into one discipline (design
        # team-disciplines D9), and the tab's rows must still be told apart
        "id": f"team:{entry.team_id}",
        "name": entry.name,
        "nationality": None,
        "club": None,
        "hr_id": None,
        "paid": entry.paid,
        "ratings": {},
        "ranks": {},
        "_team": {
            "entering_fencer": entry.entering_fencer,
            "members": len(entry.member_row_ids),
            "team_min": entry.team_min,
            "team_max": entry.team_max,
            "waitlist_position": entry.waitlist_position,
        },
    }


def team_table(rows: list[Row], tab: Tab, teams: Sequence[TeamEntry]) -> list[Row]:
    """A team discipline's tab: each team in the tab's order, its fighters
    beneath it in roster order.

    A fighter states no paid cell of its own — it holds no registration — and
    the position column numbers the teams rather than the fighters, which the
    console reads off `_team` (spec export-tables, Each tab states its own
    columns and order).

    A team whose roster names nobody is listed all the same: an empty roster is
    a fact about the entry, and dropping the team would hide it.
    """
    by_id = {row["id"]: row for row in rows if not row.get("_deleted")}
    table: list[Row] = []
    for entry in teams:
        if entry.discipline != tab.key:
            continue
        table.append(team_row(entry))
        table += [_hr_first(by_id[row_id]) for row_id in entry.member_row_ids if row_id in by_id]
    return table


def table_rows(rows: list[Row], tab: Tab, teams: Sequence[TeamEntry] = ()) -> list[Row]:
    """The rows of one table: the replayed fencer table narrowed to what the
    tab is of, in the tab's own order.

    A row a deletion took out of the table is in no tab, as it is in no export.
    Membership of a discipline is left on the row — `disciplines` for a seated
    entry, `substitute_for` for a queued one — so the console draws the
    capacity line from the rows it already holds.

    The Fencers tab is the fencer list and follows it, member rows included: a
    registration that bought nothing but team entries is not a fighter and
    appears on no tab (spec etl-console, The fencer list is the tournament's
    start field). A team discipline's tab is `team_table`'s, and needs the
    teams `team_entries` reads.
    """
    live = [_hr_first(row) for row in rows if not row.get("_deleted")]
    if tab.kind == FENCERS:
        return [row for row in live if row.get("fights", True)]
    if tab.kind == DISCIPLINE:
        if tab.teams:
            return team_table(rows, tab, teams)
        return _paid_first(
            [
                row
                for row in live
                if tab.key in (row.get("disciplines") or [])
                or tab.key in (row.get("substitute_for") or [])
            ]
        )
    return _paid_first([row for row in live if (row.get("extras") or {}).get(tab.key)])


def tab_counts(
    rows: list[Row], tab: Tab, teams: Sequence[TeamEntry] = ()
) -> tuple[int | None, int]:
    """How many a tab lists, as the band states it beside the tab's name:
    `(count, queued)` (spec export-tables, Every tab states how many it lists).

    Counted over `table_rows`, so a deleted row counts nowhere and an item tab
    counts its buyers. A discipline splits its population the way its capacity
    line does — a row not seated in the discipline is holding a substitute
    entry in it — and every other tab has no queue. A team discipline counts in
    teams, seated against waitlisted, as its capacity is in teams. The
    active-only switch is the reader's own and never reaches a count.

    The summary and the revenue state no count: their lines are an offer, not
    a population, and a number beside them would read as comparable with the
    others.
    """
    if tab.kind in (SUMMARY, REVENUE):
        return None, 0
    if tab.teams:
        own = [entry for entry in teams if entry.discipline == tab.key]
        waiting = sum(1 for entry in own if entry.waitlist_position is not None)
        return len(own) - waiting, waiting
    listed = table_rows(rows, tab, teams)
    if tab.kind != DISCIPLINE:
        return len(listed), 0
    queued = sum(1 for row in listed if tab.key not in (row.get("disciplines") or []))
    return len(listed) - queued, queued
