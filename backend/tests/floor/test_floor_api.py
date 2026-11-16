"""`GET /api/tournaments/{slug}/floor/roster` (spec floor-roster, The organizer
reads the floor roster from the console): the router mounts, the console gate
applies, the roster serializes."""

from tests.test_entrants import register, setup_tournament

URL = "/api/tournaments/cup/floor/roster"


def test_an_organizer_reads_the_roster(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("LS", "SB"))

    response = client.get(URL, headers=organizer)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [(d["slug"], d["kind"]) for d in body["disciplines"]] == [
        ("LS", "individual"),
        ("SB", "individual"),
    ]
    (person,) = body["persons"]
    assert person["name"] == "Adéla"
    assert {(e["person"], e["discipline"], e["paid"]) for e in body["individuals"]} == {
        (person["key"], "LS", False),
        (person["key"], "SB", False),
    }
    assert body["teams"] == []


def test_a_stranger_is_refused(client, auth_headers):
    setup_tournament(client, auth_headers())
    stranger = auth_headers(email="z@example.com", name="Zdeněk")

    assert client.get(URL, headers=stranger).status_code == 403


def test_an_unknown_tournament_is_not_found(client, auth_headers):
    response = client.get("/api/tournaments/nowhere/floor/roster", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "tournament_not_found"


def test_a_draft_is_refused(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )

    assert client.get(URL, headers=organizer).status_code == 409
