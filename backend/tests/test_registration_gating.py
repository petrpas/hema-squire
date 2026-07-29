"""Registration gating (task 2.1) and extras-selection validation (2.2).

Gate order (D6): setup complete -> opens <= today -> today <= (closes or
tournament date). Gating applies only to new registration submissions —
never to cancellation, payment matching, or admission of substitutes.
"""

from datetime import date, timedelta

TODAY = date.today()


def make_tournament(client, organizer, slug="cup", **patch):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    if patch:
        client.patch(f"/api/tournaments/{slug}", json=patch, headers=organizer)
    return slug


def add_priced_discipline(client, organizer, slug="cup"):
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )


def register(client, headers, slug="cup", **overrides):
    payload = {"disciplines": ["LS"], **overrides}
    return client.post(f"/api/tournaments/{slug}/register", json=payload, headers=headers)


def test_incomplete_setup_rejects_registration(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)  # no location, no organizers, no disciplines
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(client, fencer, slug=slug)
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "not_published"}


def test_missing_discipline_price_rejects_registration(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client, organizer, location="Brno", organizers=[{"name": "Cup Org", "link": None}]
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"code": "LS", "capacity": 10, "fee": None},
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(client, fencer, slug=slug)
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "not_published"}


def test_before_opening_date_rejects_registration(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client,
        organizer,
        location="Brno",
        organizers=[{"name": "Cup Org", "link": None}],
        registration_opens=str(TODAY + timedelta(days=1)),
    )
    add_priced_discipline(client, organizer, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(client, fencer, slug=slug)
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "not_yet_open"}


def test_after_closing_date_rejects_registration(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client,
        organizer,
        location="Brno",
        organizers=[{"name": "Cup Org", "link": None}],
        registration_closes=str(TODAY - timedelta(days=1)),
    )
    add_priced_discipline(client, organizer, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(client, fencer, slug=slug)
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "closed"}


def test_within_window_and_complete_setup_accepts_registration(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client,
        organizer,
        location="Brno",
        organizers=[{"name": "Cup Org", "link": None}],
        registration_opens=str(TODAY - timedelta(days=1)),
        registration_closes=str(TODAY + timedelta(days=1)),
    )
    add_priced_discipline(client, organizer, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(client, fencer, slug=slug)
    assert response.status_code == 201


def test_no_close_date_stays_open_through_tournament_date(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client, organizer, location="Brno", organizers=[{"name": "Cup Org", "link": None}]
    )
    add_priced_discipline(client, organizer, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    # tournament date (2026-12-05) is in the future; no opens/closes set
    assert register(client, fencer, slug=slug).status_code == 201


def test_gate_does_not_block_cancellation_or_admission_on_incomplete_setup(
    client, auth_headers
):
    """Once registered while setup was complete, later making setup
    incomplete again must not lock out cancellation or substitute admission
    on that existing registration (gate applies only to new submissions)."""
    organizer = auth_headers()
    slug = make_tournament(
        client, organizer, location="Brno", organizers=[{"name": "Cup Org", "link": None}]
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"code": "LS", "capacity": 1, "fee": 800},
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")
    assert register(client, fencer, slug=slug).status_code == 201

    waiting = auth_headers(email="f2@example.com", name="F2")
    waiting_body = register(client, waiting, slug=slug, wait_for_all=True).json()
    assert waiting_body["entries"][0]["is_substitute"] is True

    # organizer clears the titular organizers, making setup incomplete again
    client.patch(f"/api/tournaments/{slug}", json={"organizers": []}, headers=organizer)

    cancelled = client.post(f"/api/tournaments/{slug}/my-registration/cancel", headers=fencer)
    assert cancelled.status_code == 200

    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Registration, RegistrationState

    session = next(app.dependency_overrides[get_session]())
    waiting_id = session.scalar(
        select(Registration.id).where(Registration.state == RegistrationState.RESERVED)
    )
    admitted = client.post(
        f"/api/tournaments/{slug}/registrations/{waiting_id}/admit/LS", headers=organizer
    )
    assert admitted.status_code == 200


def test_unknown_extra_item_rejected(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client, organizer, location="Brno", organizers=[{"name": "Cup Org", "link": None}]
    )
    add_priced_discipline(client, organizer, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(client, fencer, slug=slug, extras=[{"extra_item_id": 999, "qty": 1}])
    assert response.status_code == 422
    assert response.json()["detail"] == {"unknown_extras": [999]}


def test_extra_quantity_over_limit_rejected(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client, organizer, location="Brno", organizers=[{"name": "Cup Org", "link": None}]
    )
    add_priced_discipline(client, organizer, slug)
    item = client.post(
        f"/api/tournaments/{slug}/extra-items",
        json={"name": "weapon rental", "category": "rental", "price": 200, "max_qty": 2},
        headers=organizer,
    ).json()
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(
        client, fencer, slug=slug, extras=[{"extra_item_id": item["id"], "qty": 3}]
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"extras_over_limit": [item["id"]]}


def test_extras_selection_billed_and_itemized_in_output(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(
        client, organizer, location="Brno", organizers=[{"name": "Cup Org", "link": None}]
    )
    add_priced_discipline(client, organizer, slug)
    item = client.post(
        f"/api/tournaments/{slug}/extra-items",
        json={"name": "weapon rental", "category": "rental", "price": 200, "max_qty": 4},
        headers=organizer,
    ).json()
    fencer = auth_headers(email="f1@example.com", name="F1")
    response = register(
        client, fencer, slug=slug, extras=[{"extra_item_id": item["id"], "qty": 2}]
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == 800 + 2 * 200
    assert body["extras"] == [
        {"extra_item_id": item["id"], "name": "weapon rental", "category": "rental", "qty": 2}
    ]
