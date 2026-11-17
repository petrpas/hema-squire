"""The elimination (spec floor-bracket), through the API. Ten Longsword
fencers fence two pools of five, all advance into a bracket of sixteen with
six byes."""

from sqlalchemy import select

from app.floor.models import FloorFormat
from tests.floor.test_floor_pools import drawn, finish, pools_of
from tests.floor.test_floor_roster import db_session
from tests.floor.test_floor_setup import BASE, ok


def closed_pools(client, auth_headers, *, third: bool = False):
    organizer, ls = drawn(client, auth_headers)
    finish(client, organizer, ls)
    if third:
        session = db_session()
        row = session.scalars(select(FloorFormat).where(FloorFormat.discipline_id == ls)).one()
        row.third_place = True
        session.commit()
    ok(client.post(f"{BASE}/pools/{ls}/close", headers=organizer))
    return organizer, ls


def view(client, headers, ls: int) -> dict:
    response = client.get(f"{BASE}/bracket/{ls}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def confirmed(client, auth_headers, *, third: bool = False):
    organizer, ls = closed_pools(client, auth_headers, third=third)
    ok(client.post(f"{BASE}/bracket/{ls}/confirm", headers=organizer))
    return organizer, ls


def record(client, headers, ls: int, bout: dict, a: int = 15, b: int = 9, **extra):
    body = {
        "score_a": a,
        "score_b": b,
        "outcome_a": "win" if a > b else "loss",
        "outcome_b": "loss" if a > b else "win",
        "version": bout["version"],
        **extra,
    }
    return client.put(f"{BASE}/bracket/{ls}/bouts/{bout['id']}", json=body, headers=headers)


def open_bouts(body: dict) -> list[dict]:
    return [b for b in body["bracket"]["bouts"] if b["score_a"] is None]


def test_the_bracket_waits_for_the_pools(client, auth_headers):
    organizer, ls = drawn(client, auth_headers)
    finish(client, organizer, ls)

    body = view(client, organizer, ls)
    refused = client.post(f"{BASE}/bracket/{ls}/confirm", headers=organizer)

    assert (body["pools_closed"], body["proposal"]) == (False, None)
    assert refused.status_code == 409 and refused.json()["detail"] == "pools_open"


def test_the_proposal_seeds_the_ranking_with_byes_to_the_top(client, auth_headers):
    organizer, ls = closed_pools(client, auth_headers)

    proposal = view(client, organizer, ls)["proposal"]

    assert (proposal["size"], proposal["advancing"]) == (16, 10)
    byes = [s for s in proposal["slots"] if s["seed"] is None]
    assert len(byes) == 6


def test_a_winner_advances(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)
    body = view(client, organizer, ls)
    first = open_bouts(body)[0]

    ok(record(client, organizer, ls, first))

    slots = {
        (s["round"], s["position"]): s for s in view(client, organizer, ls)["bracket"]["slots"]
    }
    assert slots[(1, first["position"])]["key"] == first["a"]


def test_a_correction_that_would_orphan_a_later_result_is_refused(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)
    first = open_bouts(view(client, organizer, ls))[0]
    ok(record(client, organizer, ls, first))
    later = next(
        b
        for b in open_bouts(view(client, organizer, ls))
        if b["round"] == 1 and b["position"] == first["position"] // 2
    )
    ok(record(client, organizer, ls, later))
    first_now = next(
        b for b in view(client, organizer, ls)["bracket"]["bouts"] if b["id"] == first["id"]
    )

    refused = record(client, organizer, ls, first_now, 3, 15)

    assert refused.status_code == 409
    assert refused.json()["detail"]["reason"] == "next_recorded"
    assert refused.json()["detail"]["items"] == [f"r2:{later['position'] + 1}"]


def test_a_draw_is_refused_and_a_walkover_needs_its_note(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)
    bout = open_bouts(view(client, organizer, ls))[0]

    drawn_bout = client.put(
        f"{BASE}/bracket/{ls}/bouts/{bout['id']}",
        json={"score_a": 5, "score_b": 5, "outcome_a": "draw", "outcome_b": "draw", "version": 0},
        headers=organizer,
    )
    bare = client.put(
        f"{BASE}/bracket/{ls}/bouts/{bout['id']}",
        json={"score_a": 0, "score_b": 0, "outcome_a": "no", "outcome_b": "win", "version": 0},
        headers=organizer,
    )
    walkover = client.put(
        f"{BASE}/bracket/{ls}/bouts/{bout['id']}",
        json={
            "score_a": 0,
            "score_b": 0,
            "outcome_a": "no",
            "outcome_b": "win",
            "note": "medical",
            "version": 0,
        },
        headers=organizer,
    )

    assert drawn_bout.json()["detail"] == "draw_refused"
    assert bare.json()["detail"] == "walkover_note"
    assert walkover.status_code == 204, walkover.text
    slots = {
        (s["round"], s["position"]): s for s in view(client, organizer, ls)["bracket"]["slots"]
    }
    assert slots[(1, bout["position"])]["key"] == bout["b"]


def test_the_bracket_closes_after_the_final_and_the_third_place(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers, third=True)

    for _ in range(20):
        body = view(client, organizer, ls)
        pending = open_bouts(body)
        if not pending:
            break
        ok(record(client, organizer, ls, pending[0], 45, 38))

    body = view(client, organizer, ls)
    third = [b for b in body["bracket"]["bouts"] if b["round"] == 3 and b["position"] == 1]
    today = {
        r["discipline_id"]: r for r in client.get(f"{BASE}/today", headers=organizer).json()["rows"]
    }
    assert body["state"] == "closed"
    assert len(third) == 1 and (third[0]["score_a"], third[0]["score_b"]) == (45, 38)
    assert today[ls]["steps"]["bracket"] == "closed"


def test_reopening_the_pools_is_refused_once_the_bracket_has_a_result(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)
    ok(record(client, organizer, ls, open_bouts(view(client, organizer, ls))[0]))

    refused = client.post(f"{BASE}/pools/{ls}/reopen-pools", headers=organizer)

    assert refused.status_code == 409
    assert refused.json()["detail"]["reason"] == "results_recorded"
    assert pools_of(client, organizer, ls)["state"] == "closed"


def test_a_printed_bracket_shows_results_so_far(client, auth_headers):
    organizer, ls = confirmed(client, auth_headers)
    ok(record(client, organizer, ls, open_bouts(view(client, organizer, ls))[0]))

    response = client.get(f"{BASE}/bracket/{ls}/sheet", headers=organizer)

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
