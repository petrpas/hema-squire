"""Team disciplines: pricing, capacity/waitlist, registration, rosters, the
composition deadline, export, and the no-team-discipline regression (design
team-disciplines, tasks.md section 10).

Note: `tests/test_team_lifecycle.py` covers an unrelated capability (console
team access / TournamentOrganizer CRUD) — this file is about the Team/
TeamMember roster model instead.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select

from app import pricing
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    Discipline,
    DisciplineKind,
    Fencer,
    Registration,
    Role,
    Team,
    TeamMember,
    Tournament,
)
from tests.conftest import publish

REGISTERED_AT = datetime(2026, 5, 1, 12, 0)


# ---------------------------------------------------------------------------
# 10.1 Pricing (in-memory ORM objects, no DB/API round trip needed — mirrors
# tests/test_pricing_itemized.py's style)
# ---------------------------------------------------------------------------


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        discounts=[],
        organizers=[],
        vs_year=2026,
        vs_series=1,
        # legacy-path fields the ORM default only applies on INSERT; an
        # in-memory-only Tournament needs them set explicitly
        weapon_rental_fee=0,
        afterparty_fee=0,
    )
    return Tournament(**{**defaults, **kwargs})


def team_discipline(tournament, fee=3000, team_min=3, team_max=4, code="LS"):
    return Discipline(
        tournament=tournament,
        slug=code,
        name=code,
        weapon=code,
        gender="",
        material="",
        kind=DisciplineKind.TEAM,
        team_min=team_min,
        team_max=team_max,
        capacity=8,
        fee=fee,
    )


def test_team_fee_counted_once_regardless_of_roster_size():
    tournament = make_tournament()
    discipline = team_discipline(tournament)
    small = Team(discipline=discipline, name="Small", waitlisted=False)
    small.members = [TeamMember(team=small, ordinal=0, name="A")]
    big = Team(discipline=discipline, name="Big", waitlisted=False)
    big.members = [TeamMember(team=big, ordinal=i, name=f"M{i}") for i in range(4)]

    registration_small = Registration(
        tournament=tournament, registered_at=REGISTERED_AT, entries=[], teams=[small],
        weapon_rentals=[],
    )
    registration_big = Registration(
        tournament=tournament, registered_at=REGISTERED_AT, entries=[], teams=[big],
        weapon_rentals=[],
    )
    assert pricing.registration_total(registration_small, tournament).local == 3000
    assert pricing.registration_total(registration_big, tournament).local == 3000


def test_two_teams_counted_twice():
    tournament = make_tournament()
    discipline = team_discipline(tournament)
    teams = [
        Team(discipline=discipline, name="Wolves", waitlisted=False),
        Team(discipline=discipline, name="Bears", waitlisted=False),
    ]
    registration = Registration(
        tournament=tournament, registered_at=REGISTERED_AT, entries=[], teams=teams,
        weapon_rentals=[],
    )
    assert pricing.registration_total(registration, tournament).local == 6000


def test_waitlisted_team_excluded_from_total():
    tournament = make_tournament()
    discipline = team_discipline(tournament)
    placed = Team(discipline=discipline, name="Placed", waitlisted=False)
    queued = Team(discipline=discipline, name="Queued", waitlisted=True)
    registration = Registration(
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[],
        teams=[placed, queued],
        weapon_rentals=[],
    )
    assert pricing.registration_total(registration, tournament).local == 3000


def test_discipline_scoped_discount_reaches_team_fee():
    tournament = make_tournament(
        discounts=[
            {
                "name": "10% off",
                "condition": {"kind": "discipline_count", "count": 1},
                "effect": {"kind": "percent", "value": 10},
                "scope": ["discipline"],
            }
        ]
    )
    discipline = team_discipline(tournament, fee=3000)
    # one individual discipline entry (satisfies the count condition) plus one team
    from app.models import RegistrationDiscipline

    individual = Discipline(
        tournament=tournament,
        slug="SB",
        name="SB",
        weapon="SB",
        gender="",
        material="",
        capacity=10,
        fee=1000,
    )
    team = Team(discipline=discipline, name="Wolves", waitlisted=False)
    registration = Registration(
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[RegistrationDiscipline(discipline=individual, is_substitute=False)],
        teams=[team],
        weapon_rentals=[],
    )
    # (1000 + 3000) * 0.9 = 3600
    assert pricing.registration_total(registration, tournament).local == 3600


def test_team_entry_does_not_satisfy_discipline_count_condition():
    tournament = make_tournament(
        discounts=[
            {
                "name": "2 disciplines",
                "condition": {"kind": "discipline_count", "count": 2},
                "effect": {"kind": "fixed", "value": 500},
                "scope": ["discipline"],
            }
        ]
    )
    discipline = team_discipline(tournament, fee=3000)
    from app.models import RegistrationDiscipline

    individual = Discipline(
        tournament=tournament,
        slug="SB",
        name="SB",
        weapon="SB",
        gender="",
        material="",
        capacity=10,
        fee=1000,
    )
    team = Team(discipline=discipline, name="Wolves", waitlisted=False)
    registration = Registration(
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[RegistrationDiscipline(discipline=individual, is_substitute=False)],
        teams=[team],
        weapon_rentals=[],
    )
    # one individual + one team is NOT "2 disciplines" for the count condition
    assert pricing.registration_total(registration, tournament).local == 1000 + 3000


def test_legacy_tournament_still_prices_team_fee_from_discipline_row():
    """Task 2.4: a legacy (non-itemized) tournament still prices a team's fee
    from the discipline row rather than treating teams specially."""
    tournament = make_tournament()  # no extra_items/discounts -> legacy pricing
    discipline = team_discipline(tournament, fee=2500)
    team = Team(discipline=discipline, name="Wolves", waitlisted=False)
    registration = Registration(
        tournament=tournament, registered_at=REGISTERED_AT, entries=[], teams=[team],
        weapon_rentals=[],
    )
    assert not pricing.uses_itemized_pricing(tournament)
    assert pricing.registration_total(registration, tournament).local == 2500


# ---------------------------------------------------------------------------
# API-level fixtures shared by 10.2-10.6
# ---------------------------------------------------------------------------


def setup_team_tournament(client, organizer, *, team_min=3, team_max=4, capacity=1, deadline=None):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05", "language": "cs"},
        headers=organizer,
    )
    patch = {"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]}
    if deadline is not None:
        patch["team_composition_deadline"] = deadline
    client.patch("/api/tournaments/cup", json=patch, headers=organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS",
            "weapon": "LS",
            "capacity": capacity,
            "fee": 3000,
            "kind": "team",
            "team_min": team_min,
            "team_max": team_max,
        },
        headers=organizer,
    )
    publish(client, organizer, "cup")


def register_team(client, headers, name="Wolves", code="LS", **overrides):
    payload = {"disciplines": [], "teams": [{"slug": code, "name": name}], **overrides}
    return client.post("/api/tournaments/cup/register", json=payload, headers=headers)


def db_session():
    return next(app.dependency_overrides[get_session]())


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


def mailbox_fixture():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    return mailer


# ---------------------------------------------------------------------------
# 10.2 Capacity
# ---------------------------------------------------------------------------


def test_team_discipline_counted_in_teams(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=2)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register_team(client, fencer, name="Wolves")

    availability = client.get("/api/tournaments/cup/availability").json()
    row = availability[0]
    assert row["kind"] == "team"
    assert row["taken"] == 1
    assert row["capacity"] == 2
    assert row["free"] == 1
    assert row["team_min"] == 3
    assert row["team_max"] == 4


def test_team_entry_freezes_a_team_discipline(client, auth_headers):
    """design discipline-identity-modal D6: `identity_frozen` covers a team
    discipline once a team enters it, unlike `taken_seats`, which ignores
    teams entirely."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=2)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register_team(client, fencer, name="Wolves")

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    discipline = next(d for d in detail["disciplines"] if d["slug"] == "LS")
    assert discipline["identity_frozen"] is True


def test_team_waitlisted_at_capacity(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=1)
    first = auth_headers(email="f1@example.com", name="F1")
    second = auth_headers(email="f2@example.com", name="F2")

    r1 = register_team(client, first, name="Wolves")
    assert r1.status_code == 201
    assert r1.json()["teams"][0]["waitlisted"] is False
    assert r1.json()["total_amount"] == 3000

    r2 = register_team(client, second, name="Bears")
    assert r2.status_code == 201  # never rejected, unlike a full individual discipline
    assert r2.json()["teams"][0]["waitlisted"] is True
    assert r2.json()["total_amount"] == 0

    availability = client.get("/api/tournaments/cup/availability").json()
    assert availability[0]["taken"] == 1
    assert availability[0]["queue_length"] == 1


def test_full_individual_discipline_unaffected_by_teams(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05", "language": "cs"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 1, "fee": 500},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )
    publish(client, organizer, "cup")

    a = auth_headers(email="a@example.com", name="A")
    b = auth_headers(email="b@example.com", name="B")
    client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["SB"], "teams": []}, headers=a
    )
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": [], "teams": [{"slug": "LS", "name": "Wolves"}]},
        headers=b,
    )
    availability = {
        row["slug"]: row
        for row in client.get("/api/tournaments/cup/availability").json()
    }
    assert availability["SB"]["free"] == 0
    assert availability["LS"]["taken"] == 1
    assert availability["LS"]["free"] == 4


# ---------------------------------------------------------------------------
# 10.3 Registration
# ---------------------------------------------------------------------------


def test_team_only_registration_accepted_priced_confirmed(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register_team(client, fencer, name="Wolves")
    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == 3000
    assert body["vs"] is not None
    assert body["state"] == "reserved"
    assert body["entries"] == []
    assert len(body["teams"]) == 1
    assert body["teams"][0]["name"] == "Wolves"


def test_two_teams_by_one_fencer(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register_team(
        client,
        fencer,
        name="ignored",
        teams=[{"slug": "LS", "name": "Wolves"}, {"slug": "LS", "name": "Wolves"}],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == 6000
    assert len(body["teams"]) == 2
    assert body["teams"][0]["name"] == body["teams"][1]["name"] == "Wolves"  # duplicate names OK


def test_team_removal_on_amendment_drops_roster(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    # a second, individual discipline so the amendment removing the team
    # doesn't also try to leave the registration with nothing at all
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 5, "fee": 500},
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")

    created = register_team(client, fencer, name="Wolves", disciplines=["SB"]).json()
    team_id = created["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
        headers=fencer,
    )

    amended = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={"disciplines": ["SB"], "teams": []},
        headers=fencer,
    )
    assert amended.status_code == 200
    body = amended.json()
    assert body["teams"] == []
    assert body["total_amount"] == 500

    session = db_session()
    assert session.scalar(select(TeamMember).where(TeamMember.team_id == team_id)) is None
    assert session.get(Team, team_id) is None


# ---------------------------------------------------------------------------
# 10.4 Roster
# ---------------------------------------------------------------------------


def test_roster_maximum_enforced_minimum_not(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_min=3, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    # below minimum accepted
    below = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},
        headers=fencer,
    )
    assert below.status_code == 200
    assert len(below.json()["members"]) == 1

    # over maximum rejected
    over = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": f"M{i}"} for i in range(5)]},
        headers=fencer,
    )
    assert over.status_code == 422


def test_roster_ordering_preserved(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}]},
        headers=fencer,
    )
    assert [m["name"] for m in response.json()["members"]] == ["Charlie", "Alice", "Bob"]

    read_back = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert [m["name"] for m in read_back["teams"][0]["members"]] == ["Charlie", "Alice", "Bob"]


def test_unbound_member_accepted(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "HR Unknown Person"}]},
        headers=fencer,
    )
    assert response.status_code == 200
    member = response.json()["members"][0]
    assert member["name"] == "HR Unknown Person"
    assert member["hr_id"] is None


def test_roster_editable_after_amendments_close(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"amendments_close": "2020-01-01"},  # long past
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},
        headers=fencer,
    )
    assert response.status_code == 200

    # but adding/removing a team itself is still an amendment, and is refused
    amend = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={
            "disciplines": [],
            "teams": [{"slug": "LS", "name": "Wolves"}, {"slug": "LS", "name": "Bears"}],
        },
        headers=fencer,
    )
    assert amend.status_code == 403


def test_roster_editing_refused_on_cancelled_registration(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},
        headers=fencer,
    )
    assert response.status_code == 409


def test_roster_edit_moves_no_money_vs_or_email(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    mailer = mailbox_fixture()
    try:
        fencer = auth_headers(email="f1@example.com", name="F1")
        created = register_team(client, fencer, name="Wolves").json()
        team_id = created["teams"][0]["id"]
        vs_before = created["vs"]
        total_before = created["total_amount"]
        mailer.sent.clear()

        response = client.put(
            f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
            json={"members": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
            headers=fencer,
        )
        assert response.status_code == 200

        state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
        assert state["vs"] == vs_before
        assert state["total_amount"] == total_before
        assert state["refund_state"] == "not_applicable"
        assert mailer.sent == []
    finally:
        app.dependency_overrides.pop(get_mailer, None)


# ---------------------------------------------------------------------------
# 10.5 Deadline
# ---------------------------------------------------------------------------


def test_below_minimum_flag_only_after_deadline(client, auth_headers):
    organizer = auth_headers()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    setup_team_tournament(client, organizer, deadline=yesterday)
    fencer = auth_headers(email="f1@example.com", name="F1")
    created = register_team(client, fencer, name="Wolves").json()
    team_id = created["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},  # below team_min of 3
        headers=fencer,
    )

    console = client.get("/api/tournaments/cup/teams", headers=organizer).json()
    team_row = console[0]["teams"][0]
    assert team_row["below_minimum"] is True
    # the team is unaffected: still entered, still holding its capacity slot
    assert team_row["waitlisted"] is False
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["total_amount"] == 3000
    assert state["state"] == "reserved"


def test_no_flag_before_deadline_or_without_one(client, auth_headers):
    organizer = auth_headers()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    setup_team_tournament(client, organizer, deadline=tomorrow)
    fencer = auth_headers(email="f1@example.com", name="F1")
    created = register_team(client, fencer, name="Wolves").json()
    team_id = created["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},
        headers=fencer,
    )
    console = client.get("/api/tournaments/cup/teams", headers=organizer).json()
    assert console[0]["teams"][0]["below_minimum"] is False


def test_roster_editable_day_before_tournament(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "Swapped In"}]},
        headers=fencer,
    )
    assert response.status_code == 200


def test_composition_reminder_sent_once_and_skips_complete_rosters(client, auth_headers):
    organizer = auth_headers()
    soon = (date.today() + timedelta(days=3)).isoformat()
    setup_team_tournament(client, organizer, capacity=5, deadline=soon)
    # reminder_day defaults to 5, so a deadline 3 days out is within the window
    short = auth_headers(email="short@example.com", name="Short")
    complete = auth_headers(email="complete@example.com", name="Complete")

    short_team = register_team(client, short, name="Short Team").json()["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{short_team}/roster",
        json={"members": [{"name": "A"}]},
        headers=short,
    )
    complete_team = register_team(client, complete, name="Complete Team").json()["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{complete_team}/roster",
        json={"members": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
        headers=complete,
    )

    mailer = mailbox_fixture()
    try:
        from app import scheduler

        session = db_session()
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        sent = scheduler.process_composition_reminders(session, tournament, mailer)
        assert sent == 1
        assert len(mailer.sent) == 1
        body = mailer.sent[0].get_body(("plain",)).get_content()
        assert "Short Team" in body
        assert "Complete Team" not in body

        # second tick: already reminded, nothing resent
        mailer.sent.clear()
        sent_again = scheduler.process_composition_reminders(session, tournament, mailer)
        assert sent_again == 0
        assert mailer.sent == []
    finally:
        app.dependency_overrides.pop(get_mailer, None)


def test_no_deadline_means_no_reminder(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)  # no deadline
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},
        headers=fencer,
    )
    mailer = mailbox_fixture()
    try:
        from app import scheduler

        session = db_session()
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        assert scheduler.process_composition_reminders(session, tournament, mailer) == 0
        assert mailer.sent == []
    finally:
        app.dependency_overrides.pop(get_mailer, None)


# ---------------------------------------------------------------------------
# 10.6 Export
# ---------------------------------------------------------------------------


def fresh_deployment(client, auth_headers):
    """Point the app at an empty database and return (headers, client) for it
    — the only way to restore a document beside its original, since VS is
    unique across the deployment (mirrors tests/test_export_json.py)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as OrmSession
    from sqlalchemy.pool import StaticPool

    from app.db import Base

    fresh = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(fresh)

    def fresh_session():
        with OrmSession(fresh) as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    # role=FENCER sidesteps auth_headers' role-promotion step, which targets
    # the *original* engine via a fixture closure and would crash here (the
    # signup itself already lands on the fresh engine via the override
    # above); restore() grants console access via TournamentOrganizer
    # regardless of the caller's global Role, so no promotion is needed
    new_organizer = auth_headers(email="new-owner@example.com", name="New Owner", role=Role.FENCER)
    return new_organizer, client


def test_v6_roundtrip_with_teams_and_rosters(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=1)
    fencer = auth_headers(email="f1@example.com", name="F1")
    waiting = auth_headers(email="f2@example.com", name="F2")

    created = register_team(client, fencer, name="Wolves").json()
    team_id = created["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={
            "members": [
                {"name": "A", "hr_id": 111, "club": "Brno HEMA", "nationality": "CZE"},
                {"name": "B"},
            ]
        },
        headers=fencer,
    )
    register_team(client, waiting, name="Bears")  # waitlisted (capacity 1)

    export = client.get("/api/tournaments/cup/export/json", headers=organizer)
    assert export.status_code == 200, export.text
    doc = export.json()
    assert doc["schema_version"] == 7
    assert doc["disciplines"][0]["kind"] == "team"
    assert doc["disciplines"][0]["team_min"] == 3

    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post("/api/tournaments/restore", json=doc, headers=new_organizer)
    assert restore.status_code == 201, restore.text

    export2 = restore_client.get("/api/tournaments/cup/export/json", headers=new_organizer).json()
    reg_teams = {r["fencer_email"]: r["teams"] for r in export2["registrations"]}
    wolves = reg_teams["f1@example.com"][0]
    assert wolves["name"] == "Wolves"
    assert wolves["waitlisted"] is False
    assert [m["name"] for m in wolves["members"]] == ["A", "B"]
    assert wolves["members"][0]["hr_id"] == 111
    bears = reg_teams["f2@example.com"][0]
    assert bears["waitlisted"] is True

    # no account was created for a roster member (design D4)
    session = db_session()
    assert session.scalar(select(Fencer).where(Fencer.email == "f1@example.com")) is not None
    member_as_account = session.scalar(select(Fencer).where(Fencer.display_name == "A"))
    assert member_as_account is None


def test_v5_fixture_restores_with_no_teams(client, auth_headers):
    organizer = auth_headers()
    v5_document = {
        "schema_version": 5,
        "exported_at": "2026-01-01T00:00:00+00:00",
        "tournament": {
            "slug": "legacy-v5",
            "display_name": "Legacy",
            "date": "2026-11-01",
            "language": "cs",
            "reservation_validity_days": 10,
            "reminder_day": 5,
            "amount_tolerance_percent": 5,
            "refundable_until": None,
            "bank_account": None,
            "unpaid_list_treatment": "greyed",
            "early_bird_until": None,
            "weapon_rental_fee": 0,
            "weapon_rental_fee_early": None,
            "afterparty_fee": 0,
            "afterparty_fee_early": None,
            "location": "Prague",
            "description": None,
            "qualification_open": True,
            "qualification_criteria": None,
            "registration_instructions": None,
            "local_currency": "CZK",
            "eur_payments_enabled": False,
            "eur_rate": None,
            "organizers": [{"name": "Legacy Org", "link": None}],
            "discounts": [],
            "registration_opens": None,
            "registration_closes": None,
            "vs_year": 2026,
            "vs_series": 50,
            "vs_next_seq": 1,
        },
        "disciplines": [
            {"code": "LS", "name": "Longsword", "capacity": 10, "fee": 500, "fee_early": None,
             "fee_eur": None, "fee_early_eur": None},
        ],
        "extra_items": [],
        "fencers": [],
        "registrations": [],
        "bank_transactions": [],
        "import_batches": [],
        "decisions": [],
        "rules": [],
    }
    restore = client.post("/api/tournaments/restore", json=v5_document, headers=organizer)
    assert restore.status_code == 201, restore.text
    detail = client.get("/api/tournaments/legacy-v5", headers=organizer).json()
    assert detail["disciplines"][0]["kind"] == "individual"
    assert detail["disciplines"][0]["team_min"] is None
    assert detail["team_composition_deadline"] is None


def test_teams_absent_from_sheets_export(client, auth_headers):
    from app.sheets_export import get_sheets_client_factory
    from tests.test_sheets_export import InMemorySheets

    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05", "language": "cs"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "SA", "weapon": "SA", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "output_sheet_url": "https://sheets.example/cup",
            "location": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
        },
        headers=organizer,
    )
    publish(client, organizer, "cup")

    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "teams": [{"slug": "SA", "name": "Wolves"}]},
        headers=fencer,
    )
    team_id = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()[
        "teams"
    ][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "Roster Member Not A Fencer"}]},
        headers=fencer,
    )

    sheets = InMemorySheets()
    app.dependency_overrides[get_sheets_client_factory] = lambda: (lambda tournament: sheets)
    try:
        response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
        assert response.status_code == 200, response.text
        # exactly the worksheets an individual-only tournament would produce —
        # no "SA" team-discipline worksheet
        assert response.json()["worksheets"] == ["Fencers", "LS"]
        assert "SA" not in sheets.worksheets
        fencers_rows = [row[1] for row in sheets.worksheets["Fencers"][1:]]
        assert fencers_rows == ["Jan Novák"]
        assert "Roster Member Not A Fencer" not in fencers_rows
    finally:
        app.dependency_overrides.pop(get_sheets_client_factory, None)


# ---------------------------------------------------------------------------
# 3.4 / 3.5 Setup-time guards
# ---------------------------------------------------------------------------


def test_discipline_kind_frozen_once_referenced(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register_team(client, fencer, name="Wolves")

    response = client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"weapon": "LS", "kind": "individual", "capacity": 5, "fee": 3000},
        headers=organizer,
    )
    assert response.status_code == 409

    # bounds/fee still editable, just not the kind
    response = client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={
            "weapon": "LS", "kind": "team", "team_min": 3, "team_max": 4,
            "capacity": 5, "fee": 3500,
        },
        headers=organizer,
    )
    assert response.status_code == 200
    assert response.json()["fee"] == 3500


def test_discipline_kind_editable_before_any_registration(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    response = client.patch(
        "/api/tournaments/cup/disciplines/LS",
        json={"weapon": "LS", "kind": "individual", "capacity": 5, "fee": 3000},
        headers=organizer,
    )
    assert response.status_code == 200
    assert response.json()["kind"] == "individual"


def test_hr_category_map_excludes_team_disciplines(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    response = client.patch(
        "/api/tournaments/cup",
        json={"hr_category_map": {"LS": "Some HR Category"}},
        headers=organizer,
    )
    assert response.status_code == 422


def test_team_discipline_absent_from_hr_category_map_options(client, auth_headers):
    """Task 3.5: whatever builds the map's options never offers a team
    discipline — verified through take_snapshot's own code-collection step,
    which only ever iterates individual-kind codes."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 5, "fee": 500},
        headers=organizer,
    )
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    slugs = [d.slug for d in tournament.disciplines if d.kind == DisciplineKind.INDIVIDUAL]
    assert slugs == ["SB"]  # the team discipline "LS" never appears


# ---------------------------------------------------------------------------
# 10.7 Regression: no team discipline -> unchanged behavior
# ---------------------------------------------------------------------------


def test_no_team_discipline_regression(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05", "language": "cs"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 2, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == 800
    assert body["teams"] == []

    availability = client.get("/api/tournaments/cup/availability").json()
    assert availability[0]["kind"] == "individual"
    assert availability[0]["team_min"] is None
    assert availability[0]["team_max"] is None

    export = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    assert export["registrations"][0]["teams"] == []
    assert export["disciplines"][0]["kind"] == "individual"
