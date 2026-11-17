"""The draw, the pools and the piste screen (specs floor-draw, floor-pools,
floor-ring), through the API."""

from datetime import timedelta

from app.floor.engine.pool_order import order
from app.floor.models import FloorBout, FloorPool
from app.ratelimit import limiter
from tests.floor.test_floor_checkin import desk
from tests.floor.test_floor_plan import choose, publish, ready, variants
from tests.floor.test_floor_roster import db_session
from tests.floor.test_floor_setup import BASE, ok


def planned(client, auth_headers, *, close_checkin: bool = True):
    """Ten Longsword fencers in two pools of five on a published plan, all
    arrived; check-in closed where asked."""
    organizer, ids = ready(client, auth_headers)
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))
    for row in desk(client, organizer)["persons"]:
        ok(
            client.post(
                f"{BASE}/checkin/arrivals", json={"person_key": row["key"]}, headers=organizer
            )
        )
    if close_checkin:
        ok(client.post(f"{BASE}/checkin/{ids['LS']}/close", headers=organizer))
    return organizer, ids["LS"]


def pools_of(client, headers, discipline: int) -> dict:
    response = client.get(f"{BASE}/pools/{discipline}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def drawn(client, auth_headers, *, announce: bool = True):
    organizer, ls = planned(client, auth_headers)
    ok(client.post(f"{BASE}/pools/{ls}/draw", headers=organizer))
    if announce:
        ok(client.post(f"{BASE}/pools/{ls}/announce", headers=organizer))
    return organizer, ls


def record(client, headers, bout: dict, a: int = 5, b: int = 3):
    return client.put(
        f"{BASE}/pools/bouts/{bout['id']}",
        json={
            "score_a": a,
            "score_b": b,
            "outcome_a": "win" if a > b else "loss",
            "outcome_b": "loss" if a > b else "win",
            "version": bout["version"],
        },
        headers=headers,
    )


def test_the_draw_needs_a_closed_checkin(client, auth_headers):
    organizer, ls = planned(client, auth_headers, close_checkin=False)

    refused = client.post(f"{BASE}/pools/{ls}/draw", headers=organizer)

    assert refused.status_code == 409
    assert refused.json()["detail"] == "checkin_open"


def test_the_draw_reproduces_from_its_seed(client, auth_headers):
    from app.floor import pools as service
    from app.floor.adapters.office import roster, setup_facts
    from tests.floor.test_floor_roster import tournament

    organizer, ls = planned(client, auth_headers)
    session = db_session()
    found = tournament(session)
    discipline = next(d for d in setup_facts(found).disciplines if d.id == ls)
    members = []
    for _ in range(2):
        draw = service.make(session, found.id, roster(session, found), discipline, seed=4242)
        members.append(
            [
                [m.entrant_key for m in service.members_of(session, p)]
                for p in service.pools_of(session, draw)
            ]
        )

    assert members[0] == members[1]


def test_a_swap_shows_its_cost_and_a_locked_seed_is_refused(client, auth_headers):
    organizer, ls = drawn(client, auth_headers, announce=False)
    draw = pools_of(client, organizer, ls)["draw"]
    seeds = {m["seed"]: m["key"] for p in draw["pools"] for m in p["members"]}

    locked = client.post(
        f"{BASE}/pools/{ls}/swap", json={"a": seeds[1], "b": seeds[2]}, headers=organizer
    )
    swapped = client.post(
        f"{BASE}/pools/{ls}/swap", json={"a": seeds[9], "b": seeds[10]}, headers=organizer
    )

    assert locked.status_code == 409 and locked.json()["detail"] == "locked_seed"
    assert swapped.status_code == 204, swapped.text
    after = pools_of(client, organizer, ls)["draw"]
    assert after["previous_score"] == draw["score"]
    assert set(after["score"]) == {"snake", "club", "nationality", "wave", "total"}


def test_a_pool_lists_its_bouts_in_the_template_order(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)

    pool = pools_of(client, organizer, ls)["draw"]["pools"][0]

    keys = [m["key"] for m in pool["members"]]
    assert [(keys.index(b["a"]) + 1, keys.index(b["b"]) + 1) for b in pool["bouts"]] == list(
        order(5)
    )


def test_a_whole_sheet_is_transcribed_and_the_matrix_follows(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    body = pools_of(client, organizer, ls)
    first, second = body["draw"]["pools"]
    assert body["state"] == "running"

    one = record(client, organizer, first["bouts"][0])
    assert one.status_code == 204, one.text
    today = {
        r["discipline_id"]: r for r in client.get(f"{BASE}/today", headers=organizer).json()["rows"]
    }
    assert today[ls]["steps"]["pools"] == "running"

    for pool in (first, second):
        sheet = [
            {
                "id": b["id"],
                "score_a": 5,
                "score_b": n % 5,
                "outcome_a": "win",
                "outcome_b": "loss",
                "version": b["version"],
            }
            for n, b in enumerate(pool["bouts"])
            if b is not first["bouts"][0]
        ]
        ok(client.put(f"{BASE}/pools/{ls}/sheet", json={"bouts": sheet}, headers=organizer))

    assert pools_of(client, organizer, ls)["state"] == "complete"


def test_a_stale_version_is_refused(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    bout = pools_of(client, organizer, ls)["draw"]["pools"][0]["bouts"][0]
    ok(record(client, organizer, bout))

    stale = record(client, organizer, bout, 1, 5)

    assert stale.status_code == 409
    assert stale.json()["detail"] == "stale_version"


def finish(client, organizer, ls) -> None:
    for pool in pools_of(client, organizer, ls)["draw"]["pools"]:
        for n, bout in enumerate(pool["bouts"]):
            ok(record(client, organizer, bout, 5, n % 5))


def test_who_advances_is_shown_before_closing(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    finish(client, organizer, ls)

    preview = client.get(f"{BASE}/pools/{ls}/close", headers=organizer).json()
    ok(client.post(f"{BASE}/pools/{ls}/close", headers=organizer))

    # the format advances all
    assert preview["advance"] == 10
    assert len(preview["ranking"]) == 10
    assert pools_of(client, organizer, ls)["state"] == "closed"


def test_the_next_wave_is_called(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)

    called = pools_of(client, organizer, ls)["call_list"]

    assert called and all(c["wave"] == called[0]["wave"] for c in called)
    assert all(len(c["members"]) == 5 for c in called)


def test_a_late_pool_is_slip(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    bout = pools_of(client, organizer, ls)["draw"]["pools"][0]["bouts"][0]
    ok(record(client, organizer, bout))
    session = db_session()
    row = session.get(FloorBout, bout["id"])
    assert row is not None
    pool = session.get(FloorPool, row.pool_id)
    assert pool is not None and pool.planned_start is not None
    row.recorded_at = pool.planned_start + timedelta(minutes=20)
    session.commit()

    today = {
        r["discipline_id"]: r for r in client.get(f"{BASE}/today", headers=organizer).json()["rows"]
    }

    assert today[ls]["slip"] == 20


def test_reopening_checkin_discards_the_draw_but_not_over_results(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    preview = client.get(f"{BASE}/checkin/{ls}/reopen", headers=organizer).json()
    assert "draw" in preview["invalidated"]

    bout = pools_of(client, organizer, ls)["draw"]["pools"][0]["bouts"][0]
    ok(record(client, organizer, bout))
    refused = client.post(f"{BASE}/checkin/{ls}/reopen", headers=organizer)

    assert refused.status_code == 409
    assert refused.json()["detail"]["reason"] == "results_recorded"


# ------------------------------------------------------------ the piste screen


def piste_key(client, organizer, piste_id: int) -> str:
    issued = client.post(f"{BASE}/ring/{piste_id}", headers=organizer)
    assert issued.status_code == 201, issued.text
    return issued.json()["key"]


def ring_record(client, key: str, bout: dict, version: int | None = None):
    return client.put(
        f"/api/floor/ring/bouts/{bout['id']}",
        json={
            "score_a": 5,
            "score_b": 1,
            "outcome_a": "win",
            "outcome_b": "loss",
            "version": bout["version"] if version is None else version,
        },
        headers={"X-Floor-Ring-Key": key},
    )


def test_a_piste_screen_records_its_own_pool_only(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    pools = pools_of(client, organizer, ls)["draw"]["pools"]
    key = piste_key(client, organizer, pools[0]["piste_id"])

    current = client.get("/api/floor/ring/current", headers={"X-Floor-Ring-Key": key})
    assert current.status_code == 200, current.text
    own = next(p for p in pools if p["number"] == current.json()["pool"]["number"])
    others = [p for p in pools if p["piste_id"] != own["piste_id"]]

    assert ring_record(client, key, own["bouts"][0]).status_code == 204
    row = db_session().get(FloorBout, own["bouts"][0]["id"])
    assert row is not None and row.recorded_by == f"ring:{own['piste_id']}"
    if others:
        elsewhere = ring_record(client, key, others[0]["bouts"][0])
        assert elsewhere.status_code == 409
        assert elsewhere.json()["detail"] == "not_this_piste"


def test_a_revoked_key_stops_working(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    piste = pools_of(client, organizer, ls)["draw"]["pools"][0]["piste_id"]
    old = piste_key(client, organizer, piste)
    new = piste_key(client, organizer, piste)

    assert (
        client.get("/api/floor/ring/current", headers={"X-Floor-Ring-Key": old}).status_code == 404
    )
    assert (
        client.get("/api/floor/ring/current", headers={"X-Floor-Ring-Key": new}).status_code == 200
    )
    ok(client.delete(f"{BASE}/ring/{piste}", headers=organizer))
    assert (
        client.get("/api/floor/ring/current", headers={"X-Floor-Ring-Key": new}).status_code == 404
    )


def test_a_closed_pool_refuses_the_piste(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    pool = pools_of(client, organizer, ls)["draw"]["pools"][0]
    key = piste_key(client, organizer, pool["piste_id"])
    finish(client, organizer, ls)
    ok(client.post(f"{BASE}/pools/{ls}/close", headers=organizer))
    bout = next(
        b
        for p in pools_of(client, organizer, ls)["draw"]["pools"]
        if p["piste_id"] == pool["piste_id"]
        for b in p["bouts"]
    )

    refused = client.put(
        f"/api/floor/ring/bouts/{bout['id']}",
        json={
            "score_a": 5,
            "score_b": 4,
            "outcome_a": "win",
            "outcome_b": "loss",
            "version": bout["version"],
        },
        headers={"X-Floor-Ring-Key": key},
    )

    assert refused.status_code == 409
    assert refused.json()["detail"] == "pools_closed"


def test_the_piste_screen_is_rate_limited(client, auth_headers):
    limiter.reset()
    limiter.enabled = True
    try:
        statuses = [
            client.get(
                "/api/floor/ring/current", headers={"X-Floor-Ring-Key": "nobody-at-all"}
            ).status_code
            for _ in range(125)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses[0] == 404
    assert 429 in statuses


def test_a_pool_sheet_prints(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)

    response = client.get(f"{BASE}/pools/{ls}/sheets/1", headers=organizer)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
