"""Google Sheets export: v1 format, preserve/refresh semantics, export scope."""

import io

from app.exportsummary import ITEM, QUEUE, SummaryLine
from app.hr_sync import get_hr_fetcher
from app.importer import get_import_parser
from app.main import app
from app.sheets_export import (
    DISCIPLINE_COLUMNS,
    SUMMARY_COLUMNS,
    get_sheets_client_factory,
    header_for,
    summary_label,
    typed_grid,
)
from tests.conftest import publish
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

    def fighters_page(self) -> str:
        raise AssertionError("index refresh not expected here")

    def fighter_page(self, hr_id: int) -> str | None:
        return self.pages.get(hr_id)


def snapshot(client, organizer):
    response = client.post("/api/tournaments/cup/ratings/snapshot", headers=organizer)
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
            json={"slug": code, "weapon": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )
    client.patch(
        "/api/tournaments/cup",
        json={
            "output_sheet_url": "https://sheets.example/cup",
            "city": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
        },
        headers=organizer,
    )
    publish(client, organizer, "cup")
    # one in-app registration with an HR-bound account
    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    binding = client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer)
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
    app.dependency_overrides[get_sheets_client_factory] = lambda: lambda tournament: sheets
    if fetcher is not None:
        app.dependency_overrides[get_hr_fetcher] = lambda: fetcher


def export(client, organizer):
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()


def grid_row(grid, name):
    """The row naming `name`, found by the name column wherever it stands."""
    at = next(i for i, label in enumerate(grid[0]) if label in ("Jméno", "Name"))
    return next(r for r in grid[1:] if r[at] == name)


def test_export_writes_the_export_tables(client, auth_headers):
    """One worksheet per export table, each carrying its table's columns —
    Czech, because the organizer's own language is what the sheet is written
    in unless they ask for English."""
    organizer = auth_headers(language="cs")
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    wire(sheets, fetcher)
    snapshot(client, organizer)

    body = export(client, organizer)
    assert body["worksheets"] == ["Fencers", "LS", "SA", "Summary"]

    fencers = sheets.worksheets["Fencers"]
    assert fencers[0] == [
        "#",
        "Jméno",
        "Nár.",
        "Klub",
        "HR_ID",
        "Disciplíny",
        "Zaplaceno",
    ]
    jan = grid_row(fencers, "Jan Novák")
    assert jan[4] == 10234  # numbers go to the sheet as numbers
    assert jan[5] == "LS"
    assert jan[6] == "Ne"  # payment state in the Paid column
    # every worksheet opens with its rows numbered as they stand
    assert [row[0] for row in fencers[1:]] == list(range(1, len(fencers)))

    ls = sheets.worksheets["LS"]
    assert ls[0] == ["#", "Jméno", "Nár.", "Klub", "HR_ID", "HRating", "HRank", "Zaplaceno"]
    assert grid_row(ls, "Jan Novák")[5:7] == [1250.5, 17]
    # imported SA fencers land on the SA tab only
    assert len(sheets.worksheets["SA"]) == 3
    assert all(row[1] != "Jan Novák" for row in sheets.worksheets["SA"][1:])


def test_an_english_export_carries_english_headers(client, auth_headers):
    organizer = auth_headers(language="cs")
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    wire(sheets)

    response = client.post(
        "/api/tournaments/cup/export/sheet", params={"english": True}, headers=organizer
    )
    assert response.status_code == 200, response.text

    fencers = sheets.worksheets["Fencers"]
    assert fencers[0] == ["#", "Name", "Nat.", "Club", "HR_ID", "Disciplines", "Paid"]
    assert grid_row(fencers, "Jan Novák")[6] == "No"


def test_an_item_category_gets_a_worksheet_and_an_empty_one_does_not(client, auth_headers):
    organizer = auth_headers(language="cs")
    setup(client, auth_headers, organizer)
    shirt = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "t-shirt", "category": "merch", "price": 300, "max_qty": 5},
        headers=organizer,
    ).json()
    buyer = auth_headers(email="buyer@example.com", name="Buyer One")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "extras": [{"extra_item_id": shirt["id"], "qty": 2}]},
        headers=buyer,
    )
    sheets = InMemorySheets()
    wire(sheets)

    body = export(client, organizer)
    assert "Merch" in body["worksheets"]
    assert "Rentals" not in body["worksheets"]  # the tournament sells none

    merch = sheets.worksheets["Merch"]
    assert merch[0] == ["#", "Jméno", "Nár.", "Klub", "Položky", "Zaplaceno"]
    # the item worksheet carries no hand-numbering column, only the position
    assert [row[:2] for row in merch[1:]] == [[1, "Buyer One"]]
    assert merch[1][4] == "t-shirt x2"


def test_a_corrected_rating_is_what_the_sheet_carries(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    wire(sheets, fetcher)
    snapshot(client, organizer)
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    target = next(r for r in rows if r["name"] == "Jan Novák")["id"]
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "export",
            "kind": "rating_override",
            "target": target,
            "payload": {"discipline": "LS", "rating": 1555.0},
        },
        headers=organizer,
    )

    export(client, organizer)
    assert grid_row(sheets.worksheets["LS"], "Jan Novák")[5] == 1555.0

    # written afresh every time rather than preserved as a stale cell
    export(client, organizer)
    assert grid_row(sheets.worksheets["LS"], "Jan Novák")[5] == 1555.0


def rebind(client, organizer, name, hr_id):
    """The organizer resolves a row's HR match to another profile."""
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    target = next(r for r in rows if r["name"] == name)["id"]
    response = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "matching",
            "kind": "match_resolution",
            "target": target,
            "payload": {"field": "hr_id", "value": hr_id},
        },
        headers=organizer,
    )
    assert response.status_code in (200, 201), response.text
    return target


def test_a_rebound_row_carries_its_new_profiles_rating(client, auth_headers):
    """A rule that binds a row to another HR profile brings that profile's
    rating along, in the console and in the sheet — the base row was seeded
    for the profile it was built with, and that one is not the fencer."""
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    fetcher.pages[20468] = fighter_page([("Mixed & Men's Steel Longsword", 1600.0, 5)])
    wire(sheets, fetcher)
    rebind(client, organizer, "Jan Novák", 20468)
    snapshot(client, organizer)

    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    jan = next(r for r in rows if r["name"] == "Jan Novák")
    assert jan["ratings"] == {"LS": 1600.0}
    assert jan["ranks"] == {"LS": 5}

    export(client, organizer)
    assert grid_row(sheets.worksheets["LS"], "Jan Novák")[5:7] == [1600.0, 5]


def test_a_correction_outlives_a_rebinding(client, auth_headers):
    """A rating the organizer typed belongs to the row, not to the profile it
    was bound to when they typed it."""
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    fetcher.pages[20468] = fighter_page([("Mixed & Men's Steel Longsword", 1600.0, 5)])
    wire(sheets, fetcher)
    snapshot(client, organizer)
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    target = next(r for r in rows if r["name"] == "Jan Novák")["id"]
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "export",
            "kind": "rating_override",
            "target": target,
            "payload": {"discipline": "LS", "rating": 1555.0},
        },
        headers=organizer,
    )
    rebind(client, organizer, "Jan Novák", 20468)
    snapshot(client, organizer)

    export(client, organizer)
    # the typed rating stands; the rank is the new profile's
    assert grid_row(sheets.worksheets["LS"], "Jan Novák")[5:7] == [1555.0, 5]


def test_an_old_format_sheet_keeps_what_remains(client, auth_headers):
    """A spreadsheet written in an older format, re-exported: the columns that
    remain keep their contents whatever language the header was in, the ones
    the format drops — the hand-numbering column among them — are gone, and
    the ones it adds are filled."""
    organizer = auth_headers(language="cs")
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    wire(sheets)
    sheets.worksheets["Fencers"] = [
        ["Reg.", "Name", "Nat.", "Club", "HR_ID", "Disciplines", "Paid", "Afterparty", "Notes"],
        ["R-01", "Jan Novák", "CZ", "Praha Sword Society", "10234", "LS", "No", "Yes", "old note"],
    ]

    export(client, organizer)

    fencers = sheets.worksheets["Fencers"]
    assert fencers[0] == ["#", "Jméno", "Nár.", "Klub", "HR_ID", "Disciplíny", "Zaplaceno"]
    jan = grid_row(fencers, "Jan Novák")
    assert jan[3] == "Praha Sword Society"  # a non-blank cell is not clobbered
    assert len(jan) == 7  # Reg., Afterparty and Notes are gone; the position arrived
    assert jan[0] == 1


def test_reexport_preserves_manual_work_and_refreshes_ratings(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    sheets = InMemorySheets()
    fetcher = FakeHRFetcher()
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1250.5, 17)])
    wire(sheets, fetcher)
    snapshot(client, organizer)
    export(client, organizer)

    # downstream staff fix a club by hand; the rating moves on hemaratings and
    # a fresh snapshot is taken
    jan = grid_row(sheets.worksheets["Fencers"], "Jan Novák")
    jan[3] = "Praha Sword Society"
    fetcher.pages[10234] = fighter_page([("Mixed & Men's Steel Longsword", 1301.0, 12)])
    snapshot(client, organizer)

    export(client, organizer)

    jan = grid_row(sheets.worksheets["Fencers"], "Jan Novák")
    assert jan[3] == "Praha Sword Society"  # non-blank cell not clobbered
    ls_jan = grid_row(sheets.worksheets["LS"], "Jan Novák")
    assert ls_jan[5:7] == [1301.0, 12]  # ratings always refresh


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
        json={"phase": "export", "kind": "row_delete", "target": target["id"], "payload": {}},
        headers=organizer,
    )
    export(client, organizer)

    for grid in sheets.worksheets.values():
        assert all(row[1] != "Alexander Bryzgalov" for row in grid[1:])
    # the numbering closes over the gap rather than keeping the old numbers
    assert [row[0] for row in sheets.worksheets["SA"][1:]] == [1]


def test_export_requires_configuration(client, auth_headers):
    organizer = auth_headers()
    setup(client, auth_headers, organizer)
    app.dependency_overrides[get_sheets_client_factory] = lambda: None
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 503

    app.dependency_overrides[get_sheets_client_factory] = lambda: lambda t: None
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 9.8 Tiers and a custom weapon (design discipline-identity D5, D4)
# ---------------------------------------------------------------------------


def test_two_tiers_produce_two_worksheets(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "tiers", "display_name": "Tiers", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/tiers/disciplines",
        json={"slug": "LS-A", "weapon": "LS", "name": "Longsword Top", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/tiers/disciplines",
        json={
            "slug": "LS-B",
            "weapon": "LS",
            "name": "Longsword Open",
            "capacity": 10,
            "fee": 1000,
        },
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/tiers",
        json={
            "output_sheet_url": "https://sheets.example/tiers",
            "city": "Brno",
            "organizers": [{"name": "Org", "link": None}],
        },
        headers=organizer,
    )
    publish(client, organizer, "tiers")

    top = auth_headers(email="top@example.com", name="Top Fencer")
    client.post("/api/tournaments/tiers/register", json={"disciplines": ["LS-A"]}, headers=top)
    openb = auth_headers(email="open@example.com", name="Open Fencer")
    client.post("/api/tournaments/tiers/register", json={"disciplines": ["LS-B"]}, headers=openb)

    sheets = InMemorySheets()
    app.dependency_overrides[get_sheets_client_factory] = lambda: lambda t: sheets
    response = client.post("/api/tournaments/tiers/export/sheet", headers=organizer)
    assert response.status_code == 200, response.text
    assert set(response.json()["worksheets"]) == {"Fencers", "LS-A", "LS-B", "Summary"}
    assert grid_row(sheets.worksheets["LS-A"], "Top Fencer")
    assert grid_row(sheets.worksheets["LS-B"], "Open Fencer")
    assert all(row[1] != "Open Fencer" for row in sheets.worksheets["LS-A"][1:])
    # both tiers carry the same slug in the Fencers worksheet's Disciplines column
    fencers = sheets.worksheets["Fencers"]
    assert grid_row(fencers, "Top Fencer")[5] == "LS-A"
    assert grid_row(fencers, "Open Fencer")[5] == "LS-B"


def test_custom_weapon_worksheet_has_empty_rating_columns(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "messer", "display_name": "Messer Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/messer/disciplines",
        json={"weapon": "Messer", "name": "Messer Open", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/messer",
        json={
            "output_sheet_url": "https://sheets.example/messer",
            "city": "Brno",
            "organizers": [{"name": "Org", "link": None}],
        },
        headers=organizer,
    )
    publish(client, organizer, "messer")
    fencer = auth_headers(email="messer@example.com", name="Messer Fencer")
    client.post(
        "/api/tournaments/messer/register", json={"disciplines": ["Messer"]}, headers=fencer
    )

    sheets = InMemorySheets()
    app.dependency_overrides[get_sheets_client_factory] = lambda: lambda t: sheets
    response = client.post("/api/tournaments/messer/export/sheet", headers=organizer)
    assert response.status_code == 200, response.text
    row = grid_row(sheets.worksheets["Messer"], "Messer Fencer")
    assert row[5:7] == ["", ""]  # HRating, HRank: no taxonomy counterpart


def test_only_numeric_columns_are_written_as_numbers():
    """A club named by a year stays text; a blank rating stays blank; a word
    downstream staff wrote into a numeric column stays the word."""
    grid = [
        ["#", "Jméno", "Nár.", "Klub", "HR_ID", "HRating", "HRank", "Zaplaceno"],
        ["1", "Jan", "CZ", "1996", "10234", "1250.5", "17", "Ne"],
        ["2", "Eva", "CZ", "", "", "", "n/a", "Ano"],
    ]
    assert typed_grid(grid, DISCIPLINE_COLUMNS) == [
        grid[0],
        [1, "Jan", "CZ", "1996", 10234, 1250.5, 17, "Ne"],
        [2, "Eva", "CZ", "", "", "", "n/a", "Ano"],
    ]


def test_the_summary_worksheet_counts_and_is_rewritten_whole(client, auth_headers):
    organizer = auth_headers(language="cs")
    setup(client, auth_headers, organizer)
    shirt = client.post(
        "/api/tournaments/cup/extra-items",
        json={
            "name": "Triko",
            "category": "merch",
            "price": 300,
            "max_qty": 5,
            "option_label": "size",
            "option_choices": ["L", "XL"],
        },
        headers=organizer,
    ).json()
    buyer = auth_headers(email="buyer@example.com", name="Buyer One")
    client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": ["LS"],
            "extras": [{"extra_item_id": shirt["id"], "qty": 2, "option_value": "XL"}],
        },
        headers=buyer,
    )
    sheets = InMemorySheets()
    wire(sheets)

    export(client, organizer)
    summary = sheets.worksheets["Summary"]
    assert summary[0] == ["Položka", "Zaplaceno", "Nezaplaceno"]
    assert ["Triko – L", 0, 0] in summary
    assert ["Triko – XL", 0, 2] in summary  # pieces, as numbers

    # staff wrote into it; the next export states the counts and nothing else
    summary.append(["poznámka", "", ""])
    export(client, organizer)
    assert ["poznámka", "", ""] not in sheets.worksheets["Summary"]


def test_an_english_summary_names_the_words_squire_adds_in_english():
    """The organizer's names stay as written; the queue and the unanswered
    option are Squire's words and follow the export's language."""
    queue = SummaryLine(QUEUE, "", "Dlouhý meč", 2, 12)
    missing = SummaryLine(ITEM, "merch", "Triko", 0, 1, missing=True)
    sized = SummaryLine(ITEM, "merch", "Triko", 3, 0, option="XL")

    assert [summary_label(line, "en") for line in (queue, missing, sized)] == [
        "Dlouhý meč (queue)",
        "Triko – not given",
        "Triko – XL",
    ]
    assert summary_label(queue, "cs") == "Dlouhý meč (fronta)"
    assert header_for(SUMMARY_COLUMNS, "en") == ["Item", "Paid", "Unpaid"]
