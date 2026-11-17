"""Officials on blocks (spec floor-officials), through the API."""

from tests.floor.test_floor_checkin import desk
from tests.floor.test_floor_plan import choose, publish, ready, variants
from tests.floor.test_floor_setup import BASE, fmt, ok, put, scope, serving


def planned(client, auth_headers) -> tuple[dict, dict]:
    """`ready`, with "Plánovat rozhodčí" on."""
    organizer, ids = ready(client, auth_headers)
    scope(client, organizer, plan_officials=True)
    return organizer, ids


def staffed(client, auth_headers, names: list[str], *, referees: int = 1, main: bool = True):
    """Ten Longsword fencers on a published plan, with these referees."""
    organizer, ids = planned(client, auth_headers)
    officials = [official(n, ids, main=main) for n in names]
    ok(
        put(
            client,
            organizer,
            "formats",
            [
                fmt(ids["LS"], pool_min=5, pool_max=5, referees_pool=referees),
                fmt(ids["SB"], pool_min=5, pool_max=5, referees_pool=referees),
            ],
        )
    )
    ok(put(client, organizer, "officials", officials))
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))
    return organizer, ids


def official(name: str, ids: dict, **extra) -> dict:
    return {
        "name": name,
        "serves": serving(ids["LS"], ids["SB"]),
        "days": ["2099-12-05"],
        **extra,
    }


def assignments(client, headers) -> dict:
    response = client.get(f"{BASE}/officials", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def seats(body: dict) -> list[dict]:
    return [seat | {"block": block} for block in body["blocks"] for seat in block["seats"]]


def test_publishing_assigns_every_block(client, auth_headers):
    organizer, ids = planned(client, auth_headers)
    names = ["Eva", "Filip", "Gita", "Hana"]
    ok(put(client, organizer, "officials", [official(n, ids) for n in names]))
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))

    body = assignments(client, organizer)

    assert body["published"] is True
    assert body["blocks"] and all(s["name"] in names for s in seats(body))


def test_an_official_who_fences_is_kept_off_their_discipline(client, auth_headers):
    organizer, ids = planned(client, auth_headers)
    fencer = desk(client, organizer)["persons"][0]["key"]
    ok(
        put(
            client,
            organizer,
            "officials",
            [official("Jan", ids, person_key=fencer), official("Eva", ids)],
        )
    )
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))

    names = {
        s["name"]
        for s in seats(assignments(client, organizer))
        if s["block"]["discipline_id"] == ids["LS"]
    }

    assert "Jan" not in names


def test_an_unfillable_place_is_stated_and_badged(client, auth_headers):
    organizer, ids = staffed(client, auth_headers, ["Eva", "Filip"], referees=2)
    # Filip drops out after publication
    ok(put(client, organizer, "officials", [official("Eva", ids)]))
    ok(client.post(f"{BASE}/officials/run", headers=organizer))

    body = assignments(client, organizer)
    summary = client.get(f"{BASE}/summary", headers=organizer).json()

    # one referee for two places a pool: every second place stays empty, stated
    second = [s for s in seats(body) if s["slot"] == 1]
    assert second and all(s["official_id"] is None for s in second)
    assert summary["badges"]["plan"] is True


def test_no_main_referee_is_tolerated_and_badged(client, auth_headers):
    organizer, _ = staffed(client, auth_headers, ["Petr"], main=False)

    body = assignments(client, organizer)
    today = client.get(f"{BASE}/today", headers=organizer).json()

    assert body["blocks"] and all(b["without_main"] for b in body["blocks"])
    assert all(s["official_id"] is not None for s in seats(body))
    assert {"tab": "plan", "discipline": None, "code": "without_main"} in today["waiting"]


def test_no_officials_no_assignment(client, auth_headers):
    organizer, ids = ready(client, auth_headers)
    ok(put(client, organizer, "officials", [official("Eva", ids)]))
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))

    body = assignments(client, organizer)

    assert (body["published"], body["blocks"]) == (False, [])


def test_a_pin_survives_a_rerun_and_a_swap_names_the_broken_rule(client, auth_headers):
    organizer, ids = planned(client, auth_headers)
    ok(
        put(
            client,
            organizer,
            "officials",
            [
                official("Eva", ids),
                official("Filip", ids),
                official("Gita", ids, serves=serving(ids["SB"])),
            ],
        )
    )
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))
    eva = next(
        o["id"]
        for o in client.get(f"{BASE}/setup", headers=organizer).json()["officials"]
        if o["name"] == "Eva"
    )
    first = seats(assignments(client, organizer))[0]

    ok(
        client.put(
            f"{BASE}/officials/seats/{first['id']}",
            json={"official_id": eva, "pinned": True},
            headers=organizer,
        )
    )
    ok(client.post(f"{BASE}/officials/run", headers=organizer))
    again = next(
        s
        for s in seats(assignments(client, organizer))
        if s["block"]["key"] == first["block"]["key"] and s["role"] == first["role"]
    )
    gita = next(
        o["id"]
        for o in client.get(f"{BASE}/setup", headers=organizer).json()["officials"]
        if o["name"] == "Gita"
    )
    refused = client.put(
        f"{BASE}/officials/seats/{again['id']}",
        json={"official_id": gita, "pinned": False},
        headers=organizer,
    )

    assert (again["name"], again["pinned"]) == ("Eva", True)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "not_qualified"


def test_an_officials_rozpis_prints(client, auth_headers):
    organizer, _ = staffed(client, auth_headers, ["Eva"])
    eva = client.get(f"{BASE}/setup", headers=organizer).json()["officials"][0]["id"]

    response = client.get(f"{BASE}/officials/print/official/{eva}", headers=organizer)

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
