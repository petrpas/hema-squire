"""Check-in at the desk (spec floor-checkin) and the day's overview (spec
floor-today), through the API."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.floor import gates
from app.floor.models import FloorPlan, FloorPlanActivity, FloorSnapshotEntrant
from app.models import Registration, TeamMember
from tests.floor.test_floor_roster import db_session, registration_of, save_roster, tournament
from tests.floor.test_floor_setup import BASE, discipline_ids
from tests.test_entrants import enter_team, register, setup_team_tournament, setup_tournament


def desk(client, headers) -> dict:
    response = client.get(f"{BASE}/checkin", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def person(body: dict, name: str) -> dict:
    return next(p for p in body["persons"] if p["name"] == name)


def counts(body: dict) -> dict[str, tuple[int, int]]:
    return {d["slug"]: (d["entered"], d["present"]) for d in body["disciplines"]}


def arrive(client, headers, key: str) -> None:
    response = client.post(f"{BASE}/checkin/arrivals", json={"person_key": key}, headers=headers)
    assert response.status_code == 204, response.text


def test_one_tick_for_two_disciplines(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, sabre_capacity=5)
    register(client, auth_headers(email="a@example.com", name="Adéla"), ("LS", "SB"))

    arrive(client, organizer, person(desk(client, organizer), "Adéla")["key"])
    # a second desk ticking the same person changes nothing
    arrive(client, organizer, person(desk(client, organizer), "Adéla")["key"])

    assert counts(desk(client, organizer)) == {"LS": (1, 1), "SB": (1, 1)}


def test_unpaid_is_shown_not_blocked(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))

    arrive(client, organizer, person(desk(client, organizer), "Adéla")["key"])

    adela = person(desk(client, organizer), "Adéla")
    assert adela["arrived"] is True
    assert [e["paid"] for e in adela["entries"]] == [False]


def test_a_withdrawal_does_not_cancel_the_registration(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, sabre_capacity=5)
    register(client, auth_headers(email="a@example.com", name="Adéla"), ("LS", "SB"))
    before = registration_of("a@example.com")
    snapshot = (before.state, before.total_amount, before.cancelled_at)
    ids = discipline_ids(client, organizer)
    key = person(desk(client, organizer), "Adéla")["key"]

    response = client.post(
        f"{BASE}/checkin/withdrawals", json={"entry_key": f"{key}@{ids['SB']}"}, headers=organizer
    )

    assert response.status_code == 204, response.text
    assert counts(desk(client, organizer))["SB"] == (0, 0)
    after = registration_of("a@example.com")
    assert (after.state, after.total_amount, after.cancelled_at) == snapshot


def team_day(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    captain = auth_headers(email="a@example.com", name="Adéla")
    team_id = enter_team(client, captain, "Draci")["teams"][0]["id"]
    save_roster(client, captain, team_id, [{"name": "Eva"}, {"name": "Filip"}, {"name": "Gita"}])
    return organizer, f"team:{team_id}"


def test_a_substitute_on_the_day(client, auth_headers):
    organizer, team = team_day(client, auth_headers)
    members_before = db_session().scalar(select(func.count()).select_from(TeamMember))
    body = desk(client, organizer)
    lineup = next(t for t in body["teams"] if t["key"] == team)["members"]

    local = client.post(f"{BASE}/checkin/locals", json={"name": "Petr Dvořák"}, headers=organizer)
    assert local.status_code == 201, local.text
    substitute = local.json()["key"]
    saved = client.put(
        f"{BASE}/checkin/lineups/{team}",
        json={"person_keys": [lineup[0], lineup[1], substitute]},
        headers=organizer,
    )

    assert saved.status_code == 204, saved.text
    body = desk(client, organizer)
    assert next(t for t in body["teams"] if t["key"] == team)["lineup"][2] == substitute
    assert person(body, "Petr Dvořák")["local"] is True
    assert db_session().scalar(select(func.count()).select_from(TeamMember)) == members_before


def test_a_team_short_of_its_minimum_is_not_present(client, auth_headers):
    organizer, team = team_day(client, auth_headers)
    lineup = next(t for t in desk(client, organizer)["teams"] if t["key"] == team)["lineup"]
    # the team discipline asks for two; only one arrives
    arrive(client, organizer, lineup[0])

    row = next(t for t in desk(client, organizer)["teams"] if t["key"] == team)

    assert (row["present"], row["short_by"]) == (False, 1)


def test_a_lineup_outside_its_bounds_is_refused(client, auth_headers):
    organizer, team = team_day(client, auth_headers)
    lineup = next(t for t in desk(client, organizer)["teams"] if t["key"] == team)["lineup"]

    response = client.put(
        f"{BASE}/checkin/lineups/{team}", json={"person_keys": lineup[:1]}, headers=organizer
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["code"] == "lineup_size"


def closed_sabre(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, sabre_capacity=5)
    fencers = [auth_headers(email=f"s{n}@example.com", name=f"Sabre {n}") for n in range(3)]
    for headers in fencers:
        register(client, headers, ("SB",))
    for row in desk(client, organizer)["persons"]:
        arrive(client, organizer, row["key"])
    ids = discipline_ids(client, organizer)
    impact = client.get(f"{BASE}/checkin/{ids['SB']}/close", headers=organizer)
    assert impact.status_code == 200, impact.text
    assert impact.json()["n"] == 3
    closed = client.post(f"{BASE}/checkin/{ids['SB']}/close", headers=organizer)
    assert closed.status_code == 204, closed.text
    return organizer, ids, fencers


def test_closing_pins_n_and_freezes_the_list(client, auth_headers):
    organizer, ids, fencers = closed_sabre(client, auth_headers)

    cancelled = client.post("/api/tournaments/cup/my-registration/cancel", headers=fencers[0])
    assert cancelled.status_code == 200, cancelled.text

    sabre = next(d for d in desk(client, organizer)["disciplines"] if d["slug"] == "SB")
    assert (sabre["closed"], sabre["n"]) == (True, 3)
    assert db_session().scalar(select(func.count()).select_from(FloorSnapshotEntrant)) == 3
    (pin,) = client.get(f"{BASE}/plan", headers=organizer).json()["pins"]
    assert (pin["kind"], pin["value"], pin["gate"]) == ("n", {"n": 3}, f"checkin:{ids['SB']}")


def test_reopening_after_the_draw_lists_and_discards_it(client, auth_headers):
    organizer, ids, _ = closed_sabre(client, auth_headers)
    discarded: list[int] = []
    hook = gates.Hook(
        describe=lambda session, tid, d: ["draw"],
        discard=lambda session, tid, d: discarded.append(d),
        refuse=lambda session, tid, d: [],
    )
    gates.register("checkin", hook)
    try:
        preview = client.get(f"{BASE}/checkin/{ids['SB']}/reopen", headers=organizer).json()
        reopened = client.post(f"{BASE}/checkin/{ids['SB']}/reopen", headers=organizer)
    finally:
        gates._hooks["checkin"].remove(hook)  # pyright: ignore[reportPrivateUsage]  # the test's own hook, taken back

    assert preview == {"invalidated": ["n_pin", "snapshot", "draw"], "refusals": []}
    assert reopened.status_code == 204, reopened.text
    assert discarded == [ids["SB"]]
    assert client.get(f"{BASE}/plan", headers=organizer).json()["pins"] == []


def test_reopening_after_a_result_is_refused(client, auth_headers):
    organizer, ids, _ = closed_sabre(client, auth_headers)
    hook = gates.Hook(
        describe=lambda session, tid, d: [],
        discard=lambda session, tid, d: None,
        refuse=lambda session, tid, d: ["SB:pool:1"],
    )
    gates.register("checkin", hook)
    try:
        refused = client.post(f"{BASE}/checkin/{ids['SB']}/reopen", headers=organizer)
    finally:
        gates._hooks["checkin"].remove(hook)  # pyright: ignore[reportPrivateUsage]  # the test's own hook, taken back

    assert refused.status_code == 409
    assert refused.json()["detail"] == {"reason": "results_recorded", "items": ["SB:pool:1"]}


def publish_first_pool_in(minutes: int, discipline_id: int) -> None:
    """A published plan whose one activity starts `minutes` from now."""
    session = db_session()
    tid = tournament(session).id
    now = datetime.now(UTC)
    plan = FloorPlan(tournament_id=tid, version=1, status="published", created_at=now)
    session.add(plan)
    session.flush()
    start = now + timedelta(minutes=minutes)
    session.add(
        FloorPlanActivity(
            plan_id=plan.id,
            activity_id="RP:pool:1",
            discipline_id=discipline_id,
            kind="pool",
            ordinal=1,
            round=0,
            piste_id=1,
            starts_at=start,
            ends_at=start + timedelta(minutes=45),
        )
    )
    session.commit()


def test_open_checkin_before_the_first_pool_waits(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    publish_first_pool_in(25, ids["SB"])

    summary = client.get(f"{BASE}/summary", headers=organizer).json()
    today = client.get(f"{BASE}/today", headers=organizer).json()

    assert summary["badges"]["checkin"] is True
    assert {"tab": "checkin", "discipline": "SB", "code": "checkin_open"} in today["waiting"]


def test_the_matrix_states_each_step(client, auth_headers):
    organizer, _, _ = closed_sabre(client, auth_headers)

    rows = {
        r["slug"]: r["steps"] for r in client.get(f"{BASE}/today", headers=organizer).json()["rows"]
    }

    assert rows["SB"]["checkin"] == "closed"
    assert rows["LS"] == {
        "checkin": "open",
        "pools": "waiting",
        "bracket": "waiting",
        "results": "waiting",
    }


def test_an_unchanged_state_costs_a_304(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    first = client.get(f"{BASE}/today", headers=organizer)
    tag = first.headers["etag"]

    again = client.get(f"{BASE}/today", headers={**organizer, "If-None-Match": tag})
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    desk_first = client.get(f"{BASE}/checkin", headers=organizer)
    changed = client.get(
        f"{BASE}/checkin", headers={**organizer, "If-None-Match": desk_first.headers["etag"]}
    )

    assert again.status_code == 304
    assert changed.status_code == 304
    assert registration_of("a@example.com").id == db_session().scalar(select(Registration.id))
