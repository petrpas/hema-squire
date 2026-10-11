"""A tournament's short code (spec tournament-admin, Tournament short code):
one to three characters, trimmed and composed, cleared by null, and carried
to the public list for the card's plate."""

import pytest

from tests.conftest import publish


@pytest.fixture
def cup(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2030-01-01"},
        headers=organizer,
    )
    return organizer


def patch(client, organizer, value):
    return client.patch("/api/tournaments/cup", json={"short_code": value}, headers=organizer)


def test_a_set_code_is_stored_trimmed(client, cup):
    assert patch(client, cup, "  PDM ").status_code == 200
    assert client.get("/api/tournaments/cup", headers=cup).json()["short_code"] == "PDM"


def test_a_composed_letter_counts_once(client, cup):
    # B, S and a combining caron: three code points typed, two characters read
    assert patch(client, cup, "BŠ").status_code == 200
    assert client.get("/api/tournaments/cup", headers=cup).json()["short_code"] == "BŠ"


def test_longer_than_three_is_refused(client, cup):
    response = patch(client, cup, "PRAHA")
    assert response.status_code == 422
    assert client.get("/api/tournaments/cup", headers=cup).json()["short_code"] is None


def test_null_clears_it(client, cup):
    patch(client, cup, "PDM")
    assert patch(client, cup, None).status_code == 200
    assert client.get("/api/tournaments/cup", headers=cup).json()["short_code"] is None


def test_the_list_carries_it(client, cup):
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}], "short_code": "CU"},
        headers=cup,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 4, "fee": 500},
        headers=cup,
    )
    publish(client, cup, "cup")
    listed = client.get("/api/tournaments/open").json()
    assert next(t for t in listed if t["slug"] == "cup")["short_code"] == "CU"
