from datetime import date, timedelta

TODAY = date.today()


def setup_tournament(client, organizer, early_bird=False):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    patch = {
        "weapon_rental_fee": 200,
        "afterparty_fee": 300,
        "refundable_until": "2026-11-01",
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
    }
    if early_bird:
        patch |= {
            "early_bird_until": str(TODAY + timedelta(days=7)),
            "weapon_rental_fee_early": 150,
            "afterparty_fee_early": 250,
        }
    client.patch("/api/tournaments/cup", json=patch, headers=organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": 2, "fee": 800, "fee_early": 600},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "SB", "capacity": 1, "fee": 500},
        headers=organizer,
    )


def register(client, headers, **overrides):
    payload = {"disciplines": ["LS"], **overrides}
    return client.post("/api/tournaments/cup/register", json=payload, headers=headers)


def test_registration_computes_total_and_assigns_vs(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(
        client, fencer, disciplines=["LS", "SB"], weapon_rentals=["LS"], afterparty=True
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == 800 + 500 + 200 + 300
    assert body["vs"] == 1000001
    assert body["state"] == "reserved"
    assert body["expires_at"] is not None
    assert all(not e["is_substitute"] for e in body["entries"])

    second = auth_headers(email="f2@example.com", name="F2")
    assert register(client, second).json()["vs"] == 1000002


def test_early_bird_prices_apply(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, early_bird=True)
    fencer = auth_headers(email="f1@example.com", name="F1")

    body = register(
        client, fencer, disciplines=["LS"], weapon_rentals=["LS"], afterparty=True
    ).json()
    assert body["total_amount"] == 600 + 150 + 250


def test_double_registration_rejected(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer)
    assert register(client, fencer).status_code == 409


def test_full_discipline_forces_choice(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="A"), disciplines=["SB"])

    late = auth_headers(email="b@example.com", name="B")
    response = register(client, late, disciplines=["LS", "SB"])
    assert response.status_code == 409
    assert response.json()["detail"] == {"full_disciplines": ["SB"]}

    trimmed = register(client, late, disciplines=["LS"])
    assert trimmed.status_code == 201


def test_wait_for_all_queues_everything_unbilled(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="A"), disciplines=["SB"])

    waiting = auth_headers(email="b@example.com", name="B")
    body = register(
        client, waiting, disciplines=["LS", "SB"], afterparty=True, wait_for_all=True
    ).json()
    assert all(e["is_substitute"] for e in body["entries"])
    assert body["total_amount"] == 0
    assert body["expires_at"] is None
    sb_entry = next(e for e in body["entries"] if e["code"] == "SB")
    assert sb_entry["queue_position"] == 1

    availability = client.get("/api/tournaments/cup/availability").json()
    sb = next(a for a in availability if a["code"] == "SB")
    assert sb == {"code": "SB", "capacity": 1, "taken": 1, "free": 0, "queue_length": 1}


def test_cancel_frees_spot_and_admit_bills_frozen_prices(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    first = auth_headers(email="a@example.com", name="A")
    register(client, first, disciplines=["SB"])

    waiting = auth_headers(email="b@example.com", name="B")
    waiting_body = register(
        client, waiting, disciplines=["SB"], afterparty=True, wait_for_all=True
    ).json()
    assert waiting_body["total_amount"] == 0

    cancelled = client.post("/api/tournaments/cup/my-registration/cancel", headers=first)
    assert cancelled.json()["state"] == "cancelled"

    my = client.get("/api/tournaments/cup/my-registration", headers=waiting).json()
    registration_id = None  # admit needs the id; fetch via organizer-side lookup below

    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Registration, RegistrationState

    session = next(app.dependency_overrides[get_session]())
    registration_id = session.scalar(
        select(Registration.id).where(Registration.state == RegistrationState.RESERVED)
    )

    admitted = client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/admit/SB", headers=organizer
    )
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["entries"][0]["is_substitute"] is False
    assert body["total_amount"] == 500 + 300  # SB fee + afterparty, frozen prices
    assert body["expires_at"] is not None
    assert my["state"] == "reserved"


def test_price_preview_matches_registration_total_legacy(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")

    selection = {
        "disciplines": ["LS", "SB"],
        "weapon_rentals": ["LS"],
        "afterparty": True,
    }
    preview = client.post(
        "/api/tournaments/cup/price-preview", json=selection, headers=fencer
    )
    assert preview.status_code == 200
    registered = register(client, fencer, **selection).json()
    assert preview.json()["total"] == registered["total_amount"]


def test_price_preview_matches_registration_total_itemized(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "T-shirt", "category": "merch", "price": 250, "max_qty": 2},
        headers=organizer,
    ).json()
    client.patch(
        "/api/tournaments/cup",
        json={
            "discounts": [
                {
                    "name": "2 disciplines",
                    "condition": {"kind": "discipline_count", "count": 2},
                    "effect": {"kind": "fixed", "value": 100},
                    "scope": ["discipline"],
                }
            ]
        },
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")

    selection = {
        "disciplines": ["LS", "SB"],
        "extras": [{"extra_item_id": item["id"], "qty": 2}],
    }
    preview = client.post(
        "/api/tournaments/cup/price-preview", json=selection, headers=fencer
    )
    assert preview.status_code == 200
    registered = register(client, fencer, **selection).json()
    assert preview.json()["total"] == registered["total_amount"]
    assert preview.json()["total"] == (800 + 500 - 100) + 2 * 250


def test_price_preview_rejects_unknown_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = client.post(
        "/api/tournaments/cup/price-preview",
        json={"disciplines": ["ZZ"]},
        headers=fencer,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"unknown_disciplines": ["ZZ"]}


def test_cancel_then_reregister_reuses_the_slot(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    first = register(client, fencer, disciplines=["LS"]).json()

    cancelled = client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)
    assert cancelled.json()["state"] == "cancelled"

    second = register(client, fencer, disciplines=["SB"])
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["state"] == "reserved"
    assert body["entries"][0]["code"] == "SB"
    assert body["vs"] != first["vs"]


IBAN = "CZ6508000000192000145399"


def test_payment_instructions_return_amount_iban_vs_qr(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    registered = register(client, fencer, disciplines=["LS"]).json()

    payment = client.get("/api/tournaments/cup/my-registration/payment", headers=fencer)
    assert payment.status_code == 200
    body = payment.json()
    assert body["amount"] == registered["total_amount"]
    assert body["iban"] == IBAN
    assert body["vs"] == registered["vs"]
    assert body["message"] == f"VS{registered['vs']} Cup"
    assert body["expires_at"] == registered["expires_at"]
    assert f"X-VS:{registered['vs']}" in body["spayd"]
    assert len(body["qr_png_base64"]) > 0


def test_payment_instructions_denied_for_other_account(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer, disciplines=["LS"])

    other = auth_headers(email="f2@example.com", name="F2")
    response = client.get("/api/tournaments/cup/my-registration/payment", headers=other)
    assert response.status_code == 404


def test_payment_instructions_rejected_when_already_paid(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer, disciplines=["LS"])

    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Registration, RegistrationState

    session = next(app.dependency_overrides[get_session]())
    registration = session.scalar(select(Registration))
    registration.state = RegistrationState.PAID
    session.commit()

    response = client.get("/api/tournaments/cup/my-registration/payment", headers=fencer)
    assert response.status_code == 409
    assert response.json()["detail"] == "not_unpaid"


def test_payment_instructions_rejected_when_fully_queued(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)
    register(client, auth_headers(email="a@example.com", name="A"), disciplines=["SB"])
    waiting = auth_headers(email="b@example.com", name="B")
    register(client, waiting, disciplines=["SB"], wait_for_all=True)

    response = client.get("/api/tournaments/cup/my-registration/payment", headers=waiting)
    assert response.status_code == 409
    assert response.json()["detail"] == "no_payment_due"


def test_admit_requires_organizer_and_capacity(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    first = auth_headers(email="a@example.com", name="A")
    register(client, first, disciplines=["SB"])
    waiting = auth_headers(email="b@example.com", name="B")
    register(client, waiting, disciplines=["SB"], wait_for_all=True)

    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Registration

    session = next(app.dependency_overrides[get_session]())
    waiting_id = session.scalar(select(Registration.id).where(Registration.vs == 1000002))

    denied = client.post(
        f"/api/tournaments/cup/registrations/{waiting_id}/admit/SB", headers=first
    )
    assert denied.status_code == 403

    full = client.post(
        f"/api/tournaments/cup/registrations/{waiting_id}/admit/SB", headers=organizer
    )
    assert full.status_code == 409
    assert full.json()["detail"] == "discipline_full"
