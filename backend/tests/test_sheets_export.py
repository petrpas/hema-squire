"""Google Sheets export: v1 format, preserve/refresh semantics, export scope."""

import io

from app.hr_sync import get_hr_fetcher
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


def fighter_page(rows: list[tuple[str, float, int]]) -> str:
    """A minimal hemaratings fighter-details page with the given category rows."""
    body = "".join(
        f"<tr><td>{category}</td><td>2026-05-01</td><td>#{rank}</td><td>{rating}</td>"
        f"<td>#{rank}</td><td>{rating}</td></tr>"
        for category, rating, rank in rows
    )
    return f"<h3>Ratings</h3><table><tbody>{body}</tbody></table>"


class FakeHRFetcher:
    """Serves per-fighter rating pages; mutable so tests can change ratings."""

    def __init__(self):
        self.pages: dict[int, str] = {}

    def fighters_page(self):
        raise AssertionError("index refresh not expected here")

    def fighter_page(self, hr_id):
        return self.pages.get(hr_id)


def snapshot(client, organizer):
    response = client.post(
        "/api/tournaments/cup/ratings/snapshot", headers=organizer
    )
    assert response.status_code == 200, response.text
    return response.json()


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
        json={
            "output_sheet_url": "https://sheets.example/cup",
            "location": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
        },
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


def wire(sheets, fetcher=None):
    app.dependency_overrides[get_sheets_client_factory] = lambda: (
        lambda tournament: sheets
    )
    if fetcher is not None:
        app.dependency_overrides[get_hr_fetcher] = lambda: fetcher


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
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    wire(sheets, fetcher)
    snapshot(client, organizer)

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
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    wire(sheets, fetcher)
    snapshot(client, organizer)
    export(client, organizer)

    # downstream staff number rows and fix a club by hand; the rating moves
    # on hemaratings and a fresh snapshot is taken
    fencers = sheets.worksheets["Fencers"]
    jan = grid_row(fencers, "Jan Novák")
    jan[0] = "R-01"
    jan[3] = "Praha Sword Society"
    ls = sheets.worksheets["LS"]
    grid_row(ls, "Jan Novák")[0] = "7"
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1301.0, 12)])
    snapshot(client, organizer)

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
    wire(sheets)  # no snapshot taken: HRating/HRank stay blank
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
