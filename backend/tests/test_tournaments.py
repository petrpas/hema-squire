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
        "organizers": [
            {"name": "Duelanti od sv. Rocha", "link": "https://duelanti.example"},
            {"name": "Klub X", "link": None},
        ],
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
    assert body["organizers"] == [
        {"name": "Duelanti od sv. Rocha", "link": "https://duelanti.example"},
        {"name": "Klub X", "link": None},
    ]
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


def test_generic_extra_categories_persist_and_reload(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    for category in ("other_action", "other_item"):
        row = client.post(
            "/api/tournaments/na-duel-2026/extra-items",
            json={"name": category, "category": category, "price": 100, "max_qty": 1},
            headers=headers,
        )
        assert row.status_code == 201, row.text
        assert row.json()["category"] == category

    reloaded = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    categories = {i["category"] for i in reloaded["extra_items"]}
    assert {"other_action", "other_item"} <= categories


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


def test_qualification_requires_criteria_when_not_open(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    rejected = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"qualification_open": False, "qualification_criteria": ""},
        headers=headers,
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == "qualification_criteria_required"

    accepted = client.patch(
        "/api/tournaments/na-duel-2026",
        json={
            "qualification_open": False,
            "qualification_criteria": "national championship placement",
        },
        headers=headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["qualification_criteria"] == "national championship placement"

    reopened = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"qualification_open": True},
        headers=headers,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["qualification_open"] is True
    assert reopened.json()["qualification_criteria"] is None


def test_extra_item_action_category_forces_max_qty_one(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    created = client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={"name": "afterparty", "category": "afterparty", "price": 200, "max_qty": 5},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["max_qty"] == 1


def test_extra_item_item_category_rejects_schedule_fields(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={
            "name": "t-shirt",
            "category": "merch",
            "price": 300,
            "schedule_when": "Saturday",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "schedule_fields_not_allowed_for_item_category"


def test_legacy_action_row_keeps_max_qty_until_resaved(client, auth_headers, engine):
    """A pre-existing action-category row with max_qty > 1 (from before this
    change) is left untouched on read, and only normalized to 1 on next save
    (design D4)."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import ExtraItem, Tournament

    headers = auth_headers()
    make_tournament(client, headers)

    with Session(engine) as session:
        tournament = session.scalars(
            select(Tournament).where(Tournament.slug == "na-duel-2026")
        ).one()
        legacy = ExtraItem(
            tournament_id=tournament.id,
            name="legacy afterparty",
            category="afterparty",
            price=150,
            max_qty=5,
        )
        session.add(legacy)
        session.commit()
        legacy_id = legacy.id

    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    row = next(i for i in detail["extra_items"] if i["id"] == legacy_id)
    assert row["max_qty"] == 5

    updated = client.patch(
        f"/api/tournaments/na-duel-2026/extra-items/{legacy_id}",
        json={
            "name": "legacy afterparty",
            "category": "afterparty",
            "price": 150,
            "max_qty": 5,
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["max_qty"] == 1


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


def test_reminder_day_at_or_after_validity_rejected(client, auth_headers):
    """Expiry runs before reminders, so a reminder day at or beyond the
    validity period would never fire (design harden-payment-matching
    Decision 8)."""
    headers = auth_headers()
    make_tournament(client, headers)

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 10, "reminder_day": 10},
        headers=headers,
    )
    assert response.status_code == 422
    assert "reminder_day" in response.json()["detail"]
    assert "reservation_validity_days" in response.json()["detail"]


def test_reminder_day_shortened_validity_rejected(client, auth_headers):
    """The same check fires from either side of the edit: shortening the
    validity below an existing, previously-valid reminder day."""
    headers = auth_headers()
    make_tournament(client, headers)
    assert client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 10, "reminder_day": 7},
        headers=headers,
    ).status_code == 200

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 5},
        headers=headers,
    )
    assert response.status_code == 422


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
