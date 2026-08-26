from datetime import date, timedelta

from tests.conftest import enable_payments, publish

TODAY = date.today()


def setup_tournament(client, organizer, early_bird=False):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
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
        json={"slug": "LS", "weapon": "LS", "capacity": 2, "fee": 800, "fee_early": 600},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 1, "fee": 500},
        headers=organizer,
    )
    publish(client, organizer, "cup")


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
    assert body["vs"] == 2601001
    assert body["state"] == "reserved"
    assert body["expires_at"] is not None
    assert all(not e["is_substitute"] for e in body["entries"])

    second = auth_headers(email="f2@example.com", name="F2")
    assert register(client, second).json()["vs"] == 2601002


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


def test_full_discipline_is_placed_not_refused(client, auth_headers):
    """A full discipline no longer refuses the submission to ask the fencer to
    choose between trimming it and queueing everything: it is queued, the open
    discipline beside it is seated, and both are reported per discipline."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="A"), disciplines=["SB"])

    late = auth_headers(email="b@example.com", name="B")
    response = register(client, late, disciplines=["LS", "SB"])
    assert response.status_code == 201

    entries = {e["slug"]: e for e in response.json()["entries"]}
    assert entries["LS"]["is_substitute"] is False
    assert entries["SB"]["is_substitute"] is True
    assert entries["SB"]["queue_position"] == 1
    assert entries["LS"]["queue_position"] is None


def test_mixed_selection_bills_the_seat_and_queues_the_rest(client, auth_headers):
    """The successor to the all-or-nothing rule: a full discipline no longer
    costs the fencer the open one beside it. The seat is billed with the
    extras and opens a window; the queued placement adds nothing."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="A"), disciplines=["SB"])

    waiting = auth_headers(email="b@example.com", name="B")
    body = register(client, waiting, disciplines=["LS", "SB"], afterparty=True).json()

    entries = {e["slug"]: e for e in body["entries"]}
    assert entries["LS"]["is_substitute"] is False
    assert entries["SB"]["is_substitute"] is True
    assert entries["SB"]["queue_position"] == 1
    # LS's fee and the afterparty; SB is queued and unpriced
    assert body["total_amount"] == 800 + 300
    assert body["expires_at"] is not None

    availability = client.get("/api/tournaments/cup/availability").json()
    sb = next(a for a in availability if a["slug"] == "SB")
    assert sb == {
        "slug": "SB",
        "kind": "individual",
        "capacity": 1,
        "taken": 1,
        "free": 0,
        "queue_length": 1,
        "team_min": None,
        "team_max": None,
    }
    ls = next(a for a in availability if a["slug"] == "LS")
    assert (ls["taken"], ls["free"], ls["queue_length"]) == (1, 1, 0)


def test_cancel_frees_spot_and_admit_bills_frozen_prices(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    first = auth_headers(email="a@example.com", name="A")
    register(client, first, disciplines=["SB"])

    waiting = auth_headers(email="b@example.com", name="B")
    waiting_body = register(
        client, waiting, disciplines=["SB"], afterparty=True
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


def test_price_preview_breakdown_lists_applied_and_unapplied(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={
            "discounts": [
                {
                    "name": "2 disciplines",
                    "condition": {"kind": "discipline_count", "count": 2},
                    "effect": {"kind": "fixed", "value": 100},
                    "scope": ["discipline"],
                },
                {
                    "name": "3 disciplines",
                    "condition": {"kind": "discipline_count", "count": 3},
                    "effect": {"kind": "fixed", "value": 200},
                    "scope": ["discipline"],
                },
            ]
        },
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")

    preview = client.post(
        "/api/tournaments/cup/price-preview",
        json={"disciplines": ["LS", "SB"]},
        headers=fencer,
    )
    assert preview.status_code == 200
    discounts = preview.json()["discounts"]
    assert [d["name"] for d in discounts] == ["2 disciplines", "3 disciplines"]
    assert discounts[0]["applied"] is True
    assert discounts[0]["deducted"] == 100
    assert discounts[1]["applied"] is False
    assert discounts[1]["deducted"] is None


def test_price_preview_fixed_discount_reported_in_both_currencies(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    # the tournament is already published, so enabling EUR must not pass
    # through a moment where a discipline has no EUR price (design D3 of
    # add-explicit-publishing): give every discipline its EUR price first,
    # then enable EUR mode as a separate, already-complete step
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={
            "slug": "LS",
            "weapon": "LS",
            "capacity": 2,
            "fee": 800,
            "fee_early": 600,
            "fee_eur": 32,
        },
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup/disciplines/SB",
        json={"slug": "SB", "weapon": "SB", "capacity": 1, "fee": 500, "fee_eur": 20},
        headers=organizer,
    )
    # legacy fixed weapon-rental/afterparty fees carry no EUR column and
    # block EUR mode (design Decision 9); clear them before enabling it
    client.patch(
        "/api/tournaments/cup",
        json={"weapon_rental_fee": 0, "afterparty_fee": 0, "eur_payments_enabled": True},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "discounts": [
                {
                    "name": "2 disciplines",
                    "condition": {"kind": "discipline_count", "count": 2},
                    "effect": {"kind": "fixed", "value": 100, "value_eur": 4},
                    "scope": ["discipline"],
                }
            ]
        },
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")

    preview = client.post(
        "/api/tournaments/cup/price-preview",
        json={"disciplines": ["LS", "SB"]},
        headers=fencer,
    )
    assert preview.status_code == 200
    entry = preview.json()["discounts"][0]
    assert entry["applied"] is True
    assert entry["deducted"] == 100
    assert entry["deducted_eur"] == 4


def test_price_preview_percentage_discount_carries_no_eur_value(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    # give every discipline its EUR price before enabling EUR mode, so the
    # already-published tournament never passes through an incomplete moment
    # (design D3 of add-explicit-publishing)
    client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={
            "slug": "LS",
            "weapon": "LS",
            "capacity": 2,
            "fee": 800,
            "fee_early": 600,
            "fee_eur": 32,
        },
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup/disciplines/SB",
        json={"slug": "SB", "weapon": "SB", "capacity": 1, "fee": 500, "fee_eur": 20},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"weapon_rental_fee": 0, "afterparty_fee": 0, "eur_payments_enabled": True},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "discounts": [
                {
                    "name": "10 percent off",
                    "condition": {"kind": "discipline_count", "count": 1},
                    "effect": {"kind": "percent", "value": 10},
                    "scope": ["discipline"],
                }
            ]
        },
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")

    preview = client.post(
        "/api/tournaments/cup/price-preview",
        json={"disciplines": ["LS"]},
        headers=fencer,
    )
    assert preview.status_code == 200
    entry = preview.json()["discounts"][0]
    assert entry["effect"]["kind"] == "percent"
    assert entry["applied"] is True
    assert entry["deducted"] == 80  # 800 * 0.10
    assert entry["deducted_eur"] is None


def test_price_preview_empty_breakdown_when_no_discounts_configured(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")

    preview = client.post(
        "/api/tournaments/cup/price-preview",
        json={"disciplines": ["LS"]},
        headers=fencer,
    )
    assert preview.status_code == 200
    assert preview.json()["discounts"] == []


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
    assert body["entries"][0]["slug"] == "SB"
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
    assert body["account_domestic"] == "19-2000145399/0800"


def test_payment_instructions_account_domestic_null_for_foreign_iban(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch(
        "/api/tournaments/cup", json={"bank_account": "DE89370400440532013000"}, headers=organizer
    )
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer, disciplines=["LS"])

    payment = client.get("/api/tournaments/cup/my-registration/payment", headers=fencer)
    assert payment.status_code == 200
    body = payment.json()
    assert body["iban"] == "DE89370400440532013000"
    assert body["account_domestic"] is None
    assert "ACC:DE89370400440532013000" in body["spayd"]


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
    register(client, waiting, disciplines=["SB"])

    response = client.get("/api/tournaments/cup/my-registration/payment", headers=waiting)
    assert response.status_code == 409
    assert response.json()["detail"] == "no_payment_due"


def test_admit_requires_organizer_and_capacity(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    first = auth_headers(email="a@example.com", name="A")
    register(client, first, disciplines=["SB"])
    waiting = auth_headers(email="b@example.com", name="B")
    register(client, waiting, disciplines=["SB"])

    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Registration

    session = next(app.dependency_overrides[get_session]())
    waiting_id = session.scalar(select(Registration.id).where(Registration.vs == 2601002))

    denied = client.post(
        f"/api/tournaments/cup/registrations/{waiting_id}/admit/SB", headers=first
    )
    assert denied.status_code == 403

    full = client.post(
        f"/api/tournaments/cup/registrations/{waiting_id}/admit/SB", headers=organizer
    )
    assert full.status_code == 409
    assert full.json()["detail"] == "discipline_full"


# ---------------------------------------------------------------------------
# 9.2-9.4 Console: slug generation, override, collision, freeze, custom
# weapon (design discipline-identity D3, D4)
# ---------------------------------------------------------------------------


def test_two_disciplines_same_classification_get_generated_slugs(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    first = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert first.status_code == 201, first.text
    assert first.json()["slug"] == "LS"
    second = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert second.status_code == 201, second.text
    assert second.json()["slug"] == "LS-2"


def test_individual_and_team_discipline_in_one_weapon_both_accepted(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    individual = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    team = client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )
    assert individual.status_code == 201
    assert team.status_code == 201
    assert individual.json()["slug"] == "LS"
    assert team.json()["slug"] == "Team-LS"


def test_second_individual_and_team_discipline_disambiguated(client, auth_headers):
    """design discipline-identity-modal D5: `LS`, `Team-LS`, `LS-2`, `Team-LS-2`."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    payload = {"weapon": "LS", "capacity": 10, "fee": 800}
    team_payload = {
        "weapon": "LS", "capacity": 5, "fee": 3000,
        "kind": "team", "team_min": 3, "team_max": 4,
    }
    first = client.post("/api/tournaments/cup/disciplines", json=payload, headers=organizer)
    team_first = client.post(
        "/api/tournaments/cup/disciplines", json=team_payload, headers=organizer
    )
    second = client.post("/api/tournaments/cup/disciplines", json=payload, headers=organizer)
    team_second = client.post(
        "/api/tournaments/cup/disciplines", json=team_payload, headers=organizer
    )
    assert first.json()["slug"] == "LS"
    assert team_first.json()["slug"] == "Team-LS"
    assert second.json()["slug"] == "LS-2"
    assert team_second.json()["slug"] == "Team-LS-2"


def test_organizer_override_accepted_and_collision_refused(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    a = client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-A", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    b = client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-B", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert a.status_code == 201 and a.json()["slug"] == "LS-A"
    assert b.status_code == 201 and b.json()["slug"] == "LS-B"

    collision = client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-A", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert collision.status_code == 409
    assert collision.json()["detail"] == {
        "errors": [
            {"field": "slug", "code": "discipline_slug_taken", "params": {"value": "LS-A"}}
        ]
    }


def test_slug_generated_from_a_weapon_outside_the_taxonomy_is_normalized(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    created = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "Tešák", "name": "Tesak Open", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert created.status_code == 201, created.text
    assert created.json()["slug"] == "Tesak"


def test_slug_override_is_normalized(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    created = client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "Sword & Buckler (variant)", "weapon": "SB", "capacity": 10, "fee": 800,
        },
        headers=organizer,
    )
    assert created.status_code == 201, created.text
    assert created.json()["slug"] == "Sword-Buckler-variant"


def test_existing_team_slug_from_before_kind_aware_generation_is_not_rewritten(
    client, auth_headers
):
    """design discipline-identity-modal D5: forward-only — a tournament whose
    team discipline is `LS-2` (created before slugs stated their kind) keeps
    it, and merely renaming the discipline does not touch the slug."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-2", "weapon": "LS", "capacity": 5, "fee": 3000, "kind": "team",
              "team_min": 3, "team_max": 4},
        headers=organizer,
    )
    renamed = client.patch(
        "/api/tournaments/cup/disciplines/LS-2",
        json={"weapon": "LS", "name": "Team Longsword (renamed)", "capacity": 5, "fee": 3000,
              "kind": "team", "team_min": 3, "team_max": 4},
        headers=organizer,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["slug"] == "LS-2"
    assert renamed.json()["name"] == "Team Longsword (renamed)"


# ---------------------------------------------------------------------------
# identity_frozen (design discipline-identity-modal D6): reported alongside
# the discipline rather than inferred from taken seats
# ---------------------------------------------------------------------------


def _identity_frozen(client, organizer, slug="LS"):
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    discipline = next(d for d in detail["disciplines"] if d["slug"] == slug)
    return discipline["identity_frozen"]


def test_unreferenced_discipline_is_not_frozen(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    assert _identity_frozen(client, organizer) is False


def test_cancelled_entry_still_freezes(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    availability = client.get("/api/tournaments/cup/availability").json()
    ls = next(a for a in availability if a["slug"] == "LS")
    assert ls["taken"] == 0  # the case `taken` gets wrong

    assert _identity_frozen(client, organizer) is True


def test_substitute_entry_freezes(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="A"), disciplines=["SB"])
    waiting = auth_headers(email="b@example.com", name="B")
    body = register(client, waiting, disciplines=["SB"]).json()
    assert all(e["is_substitute"] for e in body["entries"])

    assert _identity_frozen(client, organizer, slug="SB") is True


def test_rename_succeeds_on_a_frozen_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer)
    assert _identity_frozen(client, organizer) is True

    renamed = client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"weapon": "LS", "name": "Longsword Renamed", "capacity": 2, "fee": 800,
              "fee_early": 600},
        headers=organizer,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Longsword Renamed"
    assert renamed.json()["slug"] == "LS"


def test_slug_editable_before_registration_frozen_after(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    edited = client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"slug": "LS-renamed", "weapon": "LS", "capacity": 2, "fee": 800, "fee_early": 600},
        headers=organizer,
    )
    assert edited.status_code == 200
    assert edited.json()["slug"] == "LS-renamed"

    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer, disciplines=["LS-renamed"])
    frozen = client.patch(
        "/api/tournaments/cup/disciplines/LS-renamed",
        json={
            "slug": "LS-renamed-again", "weapon": "LS", "capacity": 2, "fee": 800,
            "fee_early": 600,
        },
        headers=organizer,
    )
    assert frozen.status_code == 409
    assert frozen.json()["detail"] == {
        "errors": [{"field": "slug", "code": "discipline_slug_frozen", "params": {}}]
    }


def test_slug_frozen_after_team_entry(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-Team", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )
    publish(client, organizer, "cup")
    captain = auth_headers(email="captain@example.com", name="Captain")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": [], "teams": [{"slug": "LS-Team", "name": "Wolves"}]},
        headers=captain,
    )
    frozen = client.patch(
        "/api/tournaments/cup/disciplines/LS-Team",
        json={
            "slug": "LS-Team-2", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )
    assert frozen.status_code == 409
    assert frozen.json()["detail"] == {
        "errors": [{"field": "slug", "code": "discipline_slug_frozen", "params": {}}]
    }


def test_custom_weapon_accepted_with_name_refused_without(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    named = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "Messer", "name": "Messer Open", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert named.status_code == 201, named.text
    assert named.json()["name"] == "Messer Open"

    unnamed = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "Ringen", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    assert unnamed.status_code == 422
    assert unnamed.json()["detail"] == {
        "errors": [{"field": "name", "code": "discipline_name_required", "params": {}}]
    }


# ---------------------------------------------------------------------------
# 9.5 Registration: two same-classification disciplines are counted
# separately (design discipline-identity)
# ---------------------------------------------------------------------------


def test_entering_one_tier_does_not_count_against_the_other(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-A", "weapon": "LS", "name": "Top", "capacity": 1, "fee": 800},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-B", "weapon": "LS", "name": "Open", "capacity": 1, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS-A"]}, headers=fencer
    )
    assert response.status_code == 201

    availability = {a["slug"]: a for a in client.get("/api/tournaments/cup/availability").json()}
    assert availability["LS-A"]["taken"] == 1
    assert availability["LS-A"]["free"] == 0
    assert availability["LS-B"]["taken"] == 0
    assert availability["LS-B"]["free"] == 1
