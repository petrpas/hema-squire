"""Floor Setup (spec floor-setup), one test per scenario, through the API."""

from sqlalchemy import select

from app.floor.models import FloorFormat
from app.models import Discipline
from tests.floor.test_floor_roster import db_session
from tests.test_entrants import register, setup_team_tournament, setup_tournament

BASE = "/api/tournaments/cup/floor"


def read(client, headers) -> dict:
    response = client.get(f"{BASE}/setup", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def put(client, headers, section: str, body):
    return client.put(f"{BASE}/setup/{section}", json=body, headers=headers)


def ok(response) -> None:
    assert response.status_code == 204, response.text


def errors(response) -> set[tuple[str, str]]:
    assert response.status_code == 422, response.text
    return {(e["field"], e["code"]) for e in response.json()["detail"]["errors"]}


def fmt(discipline_id: int, **overrides) -> dict:
    return {
        "discipline_id": discipline_id,
        "pool_min": 5,
        "pool_max": 7,
        "advance": None,
        "third_place": False,
        "slot_pool_bout": 4,
        "slot_elim_bout": 6,
        "pause_between_pools": 5,
        **overrides,
    }


def discipline_ids(client, headers) -> dict[str, int]:
    return {d["slug"]: d["id"] for d in read(client, headers)["disciplines"]}


def scope(client, headers, **ticks) -> None:
    ok(put(client, headers, "scope", {"plan_schedule": True, "multi_day": False, **ticks}))


def serving(*discipline_ids: int, reserve: bool = False) -> list[dict]:
    return [{"discipline_id": d, "reserve": reserve} for d in discipline_ids]


def summary_missing(client, headers) -> list[str]:
    return client.get(f"{BASE}/summary", headers=headers).json()["setup_missing"]


def day(when: str = "2099-12-05", start: str = "09:00", end: str = "19:00", **rest) -> dict:
    return {"date": when, "start": start, "end": end, **rest}


# ------------------------------------------------------------ days


def test_the_default_day(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    days = read(client, organizer)["days"]

    assert days == {
        "stored": False,
        "days": [{**day(), "breaks": [], "discipline_ids": [ids["LS"], ids["SB"]]}],
    }


def test_a_break_outside_the_day_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(
        client,
        organizer,
        "days",
        [day(end="18:00", breaks=[{"start": "18:30", "end": "19:00"}])],
    )

    assert errors(response) == {("0.breaks.0", "break_outside_day")}
    assert read(client, organizer)["days"]["stored"] is False


def test_overlapping_breaks_and_a_backwards_day_are_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    scope(client, organizer, multi_day=True)

    response = put(
        client,
        organizer,
        "days",
        [
            day(
                end="18:00",
                breaks=[{"start": "12:00", "end": "13:00"}, {"start": "12:30", "end": "13:30"}],
            ),
            day("2099-12-06", "18:00", "09:00"),
        ],
    )

    assert errors(response) == {("0.breaks.1", "breaks_overlap"), ("1.end", "end_not_after_start")}


def test_ticking_a_discipline_moves_it(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    scope(client, organizer, multi_day=True)
    ids = discipline_ids(client, organizer)
    ok(
        put(
            client,
            organizer,
            "days",
            [day(discipline_ids=[ids["LS"], ids["SB"]]), day("2099-12-06")],
        )
    )

    ok(
        put(
            client,
            organizer,
            "days",
            [day(discipline_ids=[ids["LS"]]), day("2099-12-06", discipline_ids=[ids["SB"]])],
        )
    )

    days = read(client, organizer)["days"]["days"]
    assert [d["discipline_ids"] for d in days] == [[ids["LS"]], [ids["SB"]]]
    twice = put(
        client,
        organizer,
        "days",
        [day(discipline_ids=[ids["SB"]]), day("2099-12-06", discipline_ids=[ids["SB"]])],
    )
    assert errors(twice) == {("1.discipline_ids.0", "two_days")}


def test_a_discipline_without_a_day_is_incomplete(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    scope(client, organizer, multi_day=True)
    ids = discipline_ids(client, organizer)
    ok(put(client, organizer, "days", [day(discipline_ids=[ids["LS"]]), day("2099-12-06")]))

    missing = summary_missing(client, organizer)

    assert f"day:{ids['SB']}" in missing
    assert f"day:{ids['LS']}" not in missing


def test_one_day_holds_every_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    ok(put(client, organizer, "days", [day(end="18:00")]))
    second = put(client, organizer, "days", [day(), day("2099-12-06")])

    (only,) = read(client, organizer)["days"]["days"]
    assert only["discipline_ids"] == [ids["LS"], ids["SB"]]
    assert errors(second) == {("days", "single_day")}


# ------------------------------------------------------------ scope


def test_two_days_cannot_become_one_by_a_tick(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    scope(client, organizer, multi_day=True)
    ok(put(client, organizer, "days", [day(), day("2099-12-06")]))

    response = put(client, organizer, "scope", {"plan_schedule": True, "multi_day": False})

    assert errors(response) == {("multi_day", "several_days")}


def test_officials_need_the_schedule(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(client, organizer, "scope", {"plan_schedule": False, "plan_officials": True})

    assert errors(response) == {("plan_officials", "needs_schedule")}
    assert read(client, organizer)["scope"] == {
        "plan_schedule": True,
        "multi_day": False,
        "plan_officials": False,
    }


def test_no_schedule_asks_only_for_formats(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    assert f"piste:{ids['LS']}" in summary_missing(client, organizer)

    ok(put(client, organizer, "scope", {"plan_schedule": False}))

    assert sorted(summary_missing(client, organizer)) == sorted(
        [f"format:{ids['LS']}", f"format:{ids['SB']}"]
    )


def test_officials_hidden_not_deleted(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    scope(client, organizer, plan_officials=True)
    ok(put(client, organizer, "officials", [official(f"R{n}") for n in range(6)]))

    scope(client, organizer, plan_officials=False)
    scope(client, organizer, plan_officials=True)

    assert [o["name"] for o in read(client, organizer)["officials"]] == [f"R{n}" for n in range(6)]


# ------------------------------------------------------------ pistes


def test_pistes_serve_disciplines_regular_or_reserve(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    pistes: list[dict] = [{"name": str(n), "serves": serving(ids["LS"])} for n in range(1, 5)]
    pistes.append({"name": "5", "serves": serving(ids["LS"], reserve=True)})
    pistes.append({"name": "6"})

    ok(put(client, organizer, "pistes", pistes))

    stored = read(client, organizer)["pistes"]
    assert [p["serves"] for p in stored[3:]] == [
        serving(ids["LS"]),
        serving(ids["LS"], reserve=True),
        [],
    ]
    missing = summary_missing(client, organizer)
    # Sabre is served by no piste; Longsword by four
    assert f"piste:{ids['SB']}" in missing
    assert f"piste:{ids['LS']}" not in missing


def test_piste_names_are_unique_and_may_swap(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ok(put(client, organizer, "pistes", [{"name": "A"}, {"name": "B"}]))
    a, b = read(client, organizer)["pistes"]

    refused = put(client, organizer, "pistes", [{"name": "A"}, {"name": "a"}])
    assert errors(refused) == {("1.name", "duplicate")}

    swapped = [{**a, "name": "B"}, {**b, "name": "A"}]
    ok(put(client, organizer, "pistes", swapped))
    assert [(p["id"], p["name"]) for p in read(client, organizer)["pistes"]] == [
        (a["id"], "B"),
        (b["id"], "A"),
    ]


def test_a_piste_serving_an_unknown_discipline_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(client, organizer, "pistes", [{"name": "1", "serves": serving(999)}])

    assert errors(response) == {("0.serves.0", "unknown_discipline")}


# ------------------------------------------------------------ formats


def test_the_advancing_count_is_always_stated(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    unsaved = read(client, organizer)["formats"][0]
    assert (unsaved["stored"], unsaved["advance"], unsaved["missing"]) == (False, None, ["format"])
    assert (unsaved["third_place"], unsaved["pause_between_pools"]) == (True, 10)
    assert (unsaved["referees_pool"], unsaved["referees_elim"]) == (1, 1)

    ok(put(client, organizer, "formats", [fmt(ids["LS"])]))

    session = db_session()
    row = session.scalars(select(FloorFormat).where(FloorFormat.discipline_id == ids["LS"])).one()
    # NULL is "all", and it is what the saved format states
    assert row.advance is None


def test_referees_differ_by_stage(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    ok(put(client, organizer, "formats", [fmt(ids["SB"], referees_pool=1, referees_elim=2)]))

    formats = {f["discipline_id"]: f for f in read(client, organizer)["formats"]}
    assert (formats[ids["SB"]]["referees_pool"], formats[ids["SB"]]["referees_elim"]) == (1, 2)
    assert formats[ids["SB"]]["missing"] == []


def test_a_format_is_refused_field_by_field(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    response = put(
        client, organizer, "formats", [fmt(ids["LS"], pool_min=8, pool_max=6, points_team_bout=5)]
    )

    assert errors(response) == {
        ("0.pool_min", "above_max"),
        ("0.points_team_bout", "individual_discipline"),
    }
    too_large = put(
        client, organizer, "formats", [fmt(ids["LS"], pool_max=11, advance=1, referees_pool=0)]
    )
    assert response.status_code == too_large.status_code == 422
    assert {e["field"] for e in too_large.json()["detail"]["errors"]} == {
        "0.pool_max",
        "0.advance",
        "0.referees_pool",
    }


def test_a_team_disciplines_format_names_both_stages(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    (team,) = read(client, organizer)["formats"]
    assert team["slot_team_match"] == 25

    missing = put(client, organizer, "formats", [fmt(ids["TM"], points_elim=10)])
    assert errors(missing) == {
        ("0.slot_team_match", "required"),
        ("0.points_elim", "team_discipline"),
    }
    ok(put(client, organizer, "formats", [fmt(ids["TM"], slot_team_match=30, points_team_bout=5)]))
    (team,) = read(client, organizer)["formats"]
    assert (team["stored"], team["slot_team_match"], team["points_team_bout"]) == (True, 30, 5)


def _second_longsword(client, organizer) -> None:
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LSW", "name": "Longsword W", "weapon": "ls", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert response.status_code in (200, 201), response.text


def test_only_the_same_weapon_is_taken_over(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    _second_longsword(client, organizer)
    ids = discipline_ids(client, organizer)

    other = put(client, organizer, "formats", [fmt(ids["LSW"], takes_pools_from=ids["SB"])])
    assert errors(other) == {("0.takes_pools_from", "other_weapon")}

    ok(put(client, organizer, "formats", [fmt(ids["LSW"], takes_pools_from=ids["LS"])]))
    formats = {f["discipline_id"]: f for f in read(client, organizer)["formats"]}
    assert formats[ids["LSW"]]["takes_pools_from"] == ids["LS"]

    chain = put(client, organizer, "formats", [fmt(ids["LS"], takes_pools_from=ids["LSW"])])
    assert errors(chain) == {("0.takes_pools_from", "source_takes_over")}


def test_a_target_held_before_its_source_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    _second_longsword(client, organizer)
    scope(client, organizer, multi_day=True)
    ids = discipline_ids(client, organizer)
    ok(
        put(
            client,
            organizer,
            "days",
            [
                day(discipline_ids=[ids["LSW"], ids["SB"]]),
                day("2099-12-06", discipline_ids=[ids["LS"]]),
            ],
        )
    )

    response = put(client, organizer, "formats", [fmt(ids["LSW"], takes_pools_from=ids["LS"])])

    assert errors(response) == {("0.takes_pools_from", "before_source")}


def test_a_slug_edit_keeps_the_format(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    ok(put(client, organizer, "formats", [fmt(ids["LS"], pool_max=6)]))

    renamed = client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"slug": "LSO", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert renamed.status_code == 200, renamed.text

    assert discipline_ids(client, organizer)["LSO"] == ids["LS"]
    formats = {f["discipline_id"]: f for f in read(client, organizer)["formats"]}
    assert (formats[ids["LS"]]["stored"], formats[ids["LS"]]["pool_max"]) == (True, 6)


def test_deleting_a_discipline_takes_its_format(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    ok(put(client, organizer, "formats", [fmt(ids["SB"])]))

    deleted = client.delete("/api/tournaments/cup/disciplines/SB", headers=organizer)

    assert deleted.status_code == 204, deleted.text
    session = db_session()
    assert session.get(Discipline, ids["SB"]) is None
    assert session.scalars(select(FloorFormat)).all() == []


# ------------------------------------------------------------ officials


def official(name: str, **overrides) -> dict:
    return {"name": name, "serves": [], "days": [], **overrides}


def test_choosing_the_fencer_names_the_official(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="j@example.com", name="Jan Novák"))
    (person,) = read(client, organizer)["persons"]

    ok(put(client, organizer, "officials", [official("", person_key=person["key"])]))

    (stored,) = read(client, organizer)["officials"]
    assert (stored["name"], stored["person_key"], stored["link_lost"]) == (
        "Jan Novák",
        person["key"],
        False,
    )
    assert stored["main"] is True


def test_a_link_whose_person_left_is_stated(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    jan = auth_headers(email="j@example.com", name="Jan Novák")
    register(client, jan)
    (person,) = read(client, organizer)["persons"]
    ok(
        put(
            client,
            organizer,
            "officials",
            [official("", person_key=person["key"], serves=serving(ids["LS"]))],
        )
    )

    cancelled = client.post("/api/tournaments/cup/my-registration/cancel", headers=jan)
    assert cancelled.status_code == 200, cancelled.text

    (stored,) = read(client, organizer)["officials"]
    assert (stored["name"], stored["serves"], stored["link_lost"]) == (
        "Jan Novák",
        serving(ids["LS"]),
        True,
    )
    # saving the section again keeps the lost link rather than refusing it
    ok(put(client, organizer, "officials", [_input(stored)]))


def _input(out: dict) -> dict:
    return {k: v for k, v in out.items() if k != "link_lost"}


def test_reserve_is_per_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)
    both = serving(ids["LS"]) + serving(ids["SB"], reserve=True)

    ok(put(client, organizer, "officials", [official("Eva", main=False, serves=both)]))

    (eva,) = read(client, organizer)["officials"]
    assert (eva["serves"], eva["main"]) == (both, False)


def test_a_new_link_to_nobody_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(
        client,
        organizer,
        "officials",
        [official("Petr", person_key="reg:999", serves=serving(999)), official("")],
    )

    assert errors(response) == {
        ("0.person_key", "unknown_person"),
        ("0.serves.0", "unknown_discipline"),
        ("1.name", "required"),
    }


# ------------------------------------------------------------ parameters


def test_parameters_read_their_defaults_and_refuse_unknown_keys(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    stored = read(client, organizer)
    assert stored["params"] == {"finals": "elimination", "min_rest_minutes": 10}
    assert stored["preferences"] == {
        "pool_size": "larger",
        "club_weight": 10,
        "nationality_weight": 3,
    }
    assert put(client, organizer, "params", {"club_weight": 2}).status_code == 422

    ok(put(client, organizer, "preferences", {"club_weight": 4, "pool_size": "smaller"}))
    ok(put(client, organizer, "params", {"finals": "tournament"}))

    stored = read(client, organizer)
    assert (stored["preferences"]["club_weight"], stored["preferences"]["pool_size"]) == (
        4,
        "smaller",
    )
    # each section keeps the other's keys
    assert stored["params"]["finals"] == "tournament"
