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


def test_slug_collision_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments",
        json={"slug": "na-duel-2026", "display_name": "Other", "date": "2027-01-01"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "slug_taken"


def test_setup_fields_patch_round_trip_and_detail(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    patch = {
        "location": "Brno, Sportovní hala",
        "organizer_names": ["Duelanti od sv. Rocha", "Klub X"],
        "registration_opens": "2026-01-01",
        "registration_closes": "2026-09-01",
        "discounts": [
            {
                "name": "2 disciplines",
                "condition": {"kind": "discipline_count", "count": 2},
                "effect": {"kind": "fixed", "value": 10},
            }
        ],
    }
    response = client.patch("/api/tournaments/na-duel-2026", json=patch, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["location"] == "Brno, Sportovní hala"
    assert body["organizer_names"] == ["Duelanti od sv. Rocha", "Klub X"]
    assert body["registration_opens"] == "2026-01-01"
    assert body["registration_closes"] == "2026-09-01"
    # scope defaults to ["discipline"] when omitted (invariant: don't normalize stored data)
    assert body["discounts"][0]["scope"] == ["discipline"]

    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert detail["location"] == "Brno, Sportovní hala"
    # setup still incomplete: no disciplines yet
    assert "disciplines" in detail["setup_missing"]

    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 800},
        headers=headers,
    )
    complete = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert complete["setup_missing"] == []


def test_extra_item_crud(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    created = client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={"name": "weapon rental", "category": "rental", "price": 200, "max_qty": 4},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["name"] == "weapon rental"

    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert detail["extra_items"] == [item]

    updated = client.patch(
        f"/api/tournaments/na-duel-2026/extra-items/{item['id']}",
        json={"name": "weapon rental", "category": "rental", "price": 250, "max_qty": 4},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 250

    deleted = client.delete(
        f"/api/tournaments/na-duel-2026/extra-items/{item['id']}", headers=headers
    )
    assert deleted.status_code == 204
    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert detail["extra_items"] == []


def test_extra_item_requires_organizer(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    intruder = auth_headers(email="other@example.com", name="Other")
    response = client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={"name": "t-shirt", "category": "merch", "price": 300},
        headers=intruder,
    )
    assert response.status_code == 403


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
        "/api/tournaments/na-duel-2026/team",
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
