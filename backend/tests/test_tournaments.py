def make_tournament(client, headers, slug="na-duel-2026"):
    response = client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Na Duel!", "date": "2026-10-03"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_signup_login_roundtrip(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "a@example.com", "password": "secret-123", "display_name": "A"},
    )
    assert signup.status_code == 201
    login = client.post(
        "/api/auth/login", json={"email": "a@example.com", "password": "secret-123"}
    )
    assert login.status_code == 200
    bad = client.post(
        "/api/auth/login", json={"email": "a@example.com", "password": "wrong-pass"}
    )
    assert bad.status_code == 401


def test_create_tournament_requires_auth(client):
    response = client.post(
        "/api/tournaments",
        json={"slug": "x-cup", "display_name": "X", "date": "2026-01-01"},
    )
    assert response.status_code == 401


def test_creator_becomes_organizer_and_can_configure(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    response = client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"code": "LS", "capacity": 32, "fee": 800},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Longsword Open"

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 10, "reminder_day": 5},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["reservation_validity_days"] == 10


def test_non_organizer_cannot_administer(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    intruder = auth_headers(email="other@example.com", name="Other")

    response = client.patch(
        "/api/tournaments/na-duel-2026", json={"display_name": "Hacked"}, headers=intruder
    )
    assert response.status_code == 403

    response = client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"code": "SB", "capacity": 16, "fee": 500},
        headers=intruder,
    )
    assert response.status_code == 403


def test_unknown_discipline_code_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"code": "XX", "capacity": 8, "fee": 100},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "unknown_discipline_code"


def test_taxonomy_codes(client):
    taxonomy = client.get("/api/taxonomy/disciplines").json()
    assert taxonomy["LS"] == "Longsword Open"
    assert taxonomy["SAW"] == "Sabre Women"
    assert taxonomy["Plastic LSM"] == "Longsword Men (Plastic)"
    assert len(taxonomy) == 30


def test_added_organizer_gains_access(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    helper = auth_headers(email="helper@example.com", name="Helper")

    response = client.post(
        "/api/tournaments/na-duel-2026/organizers",
        json={"email": "helper@example.com"},
        headers=organizer,
    )
    assert response.status_code == 201

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"display_name": "Na Duel! 2026"},
        headers=helper,
    )
    assert response.status_code == 200


def test_public_can_read_but_not_write(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"code": "SA", "capacity": 42, "fee": 700, "fee_early": 600},
        headers=headers,
    )

    listing = client.get("/api/tournaments")
    assert listing.status_code == 200
    assert listing.json()[0]["slug"] == "na-duel-2026"

    detail = client.get("/api/tournaments/na-duel-2026")
    assert detail.status_code == 200
    assert detail.json()["disciplines"][0]["fee_early"] == 600
