"""Discipline capacity and extra-item max_qty are bounded by an owner
decision resolved from another field (`kind`, `category` respectively) —
not expressible as a static `Field(...)` constraint, so enforced by a
`model_validator` and surfaced through the same error envelope as any other
bound (design `add-field-validation`)."""


def make_tournament(client, headers, slug="cup"):
    response = client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_individual_capacity_over_200_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 201, "fee": 800},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == [
        {"field": "capacity", "code": "out_of_range", "params": {"min": 1, "max": 200}}
    ]


def test_individual_capacity_at_200_accepted(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 200, "fee": 800},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_team_capacity_over_64_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "weapon": "LS", "capacity": 65, "fee": 800,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == [
        {"field": "capacity", "code": "out_of_range", "params": {"min": 1, "max": 64}}
    ]


def test_team_capacity_at_64_accepted(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "weapon": "LS", "capacity": 64, "fee": 800,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_rental_max_qty_over_10_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Sword rental", "category": "rental", "price": 100, "max_qty": 11},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == [
        {"field": "max_qty", "code": "out_of_range", "params": {"min": 1, "max": 10}}
    ]


def test_rental_max_qty_at_10_accepted(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Sword rental", "category": "rental", "price": 100, "max_qty": 10},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_merch_max_qty_over_100_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Event shirt", "category": "merch", "price": 300, "max_qty": 101},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == [
        {"field": "max_qty", "code": "out_of_range", "params": {"min": 1, "max": 100}}
    ]


def test_other_item_max_qty_over_100_rejected(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Misc goods", "category": "other_item", "price": 300, "max_qty": 101},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == [
        {"field": "max_qty", "code": "out_of_range", "params": {"min": 1, "max": 100}}
    ]


def test_action_category_max_qty_has_no_ceiling_before_router_forces_it_to_one(
    client, auth_headers
):
    """seminar/afterparty/other_action are always forced to max_qty=1 by the
    router regardless of what is submitted, so a high value here is not a
    validation failure — it is simply overridden after."""
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Friday seminar", "category": "seminar", "price": 300, "max_qty": 9999},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["max_qty"] == 1
