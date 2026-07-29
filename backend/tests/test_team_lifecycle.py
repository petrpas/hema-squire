"""Team CRUD authorization, ownership transfer (owner and admin fallback
paths), delete-empty vs delete-blocked, and cancelled tournament visibility
and registration gating (tasks 3.1-3.3)."""

from app.models import Role

TOURNAMENT = {"slug": "cup", "display_name": "Cup", "date": "2026-12-05"}


def make_tournament(client, headers, slug="cup"):
    payload = {**TOURNAMENT, "slug": slug}
    response = client.post("/api/tournaments", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return slug


def add_priced_discipline(client, headers, slug):
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 800},
        headers=headers,
    )


def register(client, headers, slug):
    return client.post(
        f"/api/tournaments/{slug}/register", json={"disciplines": ["LS"]}, headers=headers
    )


# --- team CRUD authorization (3.1) ---


def test_owner_can_list_add_and_remove_team_members(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    auth_headers(email="helper@example.com", name="Helper", role=Role.FENCER)

    assert client.get(f"/api/tournaments/{slug}/team", headers=owner).json() == []

    added = client.post(
        f"/api/tournaments/{slug}/team", json={"email": "helper@example.com"}, headers=owner
    )
    assert added.status_code == 201
    body = added.json()
    assert body["email"] == "helper@example.com"

    listed = client.get(f"/api/tournaments/{slug}/team", headers=owner).json()
    assert [m["email"] for m in listed] == ["helper@example.com"]

    removed = client.delete(
        f"/api/tournaments/{slug}/team/{body['fencer_id']}", headers=owner
    )
    assert removed.status_code == 204
    assert client.get(f"/api/tournaments/{slug}/team", headers=owner).json() == []


def test_add_team_member_unknown_email_404(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    response = client.post(
        f"/api/tournaments/{slug}/team", json={"email": "ghost@example.com"}, headers=owner
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "account_not_found"


def test_add_team_member_duplicate_409(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    auth_headers(email="helper@example.com", name="Helper", role=Role.FENCER)
    client.post(
        f"/api/tournaments/{slug}/team", json={"email": "helper@example.com"}, headers=owner
    )
    again = client.post(
        f"/api/tournaments/{slug}/team", json={"email": "helper@example.com"}, headers=owner
    )
    assert again.status_code == 409
    assert again.json()["detail"] == "already_organizer"


def test_team_member_cannot_manage_team(client, auth_headers):
    """Spec: Team member cannot manage the team."""
    owner = auth_headers()
    slug = make_tournament(client, owner)
    helper = auth_headers(email="helper@example.com", name="Helper", role=Role.FENCER)
    client.post(
        f"/api/tournaments/{slug}/team", json={"email": "helper@example.com"}, headers=owner
    )
    denied = client.post(
        f"/api/tournaments/{slug}/team", json={"email": "another@example.com"}, headers=helper
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "not_tournament_owner"


def test_remove_unknown_team_member_404(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    response = client.delete(f"/api/tournaments/{slug}/team/999999", headers=owner)
    assert response.status_code == 404
    assert response.json()["detail"] == "not_a_team_member"


# --- ownership transfer (3.2) ---


def test_owner_transfers_to_team_member(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    auth_headers(email="helper@example.com", name="Helper", role=Role.FENCER)
    client.post(
        f"/api/tournaments/{slug}/team", json={"email": "helper@example.com"}, headers=owner
    )

    transferred = client.post(
        f"/api/tournaments/{slug}/transfer-ownership",
        json={"email": "helper@example.com"},
        headers=owner,
    )
    assert transferred.status_code == 200

    detail = client.get(f"/api/tournaments/{slug}", headers=owner).json()

    # the new owner has console access
    login = client.post(
        "/api/auth/login", json={"email": "helper@example.com", "password": "correct-horse"}
    )
    helper = {"Authorization": f"Bearer {login.json()['token']}"}
    assert (
        client.patch(f"/api/tournaments/{slug}", json={"location": "X"}, headers=helper).status_code
        == 200
    )
    # the previous owner (now a team member) still has console access
    assert (
        client.patch(f"/api/tournaments/{slug}", json={"location": "Y"}, headers=owner).status_code
        == 200
    )
    # but the previous owner can no longer manage the team or transfer again
    assert (
        client.post(
            f"/api/tournaments/{slug}/team", json={"email": "x@example.com"}, headers=owner
        ).status_code
        == 403
    )
    assert detail["owner_id"] is not None


def test_transfer_rejects_non_team_member(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    auth_headers(email="stranger@example.com", name="Stranger", role=Role.FENCER)
    response = client.post(
        f"/api/tournaments/{slug}/transfer-ownership",
        json={"email": "stranger@example.com"},
        headers=owner,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "not_a_team_member"


def test_transfer_rejects_unknown_email(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    response = client.post(
        f"/api/tournaments/{slug}/transfer-ownership",
        json={"email": "ghost@example.com"},
        headers=owner,
    )
    assert response.status_code == 404


def test_admin_assigns_owner_fallback(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    new_owner = auth_headers(email="newowner@example.com", name="New Owner", role=Role.FENCER)

    response = client.post(
        f"/api/tournaments/{slug}/assign-owner",
        json={"email": "newowner@example.com"},
        headers=admin,
    )
    assert response.status_code == 200
    assert (
        client.patch(
            f"/api/tournaments/{slug}", json={"location": "Z"}, headers=new_owner
        ).status_code
        == 200
    )


def test_non_admin_cannot_use_assign_owner_fallback(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    response = client.post(
        f"/api/tournaments/{slug}/assign-owner", json={"email": "owner@example.com"}, headers=owner
    )
    assert response.status_code == 403


# --- delete/cancel lifecycle (3.3) ---


def test_delete_empty_tournament_succeeds(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    add_priced_discipline(client, owner, slug)
    response = client.delete(f"/api/tournaments/{slug}", headers=owner)
    assert response.status_code == 204
    assert client.get(f"/api/tournaments/{slug}", headers=owner).status_code == 404


def test_delete_blocked_by_registrations(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    client.patch(
        f"/api/tournaments/{slug}",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=owner,
    )
    add_priced_discipline(client, owner, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    assert register(client, fencer, slug).status_code == 201

    response = client.delete(f"/api/tournaments/{slug}", headers=owner)
    assert response.status_code == 409
    assert response.json()["detail"] == "has_registrations"


def test_cancel_hides_from_public_list_but_keeps_console(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    client.patch(
        f"/api/tournaments/{slug}",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=owner,
    )
    add_priced_discipline(client, owner, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")
    assert register(client, fencer, slug).status_code == 201

    cancelled = client.post(f"/api/tournaments/{slug}/cancel", headers=owner)
    assert cancelled.status_code == 200
    assert cancelled.json()["cancelled_at"] is not None

    listing = client.get("/api/tournaments").json()
    assert slug not in [t["slug"] for t in listing]

    # console (detail) remains accessible
    detail = client.get(f"/api/tournaments/{slug}", headers=owner)
    assert detail.status_code == 200
    assert client.patch(
        f"/api/tournaments/{slug}", json={"location": "Nove"}, headers=owner
    ).status_code == 200


def test_cancelled_tournament_rejects_new_registrations_as_closed(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    client.patch(
        f"/api/tournaments/{slug}",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=owner,
    )
    add_priced_discipline(client, owner, slug)
    client.post(f"/api/tournaments/{slug}/cancel", headers=owner)

    fencer = auth_headers(email="f2@example.com", name="F2")
    response = register(client, fencer, slug)
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "closed"}


def test_non_owner_cannot_cancel_or_delete(client, auth_headers):
    owner = auth_headers()
    slug = make_tournament(client, owner)
    stranger = auth_headers(email="stranger@example.com", role=Role.FENCER)
    assert client.post(f"/api/tournaments/{slug}/cancel", headers=stranger).status_code == 403
    assert client.delete(f"/api/tournaments/{slug}", headers=stranger).status_code == 403
