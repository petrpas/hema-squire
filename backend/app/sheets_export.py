"""Google Sheets export: one worksheet per export table, with preserve/refresh
semantics.

The merge is a pure function over the existing worksheet grid and the current
roster; the SheetsClient protocol only reads and writes whole worksheets, so
the semantics live here and run identically against the in-memory test fake
and the gspread client. Per the spec: Reg./No. cells are never touched,
HRating/HRank always refresh, every other cell is written only when blank
(downstream manual work wins), and deleted rows appear in no worksheet.

A column has an **identity** and a **label**. The label is rendered through
`app.i18n`, so a Czech organizer's spreadsheet reads Czech and an English
export reads English; the identity is what the merge addresses old cells by,
matching every label that column has ever carried in any locale. Without that
split, switching the export's language would read as every column being
dropped and a new one arriving — and the numbering downstream staff fill in by
hand would be lost by a tick.
"""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app import exporttables
from app.i18n import catalog
from app.models import ExtraCategory, Tournament
from app.rules import Row

FENCERS_SHEET = "Fencers"

# Worksheet names are addresses, not prose: the merge finds an existing sheet
# by its name, so renaming one with the export's language would orphan the
# organizer's own numbering. They stay put in every locale.
CATEGORY_SHEETS = {
    ExtraCategory.RENTAL: "Rentals",
    ExtraCategory.MERCH: "Merch",
    ExtraCategory.OTHER_ITEM: "Other items",
    ExtraCategory.SEMINAR: "Seminars",
    ExtraCategory.AFTERPARTY: "Afterparty",
    ExtraCategory.OTHER_ACTION: "Other programme",
}


@dataclass(frozen=True)
class Column:
    """One column of one export table.

    `preserved` marks a column downstream staff manage by hand, which the
    export never writes; `refreshed` one that is written afresh every time
    rather than only when blank — the rating, which is what the tournament
    currently holds and never a cell to be preserved.
    """

    id: str
    preserved: bool = False
    refreshed: bool = False

    @property
    def key(self) -> str:
        return f"export.column.{self.id}"


REG = Column("reg", preserved=True)
NUMBER = Column("no", preserved=True)
NAME = Column("name")
NATIONALITY = Column("nat")
CLUB = Column("club")
HR_ID = Column("hr_id")
DISCIPLINES = Column("disciplines")
RATING = Column("rating", refreshed=True)
RANK = Column("rank", refreshed=True)
ITEMS = Column("items")
PAID = Column("paid")

FENCERS_COLUMNS = [REG, NAME, NATIONALITY, CLUB, HR_ID, DISCIPLINES, PAID]
DISCIPLINE_COLUMNS = [NUMBER, NAME, NATIONALITY, CLUB, HR_ID, RATING, RANK, PAID]
CATEGORY_COLUMNS = [NAME, NATIONALITY, CLUB, ITEMS, PAID]


def header_for(columns: list[Column], locale: str) -> list[str]:
    return [catalog.translate(column.key, locale) for column in columns]


def _labels(column: Column) -> set[str]:
    """Every label this column carries, in every locale Squire speaks.

    An existing grid was written in one of them — or in the v1 format, whose
    headers are the English ones — and the merge has to recognise its own
    column whichever it was.
    """
    return {catalog.translate(column.key, locale) for locale in catalog.available()}


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _identity(name: str, hr_id: str) -> str:
    return f"hr:{hr_id}" if hr_id else f"name:{_fold(name)}"


def _yes_no(value: bool, locale: str) -> str:
    return catalog.translate("export.yes" if value else "export.no", locale)


def _common_values(row: Row, locale: str) -> dict[str, str]:
    return {
        NAME.id: row.get("name") or "",
        NATIONALITY.id: row.get("nationality") or "",
        CLUB.id: row.get("club") or "",
        HR_ID.id: str(row["hr_id"]) if row.get("hr_id") is not None else "",
        PAID.id: _yes_no(bool(row.get("paid")), locale),
    }


def _fencer_values(row: Row, locale: str) -> dict[str, str]:
    return {
        **_common_values(row, locale),
        DISCIPLINES.id: ", ".join(row.get("disciplines") or []),
    }


def _discipline_values(row: Row, slug: str, locale: str) -> dict[str, str]:
    """A seeding row. The rating is read off the replayed row, so an
    organizer's correction is what the sheet carries and a re-export never
    restores a stale fetched value over a typed one."""
    rating = (row.get("ratings") or {}).get(slug)
    rank = (row.get("ranks") or {}).get(slug)
    return {
        **_common_values(row, locale),
        RATING.id: "" if rating is None else str(rating),
        RANK.id: "" if rank is None else str(rank),
    }


def _item_label(selection: dict) -> str:
    label = selection.get("name") or ""
    if selection.get("option"):
        label = f"{label} ({selection['option']})"
    qty = selection.get("qty") or 1
    return f"{label} x{qty}" if qty > 1 else label


def _category_values(row: Row, category: str, locale: str) -> dict[str, str]:
    selections = (row.get("extras") or {}).get(category) or []
    return {
        **_common_values(row, locale),
        ITEMS.id: ", ".join(_item_label(selection) for selection in selections),
    }


class SheetsClient(Protocol):
    def read(self, worksheet: str) -> list[list[str]] | None: ...

    def write(self, worksheet: str, grid: list[list[str]]) -> None: ...


def merge_grid(
    existing: list[list[str]] | None,
    columns: list[Column],
    roster: list[tuple[str, dict[str, str]]],
    locale: str,
) -> list[list[str]]:
    """Merge the roster into the existing grid.

    `roster` is (identity, column values by column id) in export order.
    Existing rows keep their order and preserved cells; rows whose identity
    left the roster are dropped; new roster entries append at the bottom with
    preserved cells blank.

    A column of the existing grid is found by any label it has ever carried, so
    a grid written in the v1 format — or in another language — keeps its
    contents where the column remains, and loses them only where the column
    itself is gone.
    """
    header = header_for(columns, locale)
    old_header = existing[0] if existing else header
    old_rows = existing[1:] if existing else []

    positions: dict[str, int] = {}
    for column in columns:
        labels = _labels(column)
        for index, label in enumerate(old_header):
            if label in labels:
                positions[column.id] = index
                break

    def cell(row: list[str], column: Column) -> str:
        position = positions.get(column.id)
        if position is None or position >= len(row):
            return ""
        return row[position]

    values_by_identity = dict(roster)
    merged: list[list[str]] = [header]
    seen: set[str] = set()
    for old_row in old_rows:
        identity = _identity(cell(old_row, NAME), cell(old_row, HR_ID))
        values = values_by_identity.get(identity)
        if values is None or identity in seen:
            continue  # withdrawn, deleted, or duplicate — gone from the export
        seen.add(identity)
        merged.append(
            [
                cell(old_row, column)
                if column.preserved
                else values[column.id]
                if column.refreshed or not cell(old_row, column).strip()
                else cell(old_row, column)
                for column in columns
            ]
        )
    for identity, values in roster:
        if identity in seen:
            continue
        merged.append(["" if column.preserved else values[column.id] for column in columns])
    return merged


def _roster(rows: list[Row], values: Callable[[Row], dict[str, str]]):
    return [
        (_identity(row.get("name") or "", str(row.get("hr_id") or "")), values(row))
        for row in rows
        if row.get("name")
    ]


def export_to_sheets(
    tournament: Tournament,
    rows: list[Row],
    client: SheetsClient,
    locale: str,
) -> dict:
    """One worksheet per export table, each carrying its table's columns and
    its table's order (spec data-export, Google Sheets export mirrors the
    export tables).

    Which tables there are is `exporttables`' answer, not this module's: the
    console's band and the spreadsheet are the same set of tables, and a
    tournament selling nothing in a category has neither a tab nor a
    worksheet.
    """
    written: list[str] = []
    fencers = 0
    for tab in exporttables.tabs(tournament):
        table = exporttables.table_rows(rows, tab)
        if tab.kind == exporttables.FENCERS:
            name, columns = FENCERS_SHEET, FENCERS_COLUMNS
            roster = _roster(table, lambda row: _fencer_values(row, locale))
            fencers = len(roster)
        elif tab.kind == exporttables.DISCIPLINE:
            name, columns = tab.key, DISCIPLINE_COLUMNS
            roster = _roster(table, lambda row, slug=tab.key: _discipline_values(row, slug, locale))
        else:
            name, columns = CATEGORY_SHEETS[ExtraCategory(tab.key)], CATEGORY_COLUMNS
            roster = _roster(
                table, lambda row, category=tab.key: _category_values(row, category, locale)
            )
        client.write(name, merge_grid(client.read(name), columns, roster, locale))
        written.append(name)
    return {"worksheets": written, "fencers": fencers}


class GspreadSheetsClient:
    """Real Google Sheets access via a service account."""

    def __init__(self, credentials_path: str, spreadsheet_url: str):
        import gspread

        gc = gspread.service_account(filename=credentials_path)
        self._spreadsheet = gc.open_by_url(spreadsheet_url)

    def read(self, worksheet: str) -> list[list[str]] | None:
        import gspread

        try:
            return self._spreadsheet.worksheet(worksheet).get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            return None

    def write(self, worksheet: str, grid: list[list[str]]) -> None:
        import gspread

        try:
            sheet = self._spreadsheet.worksheet(worksheet)
        except gspread.exceptions.WorksheetNotFound:
            sheet = self._spreadsheet.add_worksheet(
                title=worksheet, rows=max(200, len(grid) + 10), cols=len(grid[0]) + 3
            )
        sheet.clear()
        sheet.update(grid, "A1")


# A per-tournament client, or None where the tournament names no output sheet.
type SheetsClientFactory = Callable[[Tournament], GspreadSheetsClient | None]


def get_sheets_client_factory() -> SheetsClientFactory | None:
    """FastAPI dependency returning a per-tournament client factory, or None
    when Google credentials are not configured."""
    from app.config import settings

    if not settings.google_credentials_path:
        return None

    def factory(tournament: Tournament) -> GspreadSheetsClient | None:
        if not tournament.output_sheet_url:
            return None
        return GspreadSheetsClient(settings.google_credentials_path, tournament.output_sheet_url)

    return factory
