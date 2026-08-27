"""Tests for the unified `{errors: [{field, code, params}]}` response shape
(design `add-field-validation` D3) — task 3.4."""

def make_tournament(client, headers, slug="cup"):
    response = client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_two_fields_failing_produce_two_entries(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": -1, "fee": -5},
        headers=headers,
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    fields = {error["field"] for error in errors}
    assert fields == {"capacity", "fee"}


def test_limit_violation_carries_limit_in_params(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={"weapon": "LS", "capacity": 10, "fee": 20000},
        headers=headers,
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    fee_error = next(error for error in errors if error["field"] == "fee")
    assert fee_error["code"] == "out_of_range"
    assert fee_error["params"] == {"min": 0, "max": 10000}


def test_converted_router_code_arrives_in_same_envelope(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Other", "date": "2027-01-01"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "errors": [{"field": "slug", "code": "slug_taken", "params": {}}]
    }


def test_unconverted_bare_string_detail_round_trips(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.delete(
        "/api/tournaments/cup/disciplines/does-not-exist", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "discipline_not_found"


def test_pydantic_error_field_path_drops_body_prefix(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.patch(
        "/api/tournaments/cup",
        json={"organizers": [{"name": "Duelanti", "link": "javascript:x"}]},
        headers=headers,
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert errors == [{"field": "organizers.0.link", "code": "bad_link_scheme", "params": {}}]
