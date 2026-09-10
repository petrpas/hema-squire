"""The Export phase's band of tables.

The band is derived from the tournament rather than declared: a fencer table,
one table per individual discipline, and one per extra-item category the
tournament offers at least one item in (spec export-tables, The Export phase is
a band of tables). A tournament selling parking is exported as completely as
one selling T-shirts, and a category nobody offers has no table at all.

Narrowing and ordering live here rather than in the console because two
surfaces read them: the console's tabs and the spreadsheet the export writes.
The one order this module does not produce is the seeding order — rating
descending, which a discipline tab takes when it is switched to active only.
That switch is the reader's own state and never leaves the screen, so the
console sorts for it over the rows this module hands back.
"""

from dataclasses import dataclass

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
    """

    kind: str
    key: str
    label: str
    capacity: int | None = None
    line: str | None = None


def _line_kind(tournament: Tournament) -> str:
    """What a discipline tab's line means on this tournament.

    Manual mode keeps the list outside Squire and demotes nobody to a queue
    (spec tournament-mode), so its line marks where capacity falls and names no
    fencer as queued.
    """
    return "queue" if tournament.registrations_kept_by is RegistrationsKeptBy.SQUIRE else "capacity"


def individual_disciplines(tournament: Tournament) -> list[Discipline]:
    """The tournament's individual disciplines, in its own discipline order.

    A team discipline is not among them, for the reason it produces no
    worksheet: its entries are teams, not registrations, and there is no roster
    of individuals to seed.
    """
    return [d for d in tournament.disciplines if d.kind is DisciplineKind.INDIVIDUAL]


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
        )
        for discipline in individual_disciplines(tournament)
    ]
    band += [
        Tab(kind=CATEGORY, key=category.value, label=category.value)
        for category in offered_categories(tournament)
    ]
    return band


def find_tab(tournament: Tournament, kind: str, key: str) -> Tab | None:
    return next((tab for tab in tabs(tournament) if tab.kind == kind and tab.key == key), None)


def _paid_first(rows: list[Row]) -> list[Row]:
    """Paid rows first, each group keeping the projection's own order — which
    is registration order. A stable sort, so the second key needs no
    expression."""
    return sorted(rows, key=lambda row: not row.get("paid"))


def table_rows(rows: list[Row], tab: Tab) -> list[Row]:
    """The rows of one table: the replayed fencer table narrowed to what the
    tab is of, in the tab's own order.

    A row a deletion took out of the table is in no tab, as it is in no export.
    Membership of a discipline is left on the row — `disciplines` for a seated
    entry, `substitute_for` for a queued one — so the console draws the
    capacity line from the rows it already holds.
    """
    live = [row for row in rows if not row.get("_deleted")]
    if tab.kind == FENCERS:
        return live
    if tab.kind == DISCIPLINE:
        return _paid_first(
            [
                row
                for row in live
                if tab.key in (row.get("disciplines") or [])
                or tab.key in (row.get("substitute_for") or [])
            ]
        )
    return _paid_first([row for row in live if (row.get("extras") or {}).get(tab.key)])
