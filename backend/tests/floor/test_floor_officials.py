"""Officials on blocks (spec floor-officials), through the API."""

from tests.floor.test_floor_checkin import desk
from tests.floor.test_floor_plan import choose, publish, ready, variants
from tests.floor.test_floor_setup import BASE, fmt, ok, put


def staffed(client, auth_headers, officials: list[dict], *, judge: int = 0):
    """Ten Longsword fencers on a published plan, with these officials."""
    organizer, ids = ready(client, auth_headers)
    staffing = {"referee": 1, "judge": judge}
    ok(
        put(
            client,
            organizer,
            "formats",
            [
                fmt(ids["LS"], pool_min=5, pool_max=5, staffing=staffing),
                fmt(ids["SB"], pool_min=5, pool_max=5, staffing=staffing),
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
        "roles": ["referee"],
        "discipline_ids": [ids["LS"], ids["SB"]],
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
    organizer, ids = ready(client, auth_headers)
    names = ["Eva", "Filip", "Gita", "Hana"]
    ok(put(client, organizer, "officials", [official(n, ids) for n in names]))
    choose(client, organizer, variants(client, organizer)["variants"][0]["key"])
    ok(publish(client, organizer))

    body = assignments(client, organizer)

    assert body["published"] is True
    assert body["blocks"] and all(s["name"] in names for s in seats(body))


def test_an_official_who_fences_is_kept_off_their_discipline(client, auth_headers):
    organizer, ids = ready(client, auth_headers)
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


def test_an_unfillable_role_is_stated_and_badged(client, auth_headers):
    organizer, ids = staffed(client, auth_headers, [], judge=1)
    organizer_officials = [official("Eva", ids)]
    ok(put(client, organizer, "officials", organizer_officials))
    ok(client.post(f"{BASE}/officials/run", headers=organizer))

    body = assignments(client, organizer)
    summary = client.get(f"{BASE}/summary", headers=organizer).json()

    # nobody can judge: every judge seat stays empty, and it is stated
    judges = [s for s in seats(body) if s["role"] == "judge"]
    assert judges and all(s["official_id"] is None for s in judges)
    assert summary["badges"]["plan"] is True


def test_a_pin_survives_a_rerun_and_a_swap_names_the_broken_rule(client, auth_headers):
    organizer, ids = ready(client, auth_headers)
    ok(
        put(
            client,
            organizer,
            "officials",
            [
                official("Eva", ids),
                official("Filip", ids),
                official("Gita", ids, discipline_ids=[ids["SB"]]),
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
    organizer, ids = staffed(client, auth_headers, [])
    ok(put(client, organizer, "officials", [official("Eva", ids)]))
    ok(client.post(f"{BASE}/officials/run", headers=organizer))
    eva = client.get(f"{BASE}/setup", headers=organizer).json()["officials"][0]["id"]

    response = client.get(f"{BASE}/officials/print/official/{eva}", headers=organizer)

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
