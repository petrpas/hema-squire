"""Google Sheets export: one worksheet per export table, with preserve/refresh
semantics.

The merge is a pure function over the existing worksheet grid and the current
roster; the SheetsClient protocol only reads and writes whole worksheets, so
the semantics live here and run identically against the in-memory test fake
and the gspread client. Per the spec: the # position and HRating/HRank always
refresh, every other cell is written only when blank (downstream manual work
wins), and deleted rows appear in no worksheet.

A column has an **identity** and a **label**. The label is rendered through
`app.i18n`, so a Czech organizer's spreadsheet reads Czech and an English
export reads English; the identity is what the merge addresses old cells by,
matching every label that column has ever carried in any locale. Without that
split, switching the export's language would read as every column being
dropped and a new one arriving — and every cell downstream staff corrected by
hand would be overwritten by a tick.
"""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app import exportsummary, exporttables
from app.i18n import catalog
from app.models import ExtraCategory, Tournament
from app.rules import Row

FENCERS_SHEET = "Fencers"
SUMMARY_SHEET = "Summary"

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

    `refreshed` marks one that is written afresh every time rather than only
    when blank — the rating, which is what the tournament currently holds and
    never a cell to be preserved. `numeric` one whose cells go to the
    spreadsheet as numbers, so they stand right-aligned and sort by magnitude
    rather than as text.
    """

    id: str
    refreshed: bool = False
    numeric: bool = False

    @property
    def key(self) -> str:
        return f"export.column.{self.id}"


POSITION = Column("position", refreshed=True, numeric=True)
NAME = Column("name")
NATIONALITY = Column("nat")
CLUB = Column("club")
HR_ID = Column("hr_id", numeric=True)
DISCIPLINES = Column("disciplines")
RATING = Column("rating", refreshed=True, numeric=True)
RANK = Column("rank", refreshed=True, numeric=True)
ITEMS = Column("items")
PAID = Column("paid")
# the summary's columns; its counts are written as the numbers they are
ITEM = Column("item")
UNPAID = Column("unpaid")

FENCERS_COLUMNS = [POSITION, NAME, NATIONALITY, CLUB, HR_ID, DISCIPLINES, PAID]
DISCIPLINE_COLUMNS = [POSITION, NAME, NATIONALITY, CLUB, HR_ID, RATING, RANK, PAID]
CATEGORY_COLUMNS = [POSITION, NAME, NATIONALITY, CLUB, ITEMS, PAID]
SUMMARY_COLUMNS = [ITEM, PAID, UNPAID]


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


Cell = str | int | float


class SheetsClient(Protocol):
    def read(self, worksheet: str) -> list[list[str]] | None: ...

    def write(self, worksheet: str, grid: list[list[Cell]]) -> None: ...


def _number(text: str) -> Cell:
    """The number a cell states, or the text itself where it states none — a
    blank rating, or a cell downstream staff wrote a word into."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def typed_grid(grid: list[list[str]], columns: list[Column]) -> list[list[Cell]]:
    """The merged grid as it is written: numeric columns' cells as numbers.

    The merge works in text, as the spreadsheet reads back; only the write
    types them. A number sent as a number is stored as one whatever locale the
    spreadsheet is set to, where text parsed by the spreadsheet would read
    1250.5 as a date in a Czech one.
    """
    numeric = {index for index, column in enumerate(columns) if column.numeric}
    header, *rows = grid
    return [
        list(header),
        *(
            [_number(value) if index in numeric else value for index, value in enumerate(row)]
            for row in rows
        ),
    ]


def merge_grid(
    existing: list[list[str]] | None,
    columns: list[Column],
    roster: list[tuple[str, dict[str, str]]],
    locale: str,
) -> list[list[str]]:
    """Merge the roster into the existing grid.

    `roster` is (identity, column values by column id) in export order.
    Existing rows keep their order and their non-blank cells; rows whose
    identity left the roster are dropped; new roster entries append at the
    bottom.

    A column of the existing grid is found by any label it has ever carried, so
    a grid written in the v1 format — or in another language — keeps its
    contents where the column remains, and loses them only where the column
    itself is gone.

    The position column numbers the merged grid's rows 1..n top to bottom,
    rewritten every time. It numbers the sheet as it stands, not the console's
    order: the merge keeps old rows where they are, so after a re-export the
    two can differ, and a column that skipped numbers down the sheet would
    serve nobody reading it.
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
        return str(row[position])

    values_by_identity = {identity: {**values, POSITION.id: ""} for identity, values in roster}
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
                values[column.id]
                if column.refreshed or not cell(old_row, column).strip()
                else cell(old_row, column)
                for column in columns
            ]
        )
    for identity, _ in roster:
        if identity in seen:
            continue
        values = values_by_identity[identity]
        merged.append([values[column.id] for column in columns])
    if POSITION in columns:
        index = columns.index(POSITION)
        for number, row in enumerate(merged[1:], start=1):
            row[index] = str(number)
    return merged


def _roster(rows: list[Row], values: Callable[[Row], dict[str, str]]):
    return [
        (_identity(row.get("name") or "", str(row.get("hr_id") or "")), values(row))
        for row in rows
        if row.get("name")
    ]


def summary_label(line: exportsummary.SummaryLine, locale: str) -> str:
    """A summary line's item cell: `LSM (fronta)`, `Triko – XL`, `Triko –
    neuvedeno`. The names are the organizer's and stay as written; only the
    words Squire adds follow the export's language."""
    if line.kind == exportsummary.QUEUE:
        return catalog.translate("export.summary.queue", locale, name=line.name)
    if line.missing:
        option = catalog.translate("export.summary.missing", locale)
        return catalog.translate("export.summary.option", locale, name=line.name, option=option)
    if line.option is not None:
        return catalog.translate(
            "export.summary.option", locale, name=line.name, option=line.option
        )
    return line.name


def summary_grid(tournament: Tournament, rows: list[Row], locale: str) -> list[list[Cell]]:
    """The Summary worksheet, whole. It is not merged with what the sheet
    held: its lines have no identity a cell could be kept by, and a count
    preserved from the last export would be a stale one (spec data-export,
    Repeat-export preservation semantics)."""
    header: list[Cell] = [*header_for(SUMMARY_COLUMNS, locale)]
    return [
        header,
        *(
            [summary_label(line, locale), line.paid, line.unpaid]
            for line in exportsummary.summary_lines(tournament, rows)
        ),
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
        if tab.kind == exporttables.SUMMARY:
            client.write(SUMMARY_SHEET, summary_grid(tournament, rows, locale))
            written.append(SUMMARY_SHEET)
            continue
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
        merged = merge_grid(client.read(name), columns, roster, locale)
        client.write(name, typed_grid(merged, columns))
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

    def write(self, worksheet: str, grid: list[list[Cell]]) -> None:
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


# Keyed on the credentials path, because the file does not change under a
# running server and the address is read on a request path. The path itself is
# the key rather than a bare flag, so a test that points the setting at another
# file is answered from that file and not from the first one read.
_SERVICE_ACCOUNTS: dict[str, str | None] = {}


def _client_email(credentials_path: str) -> str | None:
    """The address a service-account credentials file acts as, or None where
    the file is missing, unreadable, or not one.

    A file that cannot be read is not an error here: it is the same state as no
    credentials at all, which the console already has something to say about.
    Raising instead would turn a deployment that was never configured into a
    500 on a read the organizer cannot act on.
    """
    if credentials_path in _SERVICE_ACCOUNTS:
        return _SERVICE_ACCOUNTS[credentials_path]
    import json
    from pathlib import Path

    email: str | None = None
    try:
        loaded = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
    except OSError, ValueError:
        loaded = None
    if isinstance(loaded, dict):
        found = loaded.get("client_email")
        if isinstance(found, str) and found:
            email = found
    _SERVICE_ACCOUNTS[credentials_path] = email
    return email


def service_account_email() -> str | None:
    """The address the Sheets export writes as, for the console to state.

    An organizer has to share their spreadsheet with this address for writing:
    the service account is its own identity, and the organizer's own access to
    the document grants it nothing. It is read from the credentials the export
    actually uses rather than configured a second time, so that the address the
    console states and the address that opens the spreadsheet cannot disagree.
    """
    from app.config import settings

    if not settings.google_credentials_path:
        return None
    return _client_email(settings.google_credentials_path)
