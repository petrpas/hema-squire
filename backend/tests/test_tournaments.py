from app.models import Role
from tests.conftest import publish


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
    bad = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-pass"})
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
    assert response.json()["detail"] == {
        "errors": [{"field": "slug", "code": "slug_taken", "params": {}}]
    }


def test_setup_fields_patch_round_trip_and_detail(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    patch = {
        "city": "Brno",
        "address": "[Sportovní hala](https://osm.org/go/0J0ajlLg8?m=)",
        "organizers": [
            {"name": "Duelanti od sv. Rocha", "link": "https://duelanti.example"},
            {"name": "Klub X", "link": None},
        ],
        "registration_opens": "2026-01-01",
        "registration_closes": "2026-09-01",
        "bank_account": "CZ6508000000192000145399",
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
    assert body["city"] == "Brno"
    assert body["address"] == "[Sportovní hala](https://osm.org/go/0J0ajlLg8?m=)"
    assert body["organizers"] == [
        {"name": "Duelanti od sv. Rocha", "link": "https://duelanti.example"},
        {"name": "Klub X", "link": None},
    ]
    assert body["registration_opens"] == "2026-01-01"
    assert body["registration_closes"] == "2026-09-01"
    # scope defaults to ["discipline"] when omitted (invariant: don't normalize stored data)
    assert body["discounts"][0]["scope"] == ["discipline"]

    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert detail["city"] == "Brno"
    assert detail["address"] == "[Sportovní hala](https://osm.org/go/0J0ajlLg8?m=)"
    # setup still incomplete: no disciplines yet
    assert "disciplines" in detail["setup_missing"]

    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
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
    assert rejected.json()["detail"] == {
        "errors": [
            {
                "field": "qualification_criteria",
                "code": "qualification_criteria_required",
                "params": {},
            }
        ]
    }

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
        json={"slug": "LS", "weapon": "LS", "capacity": 32, "fee": 800},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Longsword Open"

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 7, "reminder_day": 5},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["reservation_validity_days"] == 7


def test_reminder_day_at_or_after_validity_rejected(client, auth_headers):
    """Expiry runs before reminders, so a reminder day at or beyond the
    validity period would never fire (design harden-payment-matching
    Decision 8)."""
    headers = auth_headers()
    make_tournament(client, headers)

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 5, "reminder_day": 5},
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
    assert (
        client.patch(
            "/api/tournaments/na-duel-2026",
            json={"reservation_validity_days": 7, "reminder_day": 6},
            headers=headers,
        ).status_code
        == 200
    )

    response = client.patch(
        "/api/tournaments/na-duel-2026",
        json={"reservation_validity_days": 4},
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
        json={"slug": "SB", "weapon": "SB", "capacity": 16, "fee": 500},
        headers=intruder,
    )
    assert response.status_code == 403


def test_custom_weapon_without_name_rejected(client, auth_headers):
    # Creation no longer checks a closed taxonomy of weapon codes; any
    # `weapon` string is accepted, but a non-taxonomy weapon requires an
    # explicit `name` (design discipline-identity D4).
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "XX", "weapon": "XX", "capacity": 8, "fee": 100},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "errors": [{"field": "name", "code": "discipline_name_required", "params": {}}]
    }


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
    """What a visitor with no credential may read of a tournament.

    Narrowed by `public-tournament-list`: the organizer's index and the
    console's full payload used to answer anybody who asked, which handed out
    every draft and every bank account on the deployment. The public surfaces
    are the fencer-facing ones, and a published tournament's prices are among
    what they carry (spec `public-browsing`)."""
    headers = auth_headers()
    make_tournament(client, headers)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 42, "fee": 700, "fee_early": 600},
        headers=headers,
    )
    publish(client, headers, "na-duel-2026")

    assert client.get("/api/tournaments").status_code == 401
    assert client.get("/api/tournaments/na-duel-2026").status_code == 401

    detail = client.get("/api/tournaments/na-duel-2026/public")
    assert detail.status_code == 200
    assert detail.json()["disciplines"][0]["fee_early"] == 600


def test_tournament_update_refuses_to_null_a_required_field(client, auth_headers):
    """Omitting a field leaves it alone; nulling one is refused.

    The handler writes whatever the request *set*, and `exclude_unset` cannot
    tell an omitted field from an explicit null — so a null reached a NOT NULL
    column and the request answered 500 on an integrity error. Nineteen
    patchable fields had the hole; the contract fuzzer reached one of them
    (static-analysis change, phase 4). `TournamentUpdate` derives the refusal
    from the table, so a column that becomes NOT NULL is covered without anyone
    remembering to.
    """
    headers = auth_headers()
    make_tournament(client, headers)
    refused = client.patch(
        "/api/tournaments/na-duel-2026", json={"afterparty_fee": None}, headers=headers
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["errors"] == [
        {"field": "afterparty_fee", "code": "required", "params": {}}
    ]
    # a nullable column still clears
    cleared = client.patch(
        "/api/tournaments/na-duel-2026", json={"subtitle": None}, headers=headers
    )
    assert cleared.status_code == 200


def test_discipline_delete_refuses_once_a_registration_references_it(client, auth_headers):
    """The edit path already refuses to change a referenced discipline's
    identity; deleting it outright was not refused at all and failed on the
    foreign key as a 500 (found by the contract fuzzer)."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 4, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, "na-duel-2026")
    fencer = auth_headers(email="f1@example.com", name="F1", role=Role.FENCER)
    entered = client.post(
        "/api/tournaments/na-duel-2026/register",
        json={"disciplines": ["LS"]},
        headers=fencer,
    )
    assert entered.status_code == 201, entered.text

    refused = client.delete("/api/tournaments/na-duel-2026/disciplines/LS", headers=organizer)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "discipline_referenced"
