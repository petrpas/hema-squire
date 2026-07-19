"""Admin panel API: role-change authorization matrix, plea lifecycle
(submit/duplicate/grant/deny/re-plea), HR unbind and audit, and panel access
denied below Admin (tasks 4.1-4.4)."""

import pytest

from app.config import settings
from app.models import Role

# --- panel access (Requirement: Admin panel) ---


def test_fencer_and_organizer_blocked_from_admin_panel(client, auth_headers):
    fencer = auth_headers(email="f@example.com", role=Role.FENCER)
    organizer = auth_headers(email="o@example.com", role=Role.ORGANIZER)
    assert client.get("/api/admin/accounts", headers=fencer).status_code == 403
    assert client.get("/api/admin/accounts", headers=organizer).status_code == 403
    assert client.get("/api/admin/pleas", headers=fencer).status_code == 403


def test_admin_can_list_accounts(client, auth_headers):
    auth_headers(email="f@example.com", name="F", role=Role.FENCER)
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    accounts = client.get("/api/admin/accounts", headers=admin).json()
    emails = {a["email"] for a in accounts}
    assert {"f@example.com", "admin@example.com"} <= emails


# --- role-change authorization matrix ---


def test_admin_grants_and_revokes_organizer(client, auth_headers):
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    target_headers = auth_headers(email="f@example.com", name="F", role=Role.FENCER)
    target = client.get("/api/account", headers=target_headers).json()

    granted = client.patch(
        f"/api/admin/accounts/{target['id']}/role", json={"role": "organizer"}, headers=admin
    )
    assert granted.status_code == 200
    assert granted.json()["role"] == "organizer"

    revoked = client.patch(
        f"/api/admin/accounts/{target['id']}/role", json={"role": "fencer"}, headers=admin
    )
    assert revoked.status_code == 200
    assert revoked.json()["role"] == "fencer"


def test_admin_cannot_grant_admin(client, auth_headers):
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    target_headers = auth_headers(email="f@example.com", name="F", role=Role.FENCER)
    target = client.get("/api/account", headers=target_headers).json()

    response = client.patch(
        f"/api/admin/accounts/{target['id']}/role", json={"role": "admin"}, headers=admin
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_role"


def test_admin_cannot_change_another_admins_role(client, auth_headers):
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    other_admin_headers = auth_headers(email="other-admin@example.com", role=Role.ADMIN)
    other_admin = client.get("/api/account", headers=other_admin_headers).json()

    response = client.patch(
        f"/api/admin/accounts/{other_admin['id']}/role",
        json={"role": "fencer"},
        headers=admin,
    )
    assert response.status_code == 403


@pytest.fixture
def owner_email(monkeypatch):
    monkeypatch.setattr(settings, "owner_email", "owner@example.com")


def test_owner_grants_admin(client, auth_headers, owner_email):
    owner = auth_headers(email="owner@example.com", name="Owner", role=Role.FENCER)
    target_headers = auth_headers(email="f@example.com", name="F", role=Role.FENCER)
    target = client.get("/api/account", headers=target_headers).json()

    response = client.patch(
        f"/api/admin/accounts/{target['id']}/role", json={"role": "admin"}, headers=owner
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_nobody_can_edit_the_owner(client, auth_headers, owner_email):
    owner_headers = auth_headers(email="owner@example.com", name="Owner", role=Role.FENCER)
    owner_account = client.get("/api/account", headers=owner_headers).json()
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)

    # neither another Admin ...
    response = client.patch(
        f"/api/admin/accounts/{owner_account['id']}/role",
        json={"role": "fencer"},
        headers=admin,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "cannot_edit_owner"

    # ... nor the Owner itself
    response = client.patch(
        f"/api/admin/accounts/{owner_account['id']}/role",
        json={"role": "fencer"},
        headers=owner_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "cannot_edit_owner"


def test_role_change_unknown_account_404(client, auth_headers):
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    response = client.patch(
        "/api/admin/accounts/999999/role", json={"role": "organizer"}, headers=admin
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "account_not_found"


# --- plea lifecycle (submit/duplicate/grant/deny/re-plea) ---


def test_plea_submit_grant_lifecycle(client, auth_headers):
    fencer = auth_headers(email="f@example.com", name="F", role=Role.FENCER)
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)

    submitted = client.post(
        "/api/account/plea", json={"message": "please"}, headers=fencer
    )
    assert submitted.status_code == 201
    assert submitted.json()["state"] == "pending"

    mine = client.get("/api/account/plea", headers=fencer).json()
    assert mine["state"] == "pending"

    queue = client.get("/api/admin/pleas", headers=admin).json()
    assert len(queue) == 1
    plea_id = queue[0]["id"]
    assert queue[0]["message"] == "please"

    granted = client.post(f"/api/admin/pleas/{plea_id}/grant", headers=admin)
    assert granted.status_code == 200
    assert granted.json()["state"] == "granted"

    account = client.get("/api/account", headers=fencer).json()
    assert account["role"] == "organizer"

    # queue is now empty
    assert client.get("/api/admin/pleas", headers=admin).json() == []


def test_duplicate_plea_rejected(client, auth_headers):
    fencer = auth_headers(email="f@example.com", role=Role.FENCER)
    client.post("/api/account/plea", json={"message": "one"}, headers=fencer)
    second = client.post("/api/account/plea", json={"message": "two"}, headers=fencer)
    assert second.status_code == 409
    assert second.json()["detail"] == "plea_pending"


def test_deny_and_replea(client, auth_headers):
    fencer = auth_headers(email="f@example.com", role=Role.FENCER)
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)

    client.post("/api/account/plea", json={"message": "please"}, headers=fencer)
    queue = client.get("/api/admin/pleas", headers=admin).json()
    plea_id = queue[0]["id"]

    denied = client.post(f"/api/admin/pleas/{plea_id}/deny", headers=admin)
    assert denied.status_code == 200
    assert denied.json()["state"] == "denied"

    account = client.get("/api/account", headers=fencer).json()
    assert account["role"] == "fencer"

    # a denied account may plead again
    replea = client.post("/api/account/plea", json={}, headers=fencer)
    assert replea.status_code == 201
    assert replea.json()["state"] == "pending"

    mine = client.get("/api/account/plea", headers=fencer).json()
    assert mine["state"] == "pending"  # latest plea, not the denied one


def test_deciding_a_non_pending_plea_rejected(client, auth_headers):
    fencer = auth_headers(email="f@example.com", role=Role.FENCER)
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    client.post("/api/account/plea", json={}, headers=fencer)
    plea_id = client.get("/api/admin/pleas", headers=admin).json()[0]["id"]
    client.post(f"/api/admin/pleas/{plea_id}/grant", headers=admin)

    again = client.post(f"/api/admin/pleas/{plea_id}/grant", headers=admin)
    assert again.status_code == 409
    assert again.json()["detail"] == "plea_not_pending"


def test_no_plea_yet_returns_null_state(client, auth_headers):
    fencer = auth_headers(email="f@example.com", role=Role.FENCER)
    mine = client.get("/api/account/plea", headers=fencer).json()
    assert mine["state"] is None


def test_non_admin_cannot_decide_pleas(client, auth_headers):
    fencer = auth_headers(email="f@example.com", role=Role.FENCER)
    client.post("/api/account/plea", json={}, headers=fencer)
    organizer = auth_headers(email="o@example.com", role=Role.ORGANIZER)
    response = client.post("/api/admin/pleas/1/grant", headers=organizer)
    assert response.status_code == 403


# --- HR unbind and audit ---


def test_admin_unbinds_hr_id_and_audits(client, auth_headers):
    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import FencerProfileAudit

    fencer = auth_headers(email="jan@example.com", name="Jan", role=Role.FENCER)
    signup_and_bind = client.post(
        "/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer
    )
    assert signup_and_bind.status_code == 200
    account = client.get("/api/account", headers=fencer).json()
    assert account["hr_id"] == 10234

    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    unbound = client.post(f"/api/admin/accounts/{account['id']}/hr-unbind", headers=admin)
    assert unbound.status_code == 200
    assert unbound.json()["hr_id"] is None

    session = next(app.dependency_overrides[get_session]())
    entries = session.scalars(
        select(FencerProfileAudit).where(FencerProfileAudit.field == "hr_id")
    ).all()
    assert any(e.old_value == "10234" and e.new_value is None for e in entries)

    # the fencer can now bind the correct profile
    rebound = client.post(
        "/api/account/hr-binding", json={"hr_id": 8821}, headers=fencer
    )
    assert rebound.status_code == 200
    assert rebound.json()["hr_id"] == 8821


def test_fencer_still_cannot_rebind_without_admin_unbind(client, auth_headers):
    fencer = auth_headers(email="jan@example.com", name="Jan", role=Role.FENCER)
    client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=fencer)
    again = client.post("/api/account/hr-binding", json={"hr_id": 8821}, headers=fencer)
    assert again.status_code == 409
    assert again.json()["detail"] == "already_bound"


def test_hr_unbind_unknown_account_404(client, auth_headers):
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    response = client.post("/api/admin/accounts/999999/hr-unbind", headers=admin)
    assert response.status_code == 404


def test_admin_listing_flags_shared_hr_claims(client, auth_headers):
    first = auth_headers(email="a@example.com", name="A", role=Role.FENCER)
    second = auth_headers(email="b@example.com", name="B", role=Role.FENCER)
    client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=first)
    client.post("/api/account/hr-binding", json={"hr_id": 8821}, headers=second)

    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    accounts = {
        a["email"]: a for a in client.get("/api/admin/accounts", headers=admin).json()
    }
    assert accounts["a@example.com"]["hr_shared"] is False
    assert accounts["b@example.com"]["hr_shared"] is False

    third = auth_headers(email="c@example.com", name="C", role=Role.FENCER)
    client.post("/api/account/hr-binding", json={"hr_id": 10234}, headers=third)

    accounts = {
        a["email"]: a for a in client.get("/api/admin/accounts", headers=admin).json()
    }
    assert accounts["a@example.com"]["hr_shared"] is True
    assert accounts["c@example.com"]["hr_shared"] is True
    assert accounts["b@example.com"]["hr_shared"] is False

    account_id = accounts["c@example.com"]["id"]
    unbound = client.post(f"/api/admin/accounts/{account_id}/hr-unbind", headers=admin)
    assert unbound.json()["hr_shared"] is False

    accounts = {
        a["email"]: a for a in client.get("/api/admin/accounts", headers=admin).json()
    }
    assert accounts["a@example.com"]["hr_shared"] is False
