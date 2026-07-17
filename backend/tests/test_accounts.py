def signup(client, **overrides):
    payload = {
        "email": "fencer@example.com",
        "password": "long-enough-pass",
        "display_name": "Fencer",
        **overrides,
    }
    return client.post("/api/auth/signup", json=payload)


def headers_from(response):
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_hr_search_is_diacritics_insensitive(client):
    hits = client.get("/api/hr/search", params={"q": "novak"}).json()
    assert [h["name"] for h in hits] == ["Jan Novák"]
    hits = client.get("/api/hr/search", params={"q": "Novák"}).json()
    assert [h["hr_id"] for h in hits] == [10234]


def test_signup_with_hr_binding_prefills_profile(client):
    response = signup(client, display_name=None, hr_id=10234)
    assert response.status_code == 201

    account = client.get("/api/account", headers=headers_from(response)).json()
    assert account["display_name"] == "Jan Novák"  # HR canonical name
    assert account["nationality"] == "CZE"
    assert account["club"] == "Prague HEMA"
    assert account["hr_id"] == 10234


def test_signup_may_adjust_club(client):
    response = signup(client, display_name=None, hr_id=5567, club="SK Brno")
    account = client.get("/api/account", headers=headers_from(response)).json()
    assert account["club"] == "SK Brno"
    assert account["display_name"] == "Petr Svoboda"


def test_one_account_per_hr_identity(client):
    assert signup(client, hr_id=10234).status_code == 201
    second = signup(client, email="other@example.com", hr_id=10234)
    assert second.status_code == 409
    assert second.json()["detail"] == "hr_id_already_bound"


def test_signup_without_hr_profile_and_bind_later(client):
    response = signup(client)
    assert response.status_code == 201
    headers = headers_from(response)
    assert client.get("/api/account", headers=headers).json()["hr_id"] is None

    bound = client.post("/api/account/hr-binding", json={"hr_id": 8821}, headers=headers)
    assert bound.status_code == 200
    account = bound.json()
    assert account["hr_id"] == 8821
    assert account["display_name"] == "Lukas Mueller"

    again = client.post("/api/account/hr-binding", json={"hr_id": 3340}, headers=headers)
    assert again.status_code == 409
    assert again.json()["detail"] == "already_bound"


def test_late_binding_respects_uniqueness(client):
    signup(client, hr_id=3340)
    other = signup(client, email="b@example.com")
    response = client.post(
        "/api/account/hr-binding", json={"hr_id": 3340}, headers=headers_from(other)
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "hr_id_already_bound"


def test_profile_update_is_audited(client):
    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import FencerProfileAudit

    response = signup(client)
    headers = headers_from(response)
    updated = client.patch("/api/account", json={"club": "Nový klub"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["club"] == "Nový klub"

    session_gen = app.dependency_overrides[get_session]()
    session = next(session_gen)
    entries = session.scalars(select(FencerProfileAudit)).all()
    assert [(e.field, e.old_value, e.new_value) for e in entries] == [
        ("club", None, "Nový klub")
    ]


def test_display_name_required_without_hr(client):
    response = signup(client, display_name=None)
    assert response.status_code == 422
