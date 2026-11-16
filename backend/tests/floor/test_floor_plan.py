"""Plan versions, pins, publishing, the difference and re-planning (spec
floor-plan), through the API."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.floor import progress
from app.floor.models import FloorPin, FloorPlan
from tests.floor.test_floor_roster import db_session, tournament
from tests.floor.test_floor_setup import BASE, discipline_ids, fmt, ok, put
from tests.test_entrants import register, setup_tournament


def ready(client, auth_headers, *, fencers: int = 10, both: bool = False) -> tuple[dict, dict]:
    """A published tournament with ten Longsword fencers (and in Sabre too,
    where `both`), four pistes and both formats saved."""
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False, sabre_capacity=10)
    for n in range(fencers):
        disciplines = ("LS", "SB") if both else ("LS",)
        register(client, auth_headers(email=f"f{n}@example.com", name=f"Fencer {n}"), disciplines)
    ids = discipline_ids(client, organizer)
    ok(
        put(
            client,
            organizer,
            "pistes",
            [{"name": str(n), "days": ["2099-12-05"]} for n in range(1, 5)],
        )
    )
    ok(
        put(
            client,
            organizer,
            "formats",
            [fmt(ids["LS"], pool_min=5, pool_max=5), fmt(ids["SB"], pool_min=5, pool_max=5)],
        )
    )
    return organizer, ids


def variants(client, headers) -> dict:
    response = client.post(f"{BASE}/plan/variants", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def choose(client, headers, key: str) -> None:
    ok(client.post(f"{BASE}/plan/choose", json={"key": key}, headers=headers))


def state(client, headers) -> dict:
    response = client.get(f"{BASE}/plan", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def publish(client, headers):
    return client.post(f"{BASE}/plan/publish", headers=headers)


def test_choosing_a_variant_makes_it_the_working_version(client, auth_headers):
    organizer, _ = ready(client, auth_headers)
    found = variants(client, organizer)
    assert found["variants"], found
    chosen = found["variants"][-1]

    choose(client, organizer, chosen["key"])

    working = state(client, organizer)["working"]
    assert working["status"] == "working"
    assert working["choices"] == chosen["choices"]
    assert {a["id"] for a in working["activities"]} == {a["id"] for a in chosen["activities"]}


def test_publishing_replaces_the_published_version(client, auth_headers):
    organizer, _ = ready(client, auth_headers)
    key = variants(client, organizer)["variants"][0]["key"]
    for _ in range(3):
        choose(client, organizer, key)
        ok(publish(client, organizer))

    choose(client, organizer, key)
    ok(publish(client, organizer))

    plan = state(client, organizer)
    assert plan["published"]["version"] == 4
    assert plan["history"] == [3, 2, 1]
    assert plan["working"] is None
    summary = client.get(f"{BASE}/summary", headers=organizer).json()
    assert summary["plan_published"] is True


def test_a_pinned_day_holds(client, auth_headers):
    organizer, ids = ready(client, auth_headers)
    ok(
        put(
            client,
            organizer,
            "days",
            [
                {"date": "2099-12-05", "start": "09:00", "end": "19:00"},
                {"date": "2099-12-06", "start": "09:00", "end": "19:00"},
            ],
        )
    )
    ok(
        put(
            client,
            organizer,
            "pistes",
            [{"name": str(n), "days": ["2099-12-05", "2099-12-06"]} for n in range(1, 5)],
        )
    )
    pinned = client.post(
        f"{BASE}/plan/pins",
        json={"kind": "day", "target": str(ids["LS"]), "value": {"day": "2099-12-06"}},
        headers=organizer,
    )
    assert pinned.status_code == 201, pinned.text

    found = variants(client, organizer)["variants"]

    assert found
    for variant in found:
        (choice,) = [c for c in variant["choices"] if c["discipline_id"] == ids["LS"]]
        assert choice["day"] == "2099-12-06"


def test_a_gates_pin_is_not_removed_from_the_plan_tab(client, auth_headers):
    organizer, ids = ready(client, auth_headers)
    session = db_session()
    pin = FloorPin(
        tournament_id=tournament(session).id,
        kind="k",
        target=str(ids["LS"]),
        value={"k": 2},
        gate="checkin",
        created_at=datetime.now(UTC),
        created_by=None,
    )
    session.add(pin)
    session.commit()

    (listed,) = state(client, organizer)["pins"]
    refused = client.delete(f"{BASE}/plan/pins/{pin.id}", headers=organizer)

    assert listed["gate"] == "checkin"
    assert refused.status_code == 409
    assert refused.json()["detail"] == "pin_from_gate"


def test_an_obstacle_blocks_publication(client, auth_headers):
    # the same ten fence both; everything runs at once, so nobody fits outside
    organizer, ids = ready(client, auth_headers, both=True)
    found = variants(client, organizer)
    choose(client, organizer, found["variants"][0]["key"])

    refused = publish(client, organizer)

    assert refused.status_code == 409
    detail = refused.json()["detail"]
    pair = sorted((ids["LS"], ids["SB"]))
    assert detail["obstacles"] == [f"shortage:{pair[0]}:{pair[1]}"]
    assert state(client, organizer)["obstacles"] == detail["obstacles"]


def test_a_moved_pool_is_stated(client, auth_headers):
    organizer, ids = ready(client, auth_headers)
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))
    before = next(
        a for a in state(client, organizer)["published"]["activities"] if a["id"] == "LS:pool:1"
    )
    pistes = client.get(f"{BASE}/setup", headers=organizer).json()["pistes"]
    other = next(p["id"] for p in pistes if p["id"] != before["piste_id"])
    pinned = client.post(
        f"{BASE}/plan/pins",
        json={
            "kind": "place",
            "target": "LS:pool:1",
            "value": {"piste": other, "day": "2099-12-05", "start": "10:20"},
        },
        headers=organizer,
    )
    assert pinned.status_code == 201, pinned.text

    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])

    moved = [c for c in state(client, organizer)["diff"] if c["activity"] == "LS:pool:1"]
    assert moved == [
        {
            "activity": "LS:pool:1",
            "kind": "moved",
            "before": [before["piste_id"], "2099-12-05", before["start"]],
            "after": [other, "2099-12-05", "10:20"],
        }
    ]


def test_replanning_freezes_the_past(client, auth_headers):
    organizer, _ = ready(client, auth_headers)
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))
    published = {a["id"]: a for a in state(client, organizer)["published"]["activities"]}

    def source(session, tid, now):
        return {"LS:pool:2"}

    progress.register(source)
    try:
        response = client.post(f"{BASE}/plan/replan", headers=organizer)
    finally:
        progress._sources.remove(source)  # pyright: ignore[reportPrivateUsage]  # the test's own registration, taken back

    assert response.status_code == 200, response.text
    working = {a["id"]: a for a in state(client, organizer)["working"]["activities"]}
    kept = working["LS:pool:2"]
    assert (kept["piste_id"], kept["start"]) == (
        published["LS:pool:2"]["piste_id"],
        published["LS:pool:2"]["start"],
    )
    rows = db_session().scalars(select(FloorPlan.status)).all()
    assert sorted(rows) == ["published", "working"]


def test_the_planner_refuses_an_incomplete_setup(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = client.post(f"{BASE}/plan/variants", headers=organizer)

    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "setup_incomplete"
