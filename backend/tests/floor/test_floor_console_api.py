"""The floor console's server side (spec floor-console): who may open it, what
has no floor, and the summary its tab band reads."""

from tests.floor.test_floor_setup import BASE, discipline_ids, fmt, ok, put
from tests.test_entrants import setup_tournament


def test_a_stranger_is_refused(client, auth_headers):
    setup_tournament(client, auth_headers())
    stranger = auth_headers(email="z@example.com", name="Zdeněk")

    assert client.get(f"{BASE}/setup", headers=stranger).status_code == 403
    assert client.get(f"{BASE}/summary", headers=stranger).status_code == 403
    assert put(client, stranger, "params", {}).status_code == 403


def test_an_event_has_no_floor(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )

    response = client.get(f"{BASE}/summary", headers=organizer)

    assert response.status_code == 404
    assert response.json()["detail"] == "floor_not_found"


def test_a_draft_is_read_but_not_written(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )

    assert client.get(f"{BASE}/setup", headers=organizer).status_code == 200
    assert put(client, organizer, "params", {}).status_code == 409


def test_the_setup_badge_names_what_waits_until_nothing_does(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    summary = client.get(f"{BASE}/summary", headers=organizer).json()
    assert summary["plan_published"] is False
    assert summary["badges"] == {
        "setup": True,
        "data": False,
        "plan": False,
        "today": False,
        "checkin": False,
        "pools": False,
        "bracket": False,
        "results": False,
    }
    assert summary["setup_missing"] == [
        "days",
        "pistes",
        f"format:{ids['LS']}",
        f"format:{ids['SB']}",
    ]

    ok(put(client, organizer, "pistes", [{"name": "1", "days": ["2099-12-05"]}]))
    ok(put(client, organizer, "formats", [fmt(ids["LS"]), fmt(ids["SB"])]))

    summary = client.get(f"{BASE}/summary", headers=organizer).json()
    assert summary["setup_missing"] == []
    assert summary["badges"]["setup"] is False
