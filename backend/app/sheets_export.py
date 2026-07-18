"""Google Sheets export in the v1 format, with preserve/refresh semantics.

The merge is a pure function over the existing worksheet grid and the current
roster; the SheetsClient protocol only reads and writes whole worksheets, so
the semantics live here and run identically against the in-memory test fake
and the gspread client. Per the spec: Reg./No. cells are never touched,
HRating/HRank always refresh, every other cell is written only when blank
(downstream manual work wins), and deleted rows appear in no worksheet.
"""

import unicodedata
from typing import Protocol

from app.hr_index import HRRating
from app.models import Tournament
from app.rules import Row

# ratings lookup from the tournament's latest snapshot: (hr_id, code) -> HRRating
Ratings = dict[tuple[int, str], HRRating]

FENCERS_SHEET = "Fencers"
FENCERS_HEADER = [
    "Reg.", "Name", "Nat.", "Club", "HR_ID", "Disciplines",
    "Paid", "Afterparty", "Borrow weapons", "Notes",
]
DISCIPLINE_HEADER = ["No.", "Name", "Nat.", "Club", "HR_ID", "HRating", "HRank"]

# columns downstream staff manage by hand; the export never writes them
PRESERVED = {"Reg.", "No."}
# columns that must always carry the freshest index data
REFRESHED = {"HRating", "HRank"}


class SheetsClient(Protocol):
    def read(self, worksheet: str) -> list[list[str]] | None: ...

    def write(self, worksheet: str, grid: list[list[str]]) -> None: ...


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _identity(name: str, hr_id: str) -> str:
    return f"hr:{hr_id}" if hr_id else f"name:{_fold(name)}"


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _fencer_values(row: Row) -> dict[str, str]:
    return {
        "Name": row.get("name") or "",
        "Nat.": row.get("nationality") or "",
        "Club": row.get("club") or "",
        "HR_ID": str(row["hr_id"]) if row.get("hr_id") is not None else "",
        "Disciplines": ", ".join(row.get("disciplines") or []),
        "Paid": _yes_no(bool(row.get("paid"))),
        "Afterparty": _yes_no(bool(row.get("afterparty"))),
        "Borrow weapons": ", ".join(row.get("weapon_rentals") or []),
        "Notes": row.get("notes") or "",
    }


def _discipline_values(row: Row, ratings: Ratings, code: str) -> dict[str, str]:
    rating = ratings.get((row["hr_id"], code)) if row.get("hr_id") is not None else None
    return {
        "Name": row.get("name") or "",
        "Nat.": row.get("nationality") or "",
        "Club": row.get("club") or "",
        "HR_ID": str(row["hr_id"]) if row.get("hr_id") is not None else "",
        "HRating": str(rating.rating) if rating and rating.rating is not None else "",
        "HRank": str(rating.rank) if rating and rating.rank is not None else "",
    }


def merge_grid(
    existing: list[list[str]] | None,
    header: list[str],
    roster: list[tuple[str, dict[str, str]]],
) -> list[list[str]]:
    """Merge the roster into the existing grid.

    `roster` is (identity, column values) in export order. Existing rows keep
    their order and preserved cells; rows whose identity left the roster are
    dropped; new roster entries append at the bottom with preserved cells blank.
    """
    old_header = existing[0] if existing else header
    old_rows = existing[1:] if existing else []

    def cell(row: list[str], column: str) -> str:
        if column in old_header:
            position = old_header.index(column)
            return row[position] if position < len(row) else ""
        return ""

    values_by_identity = dict(roster)
    merged: list[list[str]] = [header]
    seen: set[str] = set()
    for old_row in old_rows:
        identity = _identity(cell(old_row, "Name"), cell(old_row, "HR_ID"))
        values = values_by_identity.get(identity)
        if values is None or identity in seen:
            continue  # withdrawn, deleted, or duplicate — gone from the export
        seen.add(identity)
        merged.append(
            [
                cell(old_row, column)
                if column in PRESERVED
                else values[column]
                if column in REFRESHED or not cell(old_row, column).strip()
                else cell(old_row, column)
                for column in header
            ]
        )
    for identity, values in roster:
        if identity in seen:
            continue
        merged.append(["" if c in PRESERVED else values[c] for c in header])
    return merged


def export_to_sheets(
    tournament: Tournament,
    rows: list[Row],
    client: SheetsClient,
    ratings: Ratings,
) -> dict:
    active = [r for r in rows if not r.get("_deleted")]

    fencer_roster = [
        (_identity(r.get("name") or "", str(r.get("hr_id") or "")), _fencer_values(r))
        for r in active
        if r.get("name")
    ]
    client.write(
        FENCERS_SHEET, merge_grid(client.read(FENCERS_SHEET), FENCERS_HEADER, fencer_roster)
    )

    codes = [d.code for d in tournament.disciplines]
    for code in codes:
        entered = [r for r in active if code in (r.get("disciplines") or [])]
        roster = [
            (
                _identity(r.get("name") or "", str(r.get("hr_id") or "")),
                _discipline_values(r, ratings, code),
            )
            for r in entered
            if r.get("name")
        ]
        client.write(code, merge_grid(client.read(code), DISCIPLINE_HEADER, roster))

    return {"worksheets": [FENCERS_SHEET, *codes], "fencers": len(fencer_roster)}


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


def get_sheets_client_factory():
    """FastAPI dependency returning a per-tournament client factory, or None
    when Google credentials are not configured."""
    from app.config import settings

    if not settings.google_credentials_path:
        return None

    def factory(tournament: Tournament) -> GspreadSheetsClient | None:
        if not tournament.output_sheet_url:
            return None
        return GspreadSheetsClient(
            settings.google_credentials_path, tournament.output_sheet_url
        )

    return factory
