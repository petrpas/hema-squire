"""Order of the fencer list: both populations interleaved by registration
moment, rows stating none last (spec etl-console, Order of the fencer list)."""

import io

from app.importer import ParsedFencer, get_import_parser
from app.main import app
from tests.conftest import publish

CSV = (
    "Name,When\n"
    "Early Import,2026-04-01T14:15:27\n"
    "Late Import,2027-01-01T09:00:00\n"
    "Timeless Import,\n"
    "Unreadable Import,sometime in spring\n"
)


class TimeParser:
    """Passes each row's stated time through untouched, so the test decides
    what the parser produced — including what it could not read."""

    def parse(self, rows, disciplines, rentals):
        return [
            ParsedFencer(
                registration_time=raw["When"],
                name=raw["Name"],
                nationality="CZ",
                disciplines=["LS"],
            )
            for raw in rows
        ]


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def names_in_order(client, organizer) -> list[str]:
    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return [row["name"] for row in sheet["rows"]]


def test_populations_interleave_and_timeless_rows_sort_last(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = auth_headers(email="live@example.com", name="Live Registration")
    assert (
        client.post(
            "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
        ).status_code
        == 201
    )

    app.dependency_overrides[get_import_parser] = lambda: TimeParser()
    try:
        response = client.post(
            "/api/tournaments/cup/import",
            files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
            headers=organizer,
        )
        assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.pop(get_import_parser, None)

    # the in-app registration is stamped now (2026-08-28 onwards), so it falls
    # between the two imported rows that state a moment
    assert names_in_order(client, organizer) == [
        "Early Import",
        "Live Registration",
        "Late Import",
        # neither of these states a moment the table can read, so both follow
        # every row that does, in the order of the file they came from
        "Timeless Import",
        "Unreadable Import",
    ]


def test_numbers_stand_out_of_sequence_where_an_import_is_backdated(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = auth_headers(email="live@example.com", name="Live Registration")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer)

    app.dependency_overrides[get_import_parser] = lambda: TimeParser()
    try:
        client.post(
            "/api/tournaments/cup/import",
            files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
            headers=organizer,
        )
    finally:
        app.dependency_overrides.pop(get_import_parser, None)

    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    by_name = {row["name"]: row["number"] for row in sheet["rows"]}
    # the registration arrived first and holds number 1; the backdated import
    # displays above it while carrying a higher number
    assert by_name["Live Registration"] == 1
    assert by_name["Early Import"] == 2
    assert [row["number"] for row in sheet["rows"]][:2] == [2, 1]
