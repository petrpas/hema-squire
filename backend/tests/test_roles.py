"""Global role ladder, deployment Owner from config, creation gate, and
per-tournament console access (owner/team/stranger)."""

import pytest

from app.config import settings
from app.models import Role

TOURNAMENT = {"slug": "cup", "display_name": "Cup", "date": "2026-12-05"}


def create_tournament(client, headers):
    return client.post("/api/tournaments", json=TOURNAMENT, headers=headers)


# --- creation gate (global role ladder) ---


def test_fencer_cannot_create_tournament(client, auth_headers):
    fencer = auth_headers(email="plain@example.com", role=Role.FENCER)
    response = create_tournament(client, fencer)
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_role"


def test_organizer_creates_and_becomes_tournament_owner(client, auth_headers, engine):
    organizer = auth_headers()
    response = create_tournament(client, organizer)
    assert response.status_code == 201
    body = response.json()
    assert body["owner_id"] is not None

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import Fencer, Tournament, TournamentOrganizer

    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        creator = session.scalar(
            select(Fencer).where(Fencer.email == "organizer@example.com")
        )
        assert tournament.owner_id == creator.id
        # ownership implies access; no duplicate team row is created
        assert session.scalar(select(TournamentOrganizer.id)) is None


def test_admin_outranks_organizer(client, auth_headers):
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    assert create_tournament(client, admin).status_code == 201


def test_admin_retains_fencer_capabilities(client, auth_headers):
    """Spec: every account keeps Fencer capabilities regardless of role."""
    organizer = auth_headers()
    create_tournament(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Praha", "organizers": [{"name": "Rocha", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 100},
        headers=organizer,
    )
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=admin
    )
    assert response.status_code == 201


# --- deployment Owner from configuration ---


@pytest.fixture
def owner_email(monkeypatch):
    monkeypatch.setattr(settings, "owner_email", "owner@example.com")


def test_config_owner_outranks_all_without_stored_role(client, auth_headers, owner_email):
    # the account signs up *after* deployment config was set, as a plain fencer
    owner = auth_headers(email="owner@example.com", name="Owner", role=Role.FENCER)
    assert create_tournament(client, owner).status_code == 201

    account = client.get("/api/account", headers=owner).json()
    assert account["role"] == "fencer"  # nothing stored in the DB
    assert account["is_deployment_owner"] is True


def test_owner_flag_not_leaked_to_others(client, auth_headers, owner_email):
    other = auth_headers(email="plain@example.com", role=Role.FENCER)
    account = client.get("/api/account", headers=other).json()
    assert account["is_deployment_owner"] is False


# --- console access: tournament owner OR team member, no global bypass ---


def edit_location(client, headers):
    return client.patch(
        "/api/tournaments/cup", json={"location": "Brno"}, headers=headers
    )


def test_console_access_owner_and_team_only(client, auth_headers):
    owner = auth_headers()
    create_tournament(client, owner)

    stranger = auth_headers(email="stranger@example.com", role=Role.FENCER)
    assert edit_location(client, stranger).status_code == 403

    # a plain fencer added to the team gains console access
    auth_headers(email="helper@example.com", name="Helper", role=Role.FENCER)
    added = client.post(
        "/api/tournaments/cup/team",
        json={"email": "helper@example.com"},
        headers=owner,
    )
    assert added.status_code == 201
    helper_login = client.post(
        "/api/auth/login", json={"email": "helper@example.com", "password": "correct-horse"}
    )
    helper = {"Authorization": f"Bearer {helper_login.json()['token']}"}
    assert edit_location(client, helper).status_code == 200

    assert edit_location(client, owner).status_code == 200


def test_global_admin_has_no_console_access(client, auth_headers):
    """Admins manage people, not tournaments (design D3)."""
    owner = auth_headers()
    create_tournament(client, owner)
    admin = auth_headers(email="admin@example.com", role=Role.ADMIN)
    assert edit_location(client, admin).status_code == 403
