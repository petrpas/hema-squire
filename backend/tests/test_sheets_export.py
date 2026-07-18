"""Google Sheets export: v1 format, preserve/refresh semantics, export scope."""

import io

from app.hr_index import HRProfile, HRRating, StubHRIndex, get_hr_index
from app.importer import get_import_parser
from app.main import app
from app.sheets_export import get_sheets_client_factory
from tests.test_import import CSV, FakeParser


class InMemorySheets:
    def __init__(self):
        self.worksheets: dict[str, list[list[str]]] = {}

    def read(self, worksheet):
        return self.worksheets.get(worksheet)

    def write(self, worksheet, grid):
        self.worksheets[worksheet] = grid


class RatedIndex(StubHRIndex):
    """Stub index with mutable ratings, to prove HRating/HRank always refresh."""

    def __init__(self, profiles: list[HRProfile]):
        super().__init__(profiles)
        self.ratings: dict[int, HRRating] = {}

    def rating(self, hr_id, discipline_code):
        return self.ratings.get(hr_id)


def setup(client, auth_headers, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    for code in ("LS", "SA"):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"code": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )
    client.patch(
        "/api/tournaments/cup",
        json={"output_sheet_url": "https://sheets.example/cup"},
        headers=organizer,
    )
    # one in-app registration with an HR-bound account
    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    binding = client.post(
        "/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer
    )
    assert binding.status_code == 200, binding.text
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "afterparty": True},
        headers=fencer,
    )
    # two imported rows (SA)
    app.dependency_overrides[get_import_parser] = lambda: FakeParser()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
        headers=organizer,
    )


def wire(sheets, index):
    app.dependency_overrides[get_sheets_client_factory] = lambda: (
        lambda tournament: sheets
    )
    app.dependency_overrides[get_hr_index] = lambda: index


def export(client, organizer):
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()


def grid_row(grid, name):
    return next(r for r in grid[1:] if r[1] == name)


def test_export_writes_v1_format(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    index = RatedIndex([])
    index.ratings[10234] = HRRating(rating=1250.5, rank=17)
    wire(sheets, index)

    body = export(client, organizer)
    assert body["worksheets"] == ["Fencers", "LS", "SA"]

    fencers = sheets.worksheets["Fencers"]
    assert fencers[0] == ["Reg.", "Name", "Nat.", "Club", "HR_ID", "Disciplines",
                          "Paid", "Afterparty", "Borrow weapons", "Notes"]
    jan = grid_row(fencers, "Jan Novák")
    assert jan[0] == ""  # Reg. is downstream's column
    assert jan[4] == "10234"
    assert jan[5] == "LS"
    assert jan[6] == "No"  # payment state in the Paid column
    assert jan[7] == "Yes"

    ls = sheets.worksheets["LS"]
    assert ls[0] == ["No.", "Name", "Nat.", "Club", "HR_ID", "HRating", "HRank"]
    assert grid_row(ls, "Jan Novák")[5:7] == ["1250.5", "17"]
    # imported SA fencers land on the SA tab only
    assert len(sheets.worksheets["SA"]) == 3
    assert all(row[1] != "Jan Novák" for row in sheets.worksheets["SA"][1:])


def test_reexport_preserves_manual_work_and_refreshes_ratings(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    index = RatedIndex([])
    index.ratings[10234] = HRRating(rating=1250.5, rank=17)
    wire(sheets, index)
    export(client, organizer)

    # downstream staff number rows and fix a club by hand; a rating changes
    fencers = sheets.worksheets["Fencers"]
    jan = grid_row(fencers, "Jan Novák")
    jan[0] = "R-01"
    jan[3] = "Praha Sword Society"
    ls = sheets.worksheets["LS"]
    grid_row(ls, "Jan Novák")[0] = "7"
    index.ratings[10234] = HRRating(rating=1301.0, rank=12)

    export(client, organizer)

    fencers = sheets.worksheets["Fencers"]
    jan = grid_row(fencers, "Jan Novák")
    assert jan[0] == "R-01"  # Reg. untouched
    assert jan[3] == "Praha Sword Society"  # non-blank cell not clobbered
    ls_jan = grid_row(sheets.worksheets["LS"], "Jan Novák")
    assert ls_jan[0] == "7"  # No. untouched
    assert ls_jan[5:7] == ["1301.0", "12"]  # ratings always refresh


def test_deleted_rows_excluded_from_every_worksheet(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    wire(sheets, RatedIndex([]))
    export(client, organizer)
    assert len(sheets.worksheets["SA"]) == 3

    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    target = next(r for r in rows if r["name"] == "Alexander Bryzgalov")
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "export", "kind": "row_delete", "target": target["id"],
              "payload": {}},
        headers=organizer,
    )
    export(client, organizer)

    for grid in sheets.worksheets.values():
        assert all(row[1] != "Alexander Bryzgalov" for row in grid[1:])


def test_export_requires_configuration(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    app.dependency_overrides[get_sheets_client_factory] = lambda: None
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 503

    app.dependency_overrides[get_sheets_client_factory] = lambda: (lambda t: None)
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 422
