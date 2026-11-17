"""Results and the public floor (specs floor-results, floor-public), through
the API."""

from tests.floor.test_floor_bracket import confirmed, open_bouts, record, view
from tests.floor.test_floor_plan import choose, variants
from tests.floor.test_floor_pools import drawn, pools_of
from tests.floor.test_floor_setup import BASE, ok

PUBLIC = "/api/tournaments/cup/floor/public"


def finished(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)
    for _ in range(20):
        pending = open_bouts(view(client, organizer, ls))
        if not pending:
            break
        ok(record(client, organizer, ls, pending[0]))
    return organizer, ls


def test_the_standing_follows_the_bracket_then_the_pools(client, auth_headers):
    organizer, ls = finished(client, auth_headers)

    (row,) = [
        r
        for r in client.get(f"{BASE}/results", headers=organizer).json()
        if r["discipline_id"] == ls
    ]

    places = [r["place"] for r in row["standing"]]
    assert places[:4] == [1, 2, 3, 3]
    assert places == sorted(places) and len(places) == 10
    assert all(r["name"] for r in row["standing"])


def test_bouts_are_exported(client, auth_headers):
    organizer, ls = finished(client, auth_headers)

    response = client.get(f"{BASE}/results/{ls}/csv", headers=organizer)

    assert response.status_code == 200, response.text
    lines = response.text.splitlines()
    assert lines[0] == "place,name,club,nationality"
    assert any(line.startswith("pool 1,") for line in lines)
    assert any(line.startswith("round 4,") for line in lines)


def test_unpublished_results_are_not_public_and_publishing_shows_them(client, auth_headers):
    organizer, ls = finished(client, auth_headers)

    before = client.get(f"{PUBLIC}/results").json()
    today = {
        r["discipline_id"]: r for r in client.get(f"{BASE}/today", headers=organizer).json()["rows"]
    }
    ok(client.post(f"{BASE}/results/{ls}/publish", headers=organizer))
    after = client.get(f"{PUBLIC}/results").json()
    summary = client.get(PUBLIC).json()
    ok(client.delete(f"{BASE}/results/{ls}/publish", headers=organizer))

    assert before == []
    assert today[ls]["steps"]["results"] == "waiting"
    assert [d["slug"] for d in after] == ["LS"]
    assert "key" not in after[0]["standing"][0]
    assert summary["results"] is True
    assert client.get(f"{PUBLIC}/results").json() == []


def test_publishing_waits_for_the_bracket(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)

    refused = client.post(f"{BASE}/results/{ls}/publish", headers=organizer)

    assert refused.status_code == 409 and refused.json()["detail"] == "bracket_open"


def test_the_working_plan_stays_private(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    published = client.get(f"{PUBLIC}/program").json()
    # a new working version that differs is chosen but not published
    choose(client, organizer, variants(client, organizer)["variants"][-1]["key"])

    again = client.get(f"{PUBLIC}/program").json()

    assert published == again
    assert published and published[0]["slug"] == "LS"
    assert client.get(PUBLIC).json()["program"] is True


def test_a_fencer_sees_their_own_itinerary_only(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    login = client.post(
        "/api/auth/login", json={"email": "f0@example.com", "password": "correct-horse"}
    )
    assert login.status_code == 200, login.text
    fencer = {"Authorization": f"Bearer {login.json()['token']}"}
    stranger = auth_headers(email="z@example.com", name="Zdeněk")

    mine = client.get(f"{PUBLIC}/itinerary", headers=fencer).json()
    theirs = client.get(f"{PUBLIC}/itinerary", headers=stranger).json()
    anonymous = client.get(f"{PUBLIC}/itinerary").json()

    assert [(i["discipline"], i["kind"]) for i in mine] == [("Longsword Open", "pool")]
    assert mine[0]["number"] in {
        p["number"] for p in pools_of(client, organizer, ls)["draw"]["pools"]
    }
    assert theirs == [] and anonymous == []


def test_an_unpublished_tournament_answers_404(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )

    assert client.get(PUBLIC).status_code == 404
