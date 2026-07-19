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


def test_hr_search_nationality_filter_narrows_results(client):
    # nationality filters to CZE first; both CZE profiles are scored (D4: no
    # score threshold once nationality narrows the space), but the actual
    # name match ("svoboda") ranks first
    hits = client.get(
        "/api/hr/search", params={"q": "svoboda", "nationality": "CZE"}
    ).json()
    assert [h["hr_id"] for h in hits][0] == 5567
    assert {h["hr_id"] for h in hits} == {10234, 5567}

    # POL has a single profile — it's still returned even though the query
    # doesn't match it well
    hits = client.get(
        "/api/hr/search", params={"q": "svoboda", "nationality": "POL"}
    ).json()
    assert [h["hr_id"] for h in hits] == [3340]


def test_hr_nationalities_lists_distinct_sorted_values(client):
    nationalities = client.get("/api/hr/nationalities").json()
    assert nationalities == ["CZE", "DEU", "DNK", "POL"]


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


def test_claiming_an_already_claimed_hr_id_succeeds(client):
    assert signup(client, hr_id=10234).status_code == 201
    second = signup(client, email="other@example.com", hr_id=10234)
    assert second.status_code == 201
    account = client.get("/api/account", headers=headers_from(second)).json()
    assert account["hr_id"] == 10234


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


def test_late_binding_allows_an_already_claimed_hr_id(client):
    signup(client, hr_id=3340)
    other = signup(client, email="b@example.com")
    response = client.post(
        "/api/account/hr-binding", json={"hr_id": 3340}, headers=headers_from(other)
    )
    assert response.status_code == 200
    assert response.json()["hr_id"] == 3340


def test_hr_search_marks_claimed_profiles(client):
    signup(client, hr_id=10234)

    hits = client.get("/api/hr/search", params={"q": "novak"}).json()
    assert [(h["hr_id"], h["claimed"]) for h in hits] == [(10234, True)]

    hits = client.get("/api/hr/search", params={"q": "mueller"}).json()
    assert [(h["hr_id"], h["claimed"]) for h in hits] == [(8821, False)]


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


def test_signup_stores_chosen_language(client):
    response = signup(client, language="en")
    assert response.status_code == 201
    account = client.get("/api/account", headers=headers_from(response)).json()
    assert account["language"] == "en"


def test_signup_defaults_language_to_cs(client):
    response = signup(client)
    account = client.get("/api/account", headers=headers_from(response)).json()
    assert account["language"] == "cs"


def test_signup_rejects_unknown_language(client):
    response = signup(client, language="xx")
    assert response.status_code == 422


def test_language_change_via_account_update_is_audited(client):
    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import FencerProfileAudit

    response = signup(client)
    headers = headers_from(response)
    updated = client.patch("/api/account", json={"language": "en"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["language"] == "en"

    session_gen = app.dependency_overrides[get_session]()
    session = next(session_gen)
    entries = session.scalars(select(FencerProfileAudit)).all()
    assert [(e.field, e.old_value, e.new_value) for e in entries] == [
        ("language", "cs", "en")
    ]


def test_account_update_rejects_unknown_language(client):
    response = signup(client)
    headers = headers_from(response)
    updated = client.patch("/api/account", json={"language": "xx"}, headers=headers)
    assert updated.status_code == 422
