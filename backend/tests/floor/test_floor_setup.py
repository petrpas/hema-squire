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
        "staffing": {"referee": 1},
        "slot_pool_bout": 4,
        "slot_elim_bout": 6,
        "slot_pool_overhead": 5,
        **overrides,
    }


def discipline_ids(client, headers) -> dict[str, int]:
    return {d["slug"]: d["id"] for d in read(client, headers)["disciplines"]}


# ------------------------------------------------------------ days


def test_the_default_day(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    days = read(client, organizer)["days"]

    assert days == {
        "stored": False,
        "days": [{"date": "2099-12-05", "start": "09:00", "end": "19:00", "breaks": []}],
    }


def test_a_break_outside_the_day_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(
        client,
        organizer,
        "days",
        [
            {
                "date": "2099-12-05",
                "start": "09:00",
                "end": "18:00",
                "breaks": [{"start": "18:30", "end": "19:00"}],
            }
        ],
    )

    assert errors(response) == {("0.breaks.0", "break_outside_day")}
    assert read(client, organizer)["days"]["stored"] is False


def test_overlapping_breaks_and_a_backwards_day_are_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    day = {"date": "2099-12-05", "start": "09:00", "end": "18:00"}

    response = put(
        client,
        organizer,
        "days",
        [
            {
                **day,
                "breaks": [{"start": "12:00", "end": "13:00"}, {"start": "12:30", "end": "13:30"}],
            },
            {**day, "date": "2099-12-06", "start": "18:00", "end": "09:00"},
        ],
    )

    assert errors(response) == {("0.breaks.1", "breaks_overlap"), ("1.end", "end_not_after_start")}


def test_dropping_a_day_drops_availability_on_it(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    two = [
        {"date": "2099-12-05", "start": "09:00", "end": "19:00"},
        {"date": "2099-12-06", "start": "09:00", "end": "17:00"},
    ]
    ok(put(client, organizer, "days", two))
    ok(put(client, organizer, "pistes", [{"name": "1", "days": ["2099-12-05", "2099-12-06"]}]))

    ok(put(client, organizer, "days", two[:1]))

    (piste,) = read(client, organizer)["pistes"]
    assert piste["days"] == ["2099-12-05"]


# ------------------------------------------------------------ pistes


def test_a_reserve_piste_is_kept_back(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    day = ["2099-12-05"]
    pistes = [{"name": str(n), "days": day} for n in range(1, 5)]
    pistes.append({"name": "5", "days": day, "reserve": True, "tag": "finálová"})

    # no day was saved: naming the offered one stores it
    ok(put(client, organizer, "pistes", pistes))

    stored = read(client, organizer)
    assert stored["days"]["stored"] is True
    assert [(p["name"], p["reserve"]) for p in stored["pistes"]] == [
        ("1", False),
        ("2", False),
        ("3", False),
        ("4", False),
        ("5", True),
    ]
    assert stored["pistes"][4]["tag"] == "finálová"


def test_piste_names_are_unique_and_may_swap(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    day = ["2099-12-05"]
    ok(put(client, organizer, "pistes", [{"name": "A", "days": day}, {"name": "B", "days": day}]))
    a, b = read(client, organizer)["pistes"]

    refused = put(
        client, organizer, "pistes", [{"name": "A", "days": day}, {"name": "a", "days": day}]
    )
    assert errors(refused) == {("1.name", "duplicate")}

    swapped = [{**a, "name": "B"}, {**b, "name": "A"}]
    ok(put(client, organizer, "pistes", swapped))
    assert [(p["id"], p["name"]) for p in read(client, organizer)["pistes"]] == [
        (a["id"], "B"),
        (b["id"], "A"),
    ]


def test_a_piste_on_an_unknown_day_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(client, organizer, "pistes", [{"name": "1", "days": ["2099-12-24"]}])

    assert errors(response) == {("0.days.0", "unknown_day")}


# ------------------------------------------------------------ formats


def test_the_advancing_count_is_always_stated(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    unsaved = read(client, organizer)["formats"][0]
    assert (unsaved["stored"], unsaved["advance"], unsaved["missing"]) == (False, None, ["format"])

    ok(put(client, organizer, "formats", [fmt(ids["LS"])]))

    session = db_session()
    row = session.scalars(select(FloorFormat).where(FloorFormat.discipline_id == ids["LS"])).one()
    # NULL is "all", and it is what the saved format states
    assert row.advance is None


def test_staffing_differs_by_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    ok(
        put(
            client,
            organizer,
            "formats",
            [
                fmt(ids["LS"], staffing={"referee": 1}),
                fmt(ids["SB"], staffing={"referee": 1, "judge": 1}),
            ],
        )
    )

    formats = {f["discipline_id"]: f for f in read(client, organizer)["formats"]}
    assert formats[ids["LS"]]["staffing"] == {"referee": 1, "judge": 0, "table": 0}
    assert formats[ids["SB"]]["staffing"] == {"referee": 1, "judge": 1, "table": 0}
    assert all(f["missing"] == [] for f in formats.values())


def test_staffing_is_never_assumed(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    ok(put(client, organizer, "formats", [fmt(ids["LS"], staffing=None)]))

    formats = {f["discipline_id"]: f for f in read(client, organizer)["formats"]}
    assert formats[ids["LS"]]["missing"] == ["staffing"]
    summary = client.get(f"{BASE}/summary", headers=organizer).json()
    assert summary["badges"]["setup"] is True
    assert f"staffing:{ids['LS']}" in summary["setup_missing"]


def test_a_format_is_refused_field_by_field(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    response = put(
        client,
        organizer,
        "formats",
        [fmt(ids["LS"], pool_min=8, pool_max=6, staffing={"referee": 0, "judge": 2})],
    )

    assert errors(response) == {
        ("0.pool_min", "above_max"),
        ("0.staffing.referee", "referee_required"),
    }
    too_large = put(client, organizer, "formats", [fmt(ids["LS"], pool_max=11, advance=1)])
    assert response.status_code == too_large.status_code == 422
    assert {e["field"] for e in too_large.json()["detail"]["errors"]} == {"0.pool_max", "0.advance"}


def test_a_team_disciplines_format_names_both_stages(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    ids = discipline_ids(client, organizer)

    (team,) = read(client, organizer)["formats"]
    assert team["slot_team_match"] == 25

    missing = put(client, organizer, "formats", [fmt(ids["TM"])])
    assert errors(missing) == {("0.slot_team_match", "required")}
    ok(put(client, organizer, "formats", [fmt(ids["TM"], slot_team_match=30)]))
    (team,) = read(client, organizer)["formats"]
    assert (team["stored"], team["slot_team_match"]) == (True, 30)


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
    return {"name": name, "roles": ["referee"], "discipline_ids": [], "days": [], **overrides}


def test_an_official_who_fences_is_one_person(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="j@example.com", name="Jan Novák"))
    (person,) = read(client, organizer)["persons"]

    ok(put(client, organizer, "officials", [official("Jan Novák", person_key=person["key"])]))

    (stored,) = read(client, organizer)["officials"]
    assert (stored["person_key"], stored["link_lost"]) == (person["key"], False)


def test_a_link_whose_person_left_is_stated(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    jan = auth_headers(email="j@example.com", name="Jan Novák")
    register(client, jan)
    (person,) = read(client, organizer)["persons"]
    ok(
        put(
            client,
            organizer,
            "officials",
            [official("Jan Novák", person_key=person["key"], roles=["referee", "judge"])],
        )
    )

    cancelled = client.post("/api/tournaments/cup/my-registration/cancel", headers=jan)
    assert cancelled.status_code == 200, cancelled.text

    (stored,) = read(client, organizer)["officials"]
    assert (stored["name"], stored["roles"], stored["link_lost"]) == (
        "Jan Novák",
        ["judge", "referee"],
        True,
    )
    # saving the section again keeps the lost link rather than refusing it
    ok(put(client, organizer, "officials", [_input(stored)]))


def _input(out: dict) -> dict:
    return {k: v for k, v in out.items() if k != "link_lost"}


def test_a_new_link_to_nobody_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put(
        client,
        organizer,
        "officials",
        [official("Petr", person_key="reg:999", roles=[], discipline_ids=[999])],
    )

    assert errors(response) == {
        ("0.person_key", "unknown_person"),
        ("0.roles", "required"),
        ("0.discipline_ids.0", "unknown_discipline"),
    }


# ------------------------------------------------------------ parameters


def test_parameters_read_their_defaults_and_refuse_unknown_keys(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    assert read(client, organizer)["params"] == {
        "finals_last": True,
        "prefer_larger_pools": True,
        "club_weight": 10,
        "nationality_weight": 3,
        "min_rest_minutes": 10,
    }
    assert put(client, organizer, "params", {"pool_spread": 2}).status_code == 422

    ok(put(client, organizer, "params", {"club_weight": 4}))
    params = read(client, organizer)["params"]
    assert (params["club_weight"], params["nationality_weight"]) == (4, 3)
