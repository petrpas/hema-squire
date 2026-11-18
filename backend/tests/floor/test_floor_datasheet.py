"""The Data sheet through the API (spec floor-data, The sheet is the floor's to
correct; The ratings are refreshed for one discipline; A closed discipline's
sheet is the snapshot)."""

from sqlalchemy import func, select

from app import hr_sync
from app.floor.models import FloorSnapshotEntrant
from app.hr_sync import get_hr_fetcher
from app.main import app
from app.models import HRRatingSnapshot, Registration
from tests.floor.test_floor_checkin import arrive, closed_sabre, desk, person, team_day
from tests.floor.test_floor_roster import db_session, set_hr_id, tournament
from tests.floor.test_floor_setup import BASE, discipline_ids
from tests.test_entrants import register, setup_tournament
from tests.test_sheets_export import FakeHRFetcher, fighter_page


def sheet(client, headers, discipline_id: int) -> dict:
    response = client.get(f"{BASE}/sheet/{discipline_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def row(body: dict, name: str) -> dict:
    return next(r for r in body["rows"] if r["name"] == name)


def cell(client, headers, subject: str, field: str, value):
    return client.put(
        f"{BASE}/sheet/cells",
        json={"subject": subject, "field": field, "value": value},
        headers=headers,
    )


def two_disciplines(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, sabre_capacity=5)
    register(client, auth_headers(email="a@example.com", name="Adéla"), ("LS", "SB"))
    register(client, auth_headers(email="b@example.com", name="Boris"), ("SB",))
    return organizer, discipline_ids(client, organizer)


def test_the_sheet_states_the_office_columns_in_seeding_order(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    adela = row(sheet(client, organizer, ids["SB"]), "Adéla")
    cell(client, organizer, adela["entry_key"], "rating", 1500)
    boris = row(sheet(client, organizer, ids["SB"]), "Boris")
    cell(client, organizer, boris["entry_key"], "rating", 1700)

    body = sheet(client, organizer, ids["SB"])

    assert [r["name"] for r in body["rows"]] == ["Boris", "Adéla"]
    assert body["count"] == 2
    assert set(body["rows"][0]) >= {
        "name",
        "club",
        "nationality",
        "hr_id",
        "rating",
        "rank",
        "paid",
    }
    assert body["rows"][0]["edited"] == ["rating"]


def test_a_club_is_corrected_once(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    adela = row(sheet(client, organizer, ids["LS"]), "Adéla")

    assert cell(client, organizer, adela["person"], "club", "Klub Y").status_code == 204

    assert row(sheet(client, organizer, ids["SB"]), "Adéla")["club"] == "Klub Y"
    assert row(sheet(client, organizer, ids["LS"]), "Adéla")["edited"] == ["club"]
    assert person(desk(client, organizer), "Adéla")["club"] == "Klub Y"
    office = client.get(
        "/api/tournaments/cup/export/table?kind=discipline&key=LS", headers=organizer
    ).json()
    assert [r["club"] for r in office["rows"]] != ["Klub Y"]
    # an emptied cell returns to what lies beneath it
    cell(client, organizer, adela["person"], "club", "")
    assert row(sheet(client, organizer, ids["LS"]), "Adéla")["edited"] == []


def test_a_walk_in(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    registrations = db_session().scalar(select(func.count()).select_from(Registration))

    added = client.post(
        f"{BASE}/sheet/{ids['SB']}/entries",
        json={"person": {"name": "Jana Nováková", "club": "Brno"}},
        headers=organizer,
    )

    assert added.status_code == 201, added.text
    body = sheet(client, organizer, ids["SB"])
    jana = row(body, "Jana Nováková")
    assert (jana["added"], jana["local"], jana["paid"], body["count"]) == (True, True, False, 3)
    sabre = next(d for d in desk(client, organizer)["disciplines"] if d["slug"] == "SB")
    assert sabre["entered"] == 3
    assert db_session().scalar(select(func.count()).select_from(Registration)) == registrations

    # removing an addition deletes it
    removed = client.delete(f"{BASE}/sheet/{ids['SB']}/entries/{jana['person']}", headers=organizer)
    assert removed.status_code == 204, removed.text
    assert sheet(client, organizer, ids["SB"])["count"] == 2


def test_a_nationality_is_drawn_as_the_office_draws_it(client, auth_headers):
    # a HEMA Ratings profile names the country; the sheet, like the Export,
    # states its code, and keeps text that names no country as written
    organizer, ids = two_disciplines(client, auth_headers)
    client.post(
        f"{BASE}/sheet/{ids['SB']}/entries",
        json={"person": {"name": "Jana", "nationality": "Czech Republic"}},
        headers=organizer,
    )
    jana = row(sheet(client, organizer, ids["SB"]), "Jana")
    assert jana["nationality"] == "CZ"

    cell(client, organizer, jana["person"], "nationality", "Slovakia")
    assert row(sheet(client, organizer, ids["SB"]), "Jana")["nationality"] == "SK"
    cell(client, organizer, jana["person"], "nationality", "Ruritania")
    assert row(sheet(client, organizer, ids["SB"]), "Jana")["nationality"] == "Ruritania"


def test_a_person_already_on_the_floor_enters_one_more_discipline(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    boris = row(sheet(client, organizer, ids["SB"]), "Boris")

    added = client.post(
        f"{BASE}/sheet/{ids['LS']}/entries", json={"person_key": boris["person"]}, headers=organizer
    )
    again = client.post(
        f"{BASE}/sheet/{ids['LS']}/entries", json={"person_key": boris["person"]}, headers=organizer
    )

    assert added.status_code == 201, added.text
    assert again.status_code == 409
    assert row(sheet(client, organizer, ids["LS"]), "Boris")["added"] is True


def test_a_no_show_removed_on_data_appears_withdrawn_at_the_desk(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    boris = row(sheet(client, organizer, ids["SB"]), "Boris")

    withdrawn = client.post(
        f"{BASE}/checkin/withdrawals", json={"entry_key": boris["entry_key"]}, headers=organizer
    )

    assert withdrawn.status_code == 204, withdrawn.text
    body = sheet(client, organizer, ids["SB"])
    assert (row(body, "Boris")["withdrawn"], body["count"]) == (True, 1)
    entry = person(desk(client, organizer), "Boris")["entries"][0]
    assert entry["withdrawn"] is True
    client.delete(f"{BASE}/checkin/withdrawals/{boris['entry_key']}", headers=organizer)
    assert row(sheet(client, organizer, ids["SB"]), "Boris")["withdrawn"] is False


def test_paid_cannot_be_ticked_on_the_floor(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    boris = row(sheet(client, organizer, ids["SB"]), "Boris")

    response = cell(client, organizer, boris["entry_key"], "paid", True)

    assert response.status_code == 422
    assert row(sheet(client, organizer, ids["SB"]), "Boris")["paid"] is False


def sabre_page(tournament_code: str, rating: float, rank: int) -> str:
    session = db_session()
    found = tournament(session)
    keyword = hr_sync.category_keyword(found, tournament_code)
    assert keyword is not None
    return fighter_page([(keyword, rating, rank)])


def sabre_code() -> str:
    found = tournament(db_session())
    return next(d.taxonomy_code for d in found.disciplines if d.slug == "SB")


def test_only_the_discipline_is_fetched_and_the_office_is_untouched(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    register(client, auth_headers(email="c@example.com", name="Cyril"), ("LS",))
    set_hr_id("a@example.com", 11)
    set_hr_id("b@example.com", 22)
    set_hr_id("c@example.com", 33)
    fetcher = FakeHRFetcher()
    asked: list[int] = []
    pages = {11: sabre_page(sabre_code(), 1650.5, 12), 22: sabre_page(sabre_code(), 1400, 80)}

    def page(hr_id: int) -> str | None:
        asked.append(hr_id)
        return pages.get(hr_id)

    fetcher.fighter_page = page  # pyright: ignore[reportAttributeAccessIssue]  # a recording stand-in
    app.dependency_overrides[get_hr_fetcher] = lambda: fetcher
    adela_sb = row(sheet(client, organizer, ids["SB"]), "Adéla")
    cell(client, organizer, adela_sb["entry_key"], "rating", 1550)

    response = client.post(f"{BASE}/sheet/{ids['SB']}/ratings", headers=organizer)

    assert response.status_code == 200, response.text
    assert response.json() == {"ratings": 2, "fencers": 2}
    assert sorted(asked) == [11, 22]
    body = sheet(client, organizer, ids["SB"])
    # the hand correction survives the refresh
    assert (row(body, "Adéla")["rating"], row(body, "Adéla")["edited"]) == (1550, ["rating"])
    assert (row(body, "Boris")["rating"], row(body, "Boris")["rank"]) == (1400, 80)
    assert body["fetched_at"] is not None and body["missing"] == 0
    assert sheet(client, organizer, ids["LS"])["fetched_at"] is None
    assert db_session().scalar(select(func.count()).select_from(HRRatingSnapshot)) == 0


def test_a_rejected_fetch_keeps_the_figures(client, auth_headers):
    organizer, ids = two_disciplines(client, auth_headers)
    set_hr_id("b@example.com", 22)
    fetcher = FakeHRFetcher()
    fetcher.pages[22] = "<html>redesigned</html>"
    app.dependency_overrides[get_hr_fetcher] = lambda: fetcher

    response = client.post(f"{BASE}/sheet/{ids['SB']}/ratings", headers=organizer)

    assert response.status_code == 502
    assert sheet(client, organizer, ids["SB"])["fetched_at"] is None


def test_a_team_formed_on_the_day(client, auth_headers):
    organizer, _ = team_day(client, auth_headers)
    found = client.get(f"{BASE}/roster", headers=organizer).json()
    team_discipline = next(d["id"] for d in found["disciplines"] if d["kind"] == "team")
    body = desk(client, organizer)
    lineup = next(t for t in body["teams"])["lineup"]

    taken = client.post(
        f"{BASE}/sheet/{team_discipline}/teams",
        json={"name": "Brno B", "members": [{"person_key": lineup[0]}, {"person": {"name": "X"}}]},
        headers=organizer,
    )
    assert taken.status_code == 422, taken.text

    added = client.post(
        f"{BASE}/sheet/{team_discipline}/teams",
        json={
            "name": "Brno B",
            "members": [{"person": {"name": "Jana"}}, {"person": {"name": "Ota"}}],
        },
        headers=organizer,
    )

    assert added.status_code == 201, added.text
    key = added.json()["key"]
    team = next(t for t in sheet(client, organizer, team_discipline)["teams"] if t["key"] == key)
    assert (team["name"], team["paid"], team["added"]) == ("Brno B", False, True)
    assert [m["name"] for m in team["members"]] == ["Jana", "Ota"]
    at_desk = next(t for t in desk(client, organizer)["teams"] if t["key"] == key)
    assert len(at_desk["lineup"]) == 2

    removed = client.delete(f"{BASE}/sheet/{team_discipline}/teams/{key}", headers=organizer)
    assert removed.status_code == 204, removed.text
    assert all(t["key"] != key for t in sheet(client, organizer, team_discipline)["teams"])


def test_a_newcomer_holding_a_floor_hr_id_is_that_person(client, auth_headers):
    # the team form names every member afresh; one found in HEMA Ratings who
    # already stands on the floor fences as themself, in one lineup only
    organizer, _ = team_day(client, auth_headers)
    found = client.get(f"{BASE}/roster", headers=organizer).json()
    team_discipline = next(d["id"] for d in found["disciplines"] if d["kind"] == "team")
    body = sheet(client, organizer, team_discipline)
    holder = body["teams"][0]["members"][0]
    cell(client, organizer, holder["person"], "hr_id", 4242)

    twice = client.post(
        f"{BASE}/sheet/{team_discipline}/teams",
        json={
            "name": "Brno B",
            "members": [
                {"person": {"name": "Someone", "hr_id": 4242}},
                {"person": {"name": "Ota"}},
            ],
        },
        headers=organizer,
    )
    assert twice.status_code == 422, twice.text
    assert "in_another_lineup" in twice.text


def test_a_closed_discipline_is_the_snapshot_and_refuses_writes(client, auth_headers):
    organizer, ids, _ = closed_sabre(client, auth_headers)
    body = sheet(client, organizer, ids["SB"])
    first = body["rows"][0]

    assert body["closed_at"] is not None
    assert body["count"] == 3
    assert cell(client, organizer, first["entry_key"], "rating", 1).status_code == 409
    assert client.post(f"{BASE}/sheet/{ids['SB']}/ratings", headers=organizer).status_code == 409
    added = client.post(
        f"{BASE}/sheet/{ids['SB']}/entries", json={"person": {"name": "Late"}}, headers=organizer
    )
    assert added.status_code == 409


def test_the_snapshot_keeps_a_corrected_rating(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, sabre_capacity=5)
    register(client, auth_headers(email="a@example.com", name="Adéla"), ("SB",))
    ids = discipline_ids(client, organizer)
    adela = row(sheet(client, organizer, ids["SB"]), "Adéla")
    cell(client, organizer, adela["entry_key"], "rating", 1550)
    arrive(client, organizer, adela["person"])

    closed = client.post(f"{BASE}/checkin/{ids['SB']}/close", headers=organizer)

    assert closed.status_code == 204, closed.text
    frozen = db_session().scalars(select(FloorSnapshotEntrant)).one()
    assert frozen.rating == 1550
