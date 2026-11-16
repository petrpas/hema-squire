"""A team discipline's worksheet (spec data-export, A team discipline's
worksheet is flat, and Repeat-export preservation semantics): one row per
fighter with the team's number, name and paid on every row, kept in place
across re-exports by team and fighter, and an old-shape worksheet rewritten
once."""

from collections.abc import Iterator

import pytest

from app.main import app
from app.sheets_export import get_sheets_client_factory
from tests.conftest import publish
from tests.test_sheets_export import InMemorySheets


@pytest.fixture
def sheets() -> Iterator[InMemorySheets]:
    sheets = InMemorySheets()
    app.dependency_overrides[get_sheets_client_factory] = lambda: lambda tournament: sheets
    yield sheets
    app.dependency_overrides.pop(get_sheets_client_factory, None)


def make_cup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "SA",
            "weapon": "SA",
            "capacity": 5,
            "fee": 3000,
            "kind": "team",
            "team_min": 1,
            "team_max": 4,
        },
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


def enter(client, headers, team, members):
    response = client.post(
        "/api/tournaments/cup/register",
        json={"teams": [{"slug": "SA", "name": team}]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    own = client.get("/api/tournaments/cup/my-registration", headers=headers).json()["teams"]
    team_id = next(t["id"] for t in own if t["name"] == team)
    if members:
        response = client.put(
            f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
            json={"members": members},
            headers=headers,
        )
        assert response.status_code == 200, response.text


def export(client, organizer):
    response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert response.status_code == 200, response.text


def rows(sheets):
    """(position, team, name, club, paid) of every row, as written."""
    header, *body = sheets.worksheets["SA"]
    at = {label: index for index, label in enumerate(header)}
    return [
        (r[at["Poř."]], r[at["Tým"]], r[at["Jméno"]], r[at["Klub"]], r[at["Zaplaceno"]])
        for r in body
    ]


def two_teams(client, auth_headers):
    organizer = auth_headers()
    make_cup(client, organizer)
    enter(
        client,
        auth_headers(email="a@example.com", name="Ann A"),
        "Wolves",
        [
            {"name": "Ann A", "hr_id": 7, "club": "Klub A"},
            {"name": "Bob B", "club": "Klub A"},
        ],
    )
    enter(
        client,
        auth_headers(email="c@example.com", name="Cid C"),
        "Bears",
        [
            # the same fighter on a second team, by their profile
            {"name": "Ann A.", "hr_id": 7, "club": "Klub A"},
            {"name": "Cid C", "club": "Klub C"},
        ],
    )
    return organizer


def test_team_cells_stand_on_every_row(client, auth_headers, sheets):
    organizer = two_teams(client, auth_headers)
    export(client, organizer)

    assert rows(sheets) == [
        (1, "Wolves", "Ann A", "Klub A", "Ne"),
        (1, "Wolves", "Bob B", "Klub A", "Ne"),
        (2, "Bears", "Ann A.", "Klub A", "Ne"),
        (2, "Bears", "Cid C", "Klub C", "Ne"),
    ]
    header = sheets.worksheets["SA"][0]
    # the console's facts are not the sheet's
    assert all("přihlásil" not in str(cell) for row in sheets.worksheets["SA"] for cell in row)
    assert header[:3] == ["Poř.", "Tým", "Jméno"]


def test_a_reexport_keeps_rows_and_hand_written_cells(client, auth_headers, sheets):
    organizer = two_teams(client, auth_headers)
    export(client, organizer)
    grid = sheets.worksheets["SA"]
    club = grid[0].index("Klub")
    # staff note on Bob's row, and a fighter on two teams is two rows
    grid[2][club] = "noted by hand"

    export(client, organizer)
    export(client, organizer)

    assert [(r[1], r[2]) for r in rows(sheets)] == [
        ("Wolves", "Ann A"),
        ("Wolves", "Bob B"),
        ("Bears", "Ann A."),
        ("Bears", "Cid C"),
    ]
    assert rows(sheets)[1][3] == "noted by hand"


def test_an_empty_team_is_one_row(client, auth_headers, sheets):
    organizer = auth_headers()
    make_cup(client, organizer)
    enter(client, auth_headers(email="a@example.com", name="Ann A"), "Wolves", [])

    export(client, organizer)
    export(client, organizer)

    assert rows(sheets) == [(1, "Wolves", "", "", "Ne")]


def test_an_old_shape_worksheet_is_rewritten_once(client, auth_headers, sheets):
    organizer = two_teams(client, auth_headers)
    sheets.worksheets["SA"] = [
        ["Poř.", "Jméno", "Nár.", "Klub", "HR_ID", "HRating", "HRank", "Zaplaceno"],
        ["1", "Wolves · přihlásil Ann A · 2/1–4 na soupisce", "", "", "", "", "", "Ne"],
        ["2", "Ann A", "", "a note", "7", "", "", ""],
    ]

    export(client, organizer)

    assert [r[2] for r in rows(sheets)] == ["Ann A", "Bob B", "Ann A.", "Cid C"]
    assert all("a note" not in str(cell) for row in sheets.worksheets["SA"] for cell in row)
