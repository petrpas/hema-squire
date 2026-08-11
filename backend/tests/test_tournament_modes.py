"""The four feature flags that make up a tournament's mode, and the endpoint
that writes them (design tournament-modes D1-D4, D12).

The payments feature's behavioural consequences live in
tests/test_payments_off.py; this module covers the flags themselves."""

from tests.test_tournaments import make_tournament

FLAGS = ("feature_schedule", "feature_payments", "feature_teams", "feature_extras")
EASY = dict.fromkeys(FLAGS, False)


def mode(**enabled: bool) -> dict[str, bool]:
    return {**EASY, **enabled}


def set_mode(client, headers, slug, **enabled: bool):
    return client.patch(f"/api/tournaments/{slug}/mode", json=mode(**enabled), headers=headers)


def test_created_tournament_has_no_features(client, auth_headers):
    headers = auth_headers()
    created = make_tournament(client, headers)
    assert {flag: created[flag] for flag in FLAGS} == EASY

    detail = client.get("/api/tournaments/na-duel-2026").json()
    assert {flag: detail[flag] for flag in FLAGS} == EASY


def test_mode_read_and_written(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    assert client.get("/api/tournaments/na-duel-2026/mode", headers=headers).json() == EASY

    response = set_mode(client, headers, "na-duel-2026", feature_payments=True, feature_teams=True)
    assert response.status_code == 200, response.text
    assert {flag: response.json()[flag] for flag in FLAGS} == mode(
        feature_payments=True, feature_teams=True
    )
    assert client.get("/api/tournaments/na-duel-2026/mode", headers=headers).json() == mode(
        feature_payments=True, feature_teams=True
    )


def test_mode_is_chosen_as_a_whole(client, auth_headers):
    """Every feature is given together: a request that omits one is asking for
    it to be off, not for it to be left alone."""
    headers = auth_headers()
    make_tournament(client, headers)
    set_mode(client, headers, "na-duel-2026", feature_extras=True, feature_teams=True)

    response = set_mode(client, headers, "na-duel-2026", feature_teams=True)
    assert response.json()["feature_extras"] is False

    partial = client.patch(
        "/api/tournaments/na-duel-2026/mode", json={"feature_teams": True}, headers=headers
    )
    assert partial.status_code == 422


def test_easy_mode_is_the_absence_of_every_feature(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    set_mode(client, headers, "na-duel-2026", feature_payments=True)

    response = set_mode(client, headers, "na-duel-2026")
    assert {flag: response.json()[flag] for flag in FLAGS} == EASY


def test_mode_requires_console_access(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    outsider = auth_headers(email="other@example.com", name="Other")

    assert set_mode(client, outsider, "na-duel-2026", feature_teams=True).status_code == 403
    assert (
        client.get("/api/tournaments/na-duel-2026/mode", headers=outsider).status_code == 403
    )
    anonymous = client.patch("/api/tournaments/na-duel-2026/mode", json=mode())
    assert anonymous.status_code == 401


def test_console_team_member_sees_and_sets_the_same_mode(client, auth_headers):
    """The mode belongs to the tournament, not to the reader (design D3)."""
    headers = auth_headers()
    make_tournament(client, headers)
    auth_headers(email="member@example.com", name="Member")
    added = client.post(
        "/api/tournaments/na-duel-2026/team",
        json={"email": "member@example.com"},
        headers=headers,
    )
    assert added.status_code in (200, 201), added.text
    member = client.post(
        "/api/auth/login", json={"email": "member@example.com", "password": "correct-horse"}
    ).json()
    member_headers = {"Authorization": f"Bearer {member['token']}"}

    set_mode(client, headers, "na-duel-2026", feature_extras=True)
    assert client.get("/api/tournaments/na-duel-2026/mode", headers=member_headers).json() == mode(
        feature_extras=True
    )
    assert set_mode(
        client, member_headers, "na-duel-2026", feature_extras=True, feature_schedule=True
    ).status_code == 200


def test_features_are_not_re_derived_from_contents(client, auth_headers):
    """Adding a team discipline does not turn the team feature on (design D9),
    and the API stores it regardless of the flag (design D12)."""
    headers = auth_headers()
    make_tournament(client, headers)
    added = client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={
            "slug": "LST",
            "name": "Longsword Teams",
            "weapon": "LS",
            "kind": "team",
            "capacity": 8,
            "team_min": 3,
            "team_max": 5,
        },
        headers=headers,
    )
    assert added.status_code == 201, added.text
    assert client.get("/api/tournaments/na-duel-2026/mode", headers=headers).json() == EASY

    item = client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={"name": "Afterparty", "category": "afterparty", "price": 300},
        headers=headers,
    )
    assert item.status_code == 201, item.text
    assert client.get("/api/tournaments/na-duel-2026/mode", headers=headers).json() == EASY


def test_mode_write_leaves_every_concealed_setting_untouched(client, auth_headers):
    """Turning features off writes nothing but the mode (design D4)."""
    headers = auth_headers()
    make_tournament(client, headers)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={
            "slug": "LST",
            "name": "Longsword Teams",
            "weapon": "LS",
            "kind": "team",
            "capacity": 8,
            "team_min": 3,
            "team_max": 5,
            "fee": 500,
            "schedule_when": "Saturday 09:00",
            "schedule_where": "Hall A",
        },
        headers=headers,
    )
    client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={"name": "Afterparty", "category": "afterparty", "price": 300},
        headers=headers,
    )
    configured = client.patch(
        "/api/tournaments/na-duel-2026",
        json={
            "bank_account": "CZ6508000000192000145399",
            "payment_mode": "deposit",
            "deposit_amount": 200,
            "reservation_validity_days": 5,
            "reminder_day": 3,
            "seating_deadline": "2026-09-01",
            "registration_closes": "2026-09-15",
            "team_composition_deadline": "2026-09-20",
        },
        headers=headers,
    )
    assert configured.status_code == 200, configured.text
    before = client.get("/api/tournaments/na-duel-2026").json()

    set_mode(client, headers, "na-duel-2026", feature_teams=True, feature_payments=True)
    set_mode(client, headers, "na-duel-2026")
    after = client.get("/api/tournaments/na-duel-2026").json()

    assert {k: v for k, v in after.items() if k not in FLAGS} == {
        k: v for k, v in before.items() if k not in FLAGS
    }


def test_mode_changeable_after_publication(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "LS", "name": "Longsword", "weapon": "LS", "capacity": 32, "fee": 0},
        headers=headers,
    )
    client.patch(
        "/api/tournaments/na-duel-2026",
        json={"location": "Brno", "organizers": [{"name": "Klub", "link": None}]},
        headers=headers,
    )
    published = client.post("/api/tournaments/na-duel-2026/publish", headers=headers)
    assert published.status_code == 200, published.text

    response = set_mode(client, headers, "na-duel-2026", feature_extras=True)
    assert response.status_code == 200, response.text
    assert response.json()["feature_extras"] is True
