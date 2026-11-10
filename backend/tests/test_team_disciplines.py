"""Team disciplines: pricing, capacity/waitlist, registration, rosters, the
composition deadline, export, and the no-team-discipline regression (design
team-disciplines, tasks.md section 10).

Note: `tests/test_team_lifecycle.py` covers an unrelated capability (console
team access / TournamentOrganizer CRUD) — this file is about the Team/
TeamMember roster model instead.
"""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app import pricing
from app.db import get_session
from app.export_json import SCHEMA_VERSION
from app.mail import get_mailer
from app.main import app
from app.models import (
    Discipline,
    DisciplineKind,
    Fencer,
    Registration,
    Role,
    RosterChange,
    Team,
    TeamMember,
    Tournament,
)
from tests.conftest import (
    FAR_EAST,
    FAR_WEST,
    pay_registration,
    publish,
    set_features,
    today_in,
    today_local,
)

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
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[],
        teams=[small],
        weapon_rentals=[],
    )
    registration_big = Registration(
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[],
        teams=[big],
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
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[],
        teams=teams,
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
        tournament=tournament,
        registered_at=REGISTERED_AT,
        entries=[],
        teams=[team],
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
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    patch = {"city": "Brno", "organizers": [{"name": "Cup Org", "link": None}]}
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
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}]},
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
            "slug": "LS",
            "weapon": "LS",
            "capacity": 5,
            "fee": 3000,
            "kind": "team",
            "team_min": 3,
            "team_max": 4,
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
        row["slug"]: row for row in client.get("/api/tournaments/cup/availability").json()
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


def test_roster_nationality_stored_as_country_code(client, auth_headers):
    """One vocabulary down the nationality column, whatever the source spelled
    (spec team-disciplines, A roster member is a named person). The HR search
    the client echoes back writes the fighters index's own English name, which
    would otherwise read "Czech Republic" beside a fencer table reading "CZ"."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={
            "members": [
                {"name": "A", "nationality": "Czech Republic"},
                {"name": "B", "nationality": "CZE"},
                # no country can be read from it, so it stands as given
                {"name": "C", "nationality": "Mordor"},
                {"name": "D"},
            ]
        },
        headers=fencer,
    )
    assert response.status_code == 200, response.text
    assert [m["nationality"] for m in response.json()["members"]] == [
        "CZ",
        "CZ",
        "Mordor",
        None,
    ]

    read_back = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert [m["nationality"] for m in read_back["teams"][0]["members"]] == [
        "CZ",
        "CZ",
        "Mordor",
        None,
    ]


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
# A roster member keeps its identity across saves
# ---------------------------------------------------------------------------


def put_roster(client, team_id, members, headers):
    return client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": members},
        headers=headers,
    )


def log_rows(team_id):
    session = db_session()
    return list(
        session.scalars(
            select(RosterChange).where(RosterChange.team_id == team_id).order_by(RosterChange.id)
        ).all()
    )


def test_corrected_nationality_keeps_the_member(client, auth_headers):
    """A save states the roster it wants and is applied as a difference: the
    corrected member is the same member afterwards, and the others are
    untouched (spec team-disciplines, A correction keeps the member)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    before = put_roster(
        client,
        team_id,
        [{"name": "A", "nationality": "SK"}, {"name": "B"}, {"name": "C"}],
        fencer,
    ).json()["members"]

    corrected = [dict(m) for m in before]
    corrected[0]["nationality"] = "CZ"
    after = put_roster(client, team_id, corrected, fencer).json()["members"]

    assert [m["id"] for m in after] == [m["id"] for m in before]
    assert after[0]["nationality"] == "CZ"
    assert [m["nationality"] for m in after[1:]] == [None, None]
    entries = log_rows(team_id)
    # three additions from the first save, then the one correction
    assert [(e.kind, e.field, e.before, e.after) for e in entries[3:]] == [
        ("edited", "nationality", "SK", "CZ")
    ]


def test_reordering_identifies_nobody_differently(client, auth_headers):
    """Order is rewritten from the order stated and carries no identity, so a
    reorder changes nothing anybody could dispute and the log gains no entry
    (spec team-disciplines, A reorder is not a change)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    before = put_roster(
        client, team_id, [{"name": n} for n in ("A", "B", "C", "D")], fencer
    ).json()["members"]
    entries_before = len(log_rows(team_id))

    reversed_order = [dict(m) for m in reversed(before)]
    after = put_roster(client, team_id, reversed_order, fencer).json()["members"]

    assert [m["name"] for m in after] == ["D", "C", "B", "A"]
    assert [m["id"] for m in after] == [m["id"] for m in reversed(before)]
    assert len(log_rows(team_id)) == entries_before


def test_two_members_alike_are_still_two_members(client, auth_headers):
    """Two members may be identical in every stored field; their identities
    are still distinct, and a save applies to the one it names (spec
    team-disciplines, Two members alike are still two members)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    before = put_roster(
        client, team_id, [{"name": "Jan Novak"}, {"name": "Jan Novak"}], fencer
    ).json()["members"]
    assert before[0]["id"] != before[1]["id"]

    first = [dict(m) for m in before]
    first[0]["name"] = "Jan Novak the elder"
    after_first = put_roster(client, team_id, first, fencer).json()["members"]
    assert [m["name"] for m in after_first] == ["Jan Novak the elder", "Jan Novak"]
    assert [m["id"] for m in after_first] == [m["id"] for m in before]

    second = [dict(m) for m in after_first]
    second[1]["name"] = "Jan Novak the younger"
    after_second = put_roster(client, team_id, second, fencer).json()["members"]
    assert [m["name"] for m in after_second] == [
        "Jan Novak the elder",
        "Jan Novak the younger",
    ]
    assert [m["id"] for m in after_second] == [m["id"] for m in before]


def test_a_member_added_and_a_member_removed_in_one_save(client, auth_headers):
    """The three stated keep their identities, the omitted one is removed, and
    the one stated without an identity is added (spec team-disciplines)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    before = put_roster(
        client, team_id, [{"name": n} for n in ("A", "B", "C", "D")], fencer
    ).json()["members"]
    entries_before = len(log_rows(team_id))

    kept = [dict(m) for m in before if m["name"] != "C"]
    after = put_roster(client, team_id, [*kept, {"name": "E"}], fencer).json()["members"]

    assert [m["name"] for m in after] == ["A", "B", "D", "E"]
    assert [m["id"] for m in after[:3]] == [m["id"] for m in kept]
    new_entries = log_rows(team_id)[entries_before:]
    assert sorted((e.kind, e.member_name) for e in new_entries) == [
        ("added", "E"),
        ("removed", "C"),
    ]
    # the removed member is retained, not erased: still there, marked
    session = db_session()
    removed = session.scalars(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.removed_at.is_not(None))
    ).all()
    assert [m.name for m in removed] == ["C"]


def test_a_foreign_member_id_is_refused(client, auth_headers):
    """An id that is not a member of this team makes the request a statement
    about some other roster. Refused rather than ignored, which would silently
    add a member the sender meant to move (design D1)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=2)
    fencer = auth_headers(email="f1@example.com", name="F1")
    teams = register_team(
        client,
        fencer,
        teams=[{"slug": "LS", "name": "Wolves"}, {"slug": "LS", "name": "Bears"}],
    ).json()["teams"]
    wolves, bears = teams[0]["id"], teams[1]["id"]
    theirs = put_roster(client, bears, [{"name": "Theirs"}], fencer).json()["members"][0]

    refused = put_roster(client, wolves, [{"name": "Ours"}, dict(theirs)], fencer)
    assert refused.status_code == 422
    assert refused.json()["detail"] == {"member_not_on_roster": theirs["id"]}
    # nothing of the refused save was applied
    assert (
        client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["teams"][0][
            "members"
        ]
        == []
    )
    assert [
        m["name"] for m in put_roster(client, bears, [dict(theirs)], fencer).json()["members"]
    ] == ["Theirs"]


def test_the_same_member_stated_twice_is_refused(client, auth_headers):
    """One member cannot be two places on one roster. Stating its id twice is
    not a roster, so it is refused the same way a foreign id is."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    member = put_roster(client, team_id, [{"name": "A"}], fencer).json()["members"][0]

    refused = put_roster(client, team_id, [dict(member), dict(member)], fencer)
    assert refused.status_code == 422
    assert refused.json()["detail"] == {"member_not_on_roster": member["id"]}


# ---------------------------------------------------------------------------
# A removed roster member is retained
# ---------------------------------------------------------------------------


def test_a_removed_member_counts_for_nothing(client, auth_headers):
    """A removed member is excluded from everything that states a roster or
    counts one. Each surface reads `len(team.members)` in its own file, so
    each is asked here (spec team-disciplines, A removed member counts for
    nothing)."""
    organizer = auth_headers()
    # the deadline is already past, so the below-minimum mark is live
    yesterday = (today_local() - timedelta(days=1)).isoformat()
    setup_team_tournament(client, organizer, team_min=3, team_max=4, deadline=yesterday)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    four = put_roster(client, team_id, [{"name": n} for n in ("A", "B", "C", "D")], fencer).json()[
        "members"
    ]

    kept = [dict(m) for m in four if m["name"] != "D"]
    after = put_roster(client, team_id, kept, fencer)
    assert [m["name"] for m in after.json()["members"]] == ["A", "B", "C"]

    # the entering fencer's own detail page
    detail = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert [m["name"] for m in detail["teams"][0]["members"]] == ["A", "B", "C"]
    # the organizer's teams view: three members, and not below a minimum of 3
    console = client.get("/api/tournaments/cup/teams", headers=organizer).json()
    assert [m["name"] for m in console[0]["teams"][0]["members"]] == ["A", "B", "C"]
    assert console[0]["teams"][0]["below_minimum"] is False
    # the Queue phase's count of a team's members
    queue = client.get("/api/tournaments/cup/queue/teams/LS", headers=organizer).json()
    assert queue[0]["members"] == 3
    # the public entrants roster
    entrants = client.get("/api/tournaments/cup/entrants").json()
    team_rows = [t for r in entrants["rosters"] for t in r["seated"] + r["queued"]]
    assert [m["name"] for m in team_rows[0]["members"]] == ["A", "B", "C"]
    # the backup document
    doc = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    exported = doc["registrations"][0]["teams"][0]
    assert [m["name"] for m in exported["members"]] == ["A", "B", "C"]


def test_a_removed_member_does_not_earn_a_composition_reminder(client, auth_headers):
    """The scheduler's completeness test and the mail's "have N of M" both
    count the live roster; a removed member neither triggers the reminder nor
    inflates the count it states."""
    organizer = auth_headers()
    soon = (today_local() + timedelta(days=3)).isoformat()
    setup_team_tournament(client, organizer, capacity=5, deadline=soon)
    complete = auth_headers(email="complete@example.com", name="Complete")
    team_id = register_team(client, complete, name="Complete Team").json()["teams"][0]["id"]
    four = put_roster(
        client, team_id, [{"name": n} for n in ("A", "B", "C", "D")], complete
    ).json()["members"]
    # still complete at three: no reminder is due
    put_roster(client, team_id, [dict(m) for m in four[:3]], complete)

    mailer = mailbox_fixture()
    try:
        from app import scheduler

        session = db_session()
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        assert scheduler.process_composition_reminders(session, tournament, mailer) == 0

        # drop one more and the team is short, with the mail stating two
        put_roster(client, team_id, [dict(m) for m in four[:2]], complete)
        session = db_session()
        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        assert scheduler.process_composition_reminders(session, tournament, mailer) == 1
        body = mailer.sent[0].get_body(("plain",)).get_content()
        assert "2" in body
        assert "C" not in [line.strip() for line in body.splitlines()]
    finally:
        app.dependency_overrides.pop(get_mailer, None)


def test_a_removal_is_not_an_erasure(client, auth_headers):
    """The removed member is reachable as the roster's history, carrying the
    moment it was removed and who removed it (spec team-disciplines)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    two = put_roster(client, team_id, [{"name": "A"}, {"name": "B"}], fencer).json()["members"]
    put_roster(client, team_id, [dict(two[0])], fencer)

    session = db_session()
    team = session.get(Team, team_id)
    assert [m.name for m in team.members] == ["A"]
    assert [m.name for m in team.removed_members] == ["B"]
    gone = team.removed_members[0]
    assert gone.id == two[1]["id"]
    assert gone.removed_at is not None
    actor = session.get(Fencer, gone.removed_by_fencer_id)
    assert actor is not None and actor.email == "f1@example.com"


def test_restored_rather_than_retyped(client, auth_headers):
    """A restore returns the same member, not a copy: whatever the tournament
    has decided about that person is still about them (spec
    team-disciplines)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    four = put_roster(client, team_id, [{"name": n} for n in ("A", "B", "C", "D")], fencer).json()[
        "members"
    ]
    put_roster(client, team_id, [dict(m) for m in four[:3]], fencer)

    restored = put_roster(client, team_id, [dict(m) for m in four], fencer).json()["members"]
    assert [m["id"] for m in restored] == [m["id"] for m in four]
    assert [m["name"] for m in restored] == ["A", "B", "C", "D"]
    session = db_session()
    assert session.get(Team, team_id).removed_members == []
    kinds = [e.kind for e in log_rows(team_id)]
    assert kinds[-2:] == ["removed", "restored"]


def test_a_full_roster_has_no_room_to_restore_into(client, auth_headers):
    """A restore is a member of the roster the save states, so the maximum
    refuses it the way it refuses any other roster too large, naming the
    maximum (spec team-disciplines)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    four = put_roster(client, team_id, [{"name": n} for n in ("A", "B", "C", "D")], fencer).json()[
        "members"
    ]
    # D out, E in: the roster is full again, and D is the removed one
    full = put_roster(
        client, team_id, [*[dict(m) for m in four[:3]], {"name": "E"}], fencer
    ).json()["members"]

    # D back without letting anybody go: a roster of five, which is one too many
    refused = put_roster(client, team_id, [*[dict(m) for m in full], dict(four[3])], fencer)
    assert refused.status_code == 422
    assert refused.json()["detail"] == {"roster_over_maximum": 4}
    session = db_session()
    assert [m.name for m in session.get(Team, team_id).removed_members] == ["D"]


# ---------------------------------------------------------------------------
# The organizer's own route
# ---------------------------------------------------------------------------


def console_put_roster(client, team_id, members, headers):
    return client.put(
        f"/api/tournaments/cup/teams/{team_id}/roster",
        json={"members": members},
        headers=headers,
    )


def test_the_organizer_swaps_a_member_at_the_venue(client, auth_headers):
    """A team arrives and the fencer who entered it cannot reach their editor.
    The organizer acts for them: the roster states the new member, the log
    holds both changes naming the organizer, and the registration is unchanged
    (spec team-disciplines, Organizer's teams view)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    three = put_roster(client, team_id, [{"name": n} for n in ("A", "B", "C")], fencer).json()[
        "members"
    ]

    swapped = console_put_roster(
        client,
        team_id,
        [*[dict(m) for m in three[:2]], {"name": "Substitute"}],
        organizer,
    )
    assert swapped.status_code == 200, swapped.text
    body = swapped.json()
    assert [m["name"] for m in body["members"]] == ["A", "B", "Substitute"]
    assert [m["name"] for m in body["removed_members"]] == ["C"]
    # the log is one story: the entrant's three additions and the organizer's
    # two changes, the organizer's named as theirs
    organizer_entries = [e for e in body["log"] if e["by_organizer"]]
    assert sorted((e["kind"], e["member_name"]) for e in organizer_entries) == [
        ("added", "Substitute"),
        ("removed", "C"),
    ]
    assert {e["actor"] for e in organizer_entries} == {"Organizer"}
    assert [e["by_organizer"] for e in body["log"] if not e["by_organizer"]] == [
        False,
        False,
        False,
    ]


def test_the_organizers_route_refuses_a_fencer(client, auth_headers):
    """The console's gate is `require_console_access`; the entrant's own route
    keeps checking ownership and nothing else changed about it."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=3)
    fencer = auth_headers(email="f1@example.com", name="F1")
    stranger = auth_headers(email="f2@example.com", name="F2")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    register_team(client, stranger, name="Bears")

    refused = console_put_roster(client, team_id, [{"name": "Theirs"}], stranger)
    assert refused.status_code == 403
    # and the entrant's own route still refuses a team that is not theirs
    not_mine = put_roster(client, team_id, [{"name": "Theirs"}], stranger)
    assert not_mine.status_code == 404
    assert (
        client.get("/api/tournaments/cup/teams", headers=organizer).json()[0]["teams"][0]["members"]
        == []
    )


def test_the_organizers_edit_moves_no_money_and_sends_no_mail(client, auth_headers):
    """A team's fee is per team and never multiplied by its roster, so there
    is no edit to a roster that money could follow — and a letter per
    corrected row would cost more than the error (spec team-disciplines)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    mailer = mailbox_fixture()
    try:
        fencer = auth_headers(email="f1@example.com", name="F1")
        created = register_team(client, fencer, name="Wolves").json()
        team_id = created["teams"][0]["id"]
        three = put_roster(client, team_id, [{"name": n} for n in ("A", "B", "C")], fencer).json()[
            "members"
        ]
        session = db_session()
        registration = session.scalar(
            select(Registration).join(Fencer).where(Fencer.email == "f1@example.com")
        )
        assert registration is not None
        pay_registration(session, registration)
        before = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
        assert before["state"] == "paid"
        mailer.sent.clear()

        swapped = console_put_roster(
            client,
            team_id,
            [*[dict(m) for m in three[:2]], {"name": "Substitute"}],
            organizer,
        )
        assert swapped.status_code == 200, swapped.text

        after = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
        for field in (
            "vs",
            "total_amount",
            "outstanding_amount",
            "outstanding_currency",
            "paid_at",
            "refundable",
            "refund_state",
        ):
            assert after[field] == before[field], field
        assert after["state"] == before["state"]
        assert mailer.sent == []
    finally:
        app.dependency_overrides.pop(get_mailer, None)


def test_the_deadline_constrains_neither_actor(client, auth_headers):
    """Roster editing is gated by neither the amendment window nor the
    composition deadline, for the entering fencer or the organizer. The
    organizer's entry says it was made after the deadline, because a change
    made afterwards is read differently from one made before it."""
    organizer = auth_headers()
    yesterday = (today_local() - timedelta(days=1)).isoformat()
    setup_team_tournament(client, organizer, deadline=yesterday)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]

    by_entrant = put_roster(client, team_id, [{"name": "A"}], fencer)
    assert by_entrant.status_code == 200
    mine = by_entrant.json()["members"]
    by_organizer = console_put_roster(
        client, team_id, [*[dict(m) for m in mine], {"name": "B"}], organizer
    )
    assert by_organizer.status_code == 200, by_organizer.text

    entries = {(e["kind"], e["member_name"]): e for e in by_organizer.json()["log"]}
    assert entries[("added", "A")]["after_deadline"] is True
    assert entries[("added", "A")]["by_organizer"] is False
    assert entries[("added", "B")]["after_deadline"] is True
    assert entries[("added", "B")]["by_organizer"] is True


# ---------------------------------------------------------------------------
# 10.5 Deadline
# ---------------------------------------------------------------------------


def test_below_minimum_flag_only_after_deadline(client, auth_headers):
    organizer = auth_headers()
    # the composition deadline is a date the organizer entered, so it is read
    # where the tournament is held (spec `day-boundaries`)
    yesterday = (today_local() - timedelta(days=1)).isoformat()
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
    tomorrow = (today_local() + timedelta(days=1)).isoformat()
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


@pytest.mark.parametrize("timezone", [FAR_EAST, FAR_WEST])
def test_below_minimum_follows_the_tournaments_own_day(client, auth_headers, timezone):
    """The composition deadline is a whole day where the tournament is held, not
    a UTC day (spec `day-boundaries`). One tournament cannot show which clock
    was used — the two agree most of the day — but this pair of zones disagrees
    with UTC at every hour between them, so a UTC reading fails one of them
    whenever the suite runs.
    """
    organizer = auth_headers()
    local_today = today_in(timezone)
    setup_team_tournament(client, organizer, deadline=(local_today - timedelta(days=1)).isoformat())
    client.patch("/api/tournaments/cup", json={"timezone": timezone}, headers=organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},  # below team_min of 3
        headers=fencer,
    )

    console = client.get("/api/tournaments/cup/teams", headers=organizer).json()
    assert console[0]["teams"][0]["below_minimum"] is True

    # the deadline day itself is not past until it ends, locally
    client.patch(
        "/api/tournaments/cup",
        json={"team_composition_deadline": local_today.isoformat()},
        headers=organizer,
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
    soon = (today_local() + timedelta(days=3)).isoformat()
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
    assert doc["schema_version"] == SCHEMA_VERSION
    assert doc["disciplines"][0]["kind"] == "team"
    assert doc["disciplines"][0]["team_min"] == 3

    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post("/api/tournaments/restore", json=doc, headers=new_organizer)
    assert restore.status_code == 201, restore.text

    # the document carries no publication record: what restore lands is a draft
    # holding registrations, and it must be published before it exports again
    # (spec data-export, Exporting waits for publication)
    publish(restore_client, new_organizer, "cup")
    export2 = restore_client.get("/api/tournaments/cup/export/json", headers=new_organizer).json()
    reg_teams = {r["fencer_email"]: r["teams"] for r in export2["registrations"]}
    wolves = reg_teams["f1@example.com"][0]
    assert wolves["name"] == "Wolves"
    assert wolves["waitlisted"] is False
    assert [m["name"] for m in wolves["members"]] == ["A", "B"]
    assert wolves["members"][0]["hr_id"] == 111
    # the document states what the row holds, and the row holds the code the
    # save read out of "CZE" (spec team-disciplines)
    assert wolves["members"][0]["nationality"] == "CZ"
    assert wolves["members"][1]["nationality"] is None
    bears = reg_teams["f2@example.com"][0]
    assert bears["waitlisted"] is True

    # no account was created for a roster member (design D4)
    session = db_session()
    assert session.scalar(select(Fencer).where(Fencer.email == "f1@example.com")) is not None
    member_as_account = session.scalar(select(Fencer).where(Fencer.display_name == "A"))
    assert member_as_account is None


def test_v22_roundtrip_carries_removed_members_and_the_roster_log(client, auth_headers):
    """A restore that dropped the history would make the history worth less
    than the paper it is not printed on (design D5). The document carries the
    members off the roster and every entry of its log, the organizer's acts
    among them, with the actor still named afterwards."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, team_max=4)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    three = put_roster(
        client, team_id, [{"name": "A", "hr_id": 111}, {"name": "B"}, {"name": "C"}], fencer
    ).json()["members"]
    # the organizer swaps one at the venue, which is the history worth keeping
    console_put_roster(
        client, team_id, [*[dict(m) for m in three[:2]], {"name": "Substitute"}], organizer
    )

    doc = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    assert doc["schema_version"] >= 22
    exported = doc["registrations"][0]["teams"][0]
    assert [m["name"] for m in exported["removed_members"]] == ["C"]
    assert len(exported["roster_log"]) == 5

    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post("/api/tournaments/restore", json=doc, headers=new_organizer)
    assert restore.status_code == 201, restore.text
    publish(restore_client, new_organizer, "cup")

    restored = restore_client.get("/api/tournaments/cup/teams", headers=new_organizer).json()
    team = restored[0]["teams"][0]
    assert [m["name"] for m in team["members"]] == ["A", "B", "Substitute"]
    assert [m["name"] for m in team["removed_members"]] == ["C"]
    assert sorted((e["kind"], e["member_name"], e["by_organizer"]) for e in team["log"]) == [
        ("added", "A", False),
        ("added", "B", False),
        ("added", "C", False),
        ("added", "Substitute", True),
        ("removed", "C", True),
    ]
    # the log still points at members of this restored roster, not at the ids
    # the old deployment issued
    live_and_gone = {m["id"] for m in team["members"] + team["removed_members"]}
    assert {e["member_id"] for e in team["log"]} <= live_and_gone
    # and the organizer who swapped is named, though they entered nothing
    assert {e["actor"] for e in team["log"] if e["by_organizer"]} == {"Organizer"}


def test_restore_of_a_v21_document_has_live_members_and_no_history(client, auth_headers):
    """An empty log on an old document is honest: it says nothing rather than
    something false. Its members arrive live, as the document meant them
    (design D5)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    put_roster(client, team_id, [{"name": "A"}, {"name": "B"}], fencer)

    doc = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    # as a v21 export was written: no member identity, no removals, no log
    doc["schema_version"] = 21
    team_entry = doc["registrations"][0]["teams"][0]
    team_entry.pop("removed_members")
    team_entry.pop("roster_log")
    team_entry["members"] = [
        {k: v for k, v in m.items() if k != "ref"} for m in team_entry["members"]
    ]

    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post("/api/tournaments/restore", json=doc, headers=new_organizer)
    assert restore.status_code == 201, restore.text
    publish(restore_client, new_organizer, "cup")

    team = restore_client.get("/api/tournaments/cup/teams", headers=new_organizer).json()[0][
        "teams"
    ][0]
    assert [m["name"] for m in team["members"]] == ["A", "B"]
    assert team["removed_members"] == []
    assert team["log"] == []


def test_restore_reads_an_older_documents_country_name(client, auth_headers):
    """A document written before the column spoke one vocabulary restores into
    rows that do (spec team-disciplines): the restore is a writer of rows, and
    the migration that converted the stored ones cannot reach a row arriving
    after it ran."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A", "hr_id": 111, "nationality": "CZ"}]},
        headers=fencer,
    )
    doc = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    # as an export taken before this reading spelled it
    doc["registrations"][0]["teams"][0]["members"][0]["nationality"] = "Czech Republic"

    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restore = restore_client.post("/api/tournaments/restore", json=doc, headers=new_organizer)
    assert restore.status_code == 201, restore.text
    publish(restore_client, new_organizer, "cup")

    exported = restore_client.get("/api/tournaments/cup/export/json", headers=new_organizer).json()
    member = exported["registrations"][0]["teams"][0]["members"][0]
    assert member["nationality"] == "CZ"


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
            "city": "Prague",
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
            {
                "code": "LS",
                "name": "Longsword",
                "capacity": 10,
                "fee": 500,
                "fee_early": None,
                "fee_eur": None,
                "fee_early_eur": None,
            },
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


def test_a_team_discipline_reaches_the_sheets_export(client, auth_headers):
    from app.sheets_export import get_sheets_client_factory
    from tests.test_sheets_export import InMemorySheets

    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
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
            "slug": "SA",
            "weapon": "SA",
            "capacity": 5,
            "fee": 3000,
            "kind": "team",
            "team_min": 3,
            "team_max": 4,
        },
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "output_sheet_url": "https://sheets.example/cup",
            "city": "Brno",
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
    team_id = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["teams"][0][
        "id"
    ]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "Roster Member Not A Fencer"}]},
        headers=fencer,
    )

    sheets = InMemorySheets()
    app.dependency_overrides[get_sheets_client_factory] = lambda: lambda tournament: sheets
    try:
        response = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
        assert response.status_code == 200, response.text
        # the spreadsheet mirrors the export tables, and the band carries a tab
        # per discipline — individual and team alike (spec export-tables)
        assert response.json()["worksheets"] == ["Fencers", "LS", "SA", "Summary"]
        # the team's worksheet is the team with its fighters beneath it
        team_rows = [row[1] for row in sheets.worksheets["SA"][1:]]
        assert team_rows == [
            "Wolves · přihlásil Jan Novák · 1/3–4 na soupisce",
            "Roster Member Not A Fencer",
        ]
        # and the Fencers worksheet is the fencer list, which the roster member
        # is on: it is a start list, which is what a tournament needs (design D8)
        fencers_rows = [row[1] for row in sheets.worksheets["Fencers"][1:]]
        assert fencers_rows == ["Jan Novák", "Roster Member Not A Fencer"]
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
            "weapon": "LS",
            "kind": "team",
            "team_min": 3,
            "team_max": 4,
            "capacity": 5,
            "fee": 3500,
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


def test_hr_category_map_accepts_a_team_discipline(client, auth_headers):
    """A team discipline derives a taxonomy code like any other, and the map is
    keyed by code: the one it refused is the one a team-only tournament needs
    (spec team-disciplines, A team discipline carries a rating category for its
    fighters)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    response = client.patch(
        "/api/tournaments/cup",
        json={"hr_category_map": {"LS": "Longsword"}},
        headers=organizer,
    )
    assert response.status_code == 200, response.text

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    assert tournament.hr_category_map == {"LS": "Longsword"}


def test_alike_disciplines_share_one_category_entry(client, auth_headers):
    """An individual and a team discipline classified alike share one entry,
    because the map is keyed by taxonomy code and not by a discipline's
    identity (spec hr-integration, Ratings snapshots)."""
    from app import hr_sync

    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    # the same weapon individually: one taxonomy code, two disciplines
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS-open", "weapon": "LS", "capacity": 5, "fee": 500},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    client.patch(
        "/api/tournaments/cup",
        json={"hr_category_map": {"LS": "Longsword"}},
        headers=organizer,
    )

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    codes = {d.taxonomy_code for d in tournament.disciplines}
    assert codes == {"LS"}
    assert hr_sync.category_keyword(tournament, "LS") == "Longsword"


# ---------------------------------------------------------------------------
# 10.7 Regression: no team discipline -> unchanged behavior
# ---------------------------------------------------------------------------


def test_no_team_discipline_regression(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}]},
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


def test_own_state_judges_a_team_only_registration_by_its_team(client, auth_headers):
    """A seated team is a place held: its registration reads reserved, not
    substitute, in the fencer's list — and a waitlisted one reads substitute."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=1)
    first = auth_headers(email="f1@example.com", name="F1")
    second = auth_headers(email="f2@example.com", name="F2")
    register_team(client, first, name="Wolves")
    register_team(client, second, name="Bears")

    def own_state(headers):
        listed = client.get("/api/tournaments/open", headers=headers).json()
        return next(t for t in listed if t["slug"] == "cup")["my_registration_state"]

    assert own_state(first) == "reserved"
    assert own_state(second) == "substitute"


@pytest.mark.parametrize("source_row_id", [None, "import-row-7"], ids=["hand_entry", "imported"])
def test_composition_reminder_skips_a_registration_squire_does_not_write_to(
    client, auth_headers, source_row_id
):
    """A hand entry and an imported registration are sent nothing, and the team
    is not stamped as reminded (spec team-disciplines)."""
    organizer = auth_headers()
    soon = (today_local() + timedelta(days=3)).isoformat()
    setup_team_tournament(client, organizer, capacity=5, deadline=soon)
    fencer = auth_headers(email="short@example.com", name="Short")
    team_id = register_team(client, fencer, name="Short Team").json()["teams"][0]["id"]
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A"}]},
        headers=fencer,
    )
    session = db_session()
    team = session.get(Team, team_id)
    assert team is not None
    team.registration.clocks_dormant = True
    team.registration.source_row_id = source_row_id
    session.commit()

    mailer = mailbox_fixture()
    try:
        from app import scheduler

        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        assert scheduler.process_composition_reminders(session, tournament, mailer) == 0
        assert mailer.sent == []
        session.refresh(team)
        assert team.composition_reminded_at is None
    finally:
        app.dependency_overrides.pop(get_mailer, None)


def test_composition_reminder_links_the_tournament_page(client, auth_headers):
    organizer = auth_headers()
    soon = (today_local() + timedelta(days=3)).isoformat()
    setup_team_tournament(client, organizer, capacity=5, deadline=soon)
    fencer = auth_headers(email="short@example.com", name="Short")
    team_id = register_team(client, fencer, name="Short Team").json()["teams"][0]["id"]
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
        scheduler.process_composition_reminders(session, tournament, mailer)
        (message,) = mailer.sent
        assert "/t/cup" in message.get_body(("plain",)).get_content()
    finally:
        app.dependency_overrides.pop(get_mailer, None)


# ---------------------------------------------------------------------------
# The teams a console row entered (spec etl-console, The teams a row entered)
# ---------------------------------------------------------------------------


def setup_two_team_disciplines(client, organizer):
    """A tournament with two team disciplines and one individual one, so a row
    can enter a team in each and a row can enter no team at all."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    for slug, kind in (("LS", "team"), ("SA", "team"), ("RD", "individual")):
        payload = {"slug": slug, "weapon": slug, "capacity": 10, "fee": 1000, "kind": kind}
        if kind == "team":
            payload |= {"team_min": 3, "team_max": 4}
        response = client.post("/api/tournaments/cup/disciplines", json=payload, headers=organizer)
        assert response.status_code == 201, response.text
    publish(client, organizer, "cup")


def sheet_rows(client, organizer) -> dict[str, dict]:
    response = client.get("/api/tournaments/cup/sheet", headers=organizer)
    assert response.status_code == 200, response.text
    return {row["name"]: row for row in response.json()["rows"]}


def test_console_row_states_each_team_with_its_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_two_team_disciplines(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="Two Teams")
    response = client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": [],
            "teams": [{"slug": "LS", "name": "Red Rose"}, {"slug": "SA", "name": "Street 2"}],
        },
        headers=fencer,
    )
    assert response.status_code == 201, response.text

    row = sheet_rows(client, organizer)["Two Teams"]

    # the discipline is what separates two teams that would otherwise read as
    # two bare names, and the order is the order they were entered
    assert row["teams"] == [
        {"name": "Red Rose", "discipline": "LS"},
        {"name": "Street 2", "discipline": "SA"},
    ]


def test_two_teams_in_one_discipline_both_named(client, auth_headers):
    organizer = auth_headers()
    setup_two_team_disciplines(client, organizer)
    fencer = auth_headers(email="f2@example.com", name="Same Twice")
    client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": [],
            "teams": [{"slug": "LS", "name": "Red Rose"}, {"slug": "LS", "name": "Red Rose B"}],
        },
        headers=fencer,
    )

    row = sheet_rows(client, organizer)["Same Twice"]

    assert row["teams"] == [
        {"name": "Red Rose", "discipline": "LS"},
        {"name": "Red Rose B", "discipline": "LS"},
    ]


def test_individual_only_row_entered_no_team(client, auth_headers):
    organizer = auth_headers()
    setup_two_team_disciplines(client, organizer)
    fencer = auth_headers(email="f3@example.com", name="Solo Only")
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["RD"], "teams": []},
        headers=fencer,
    )
    assert response.status_code == 201, response.text

    assert sheet_rows(client, organizer)["Solo Only"]["teams"] == []


def test_a_rosters_member_is_not_a_team_entry(client, auth_headers):
    """A member is a name local to someone else's roster, not an identity
    (design team-disciplines D4): the team stands on the entering row alone."""
    organizer = auth_headers()
    setup_two_team_disciplines(client, organizer)
    captain = auth_headers(email="cap@example.com", name="Captain")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": [], "teams": [{"slug": "LS", "name": "Red Rose"}]},
        headers=captain,
    )
    member = auth_headers(email="member@example.com", name="Member")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["RD"], "teams": []},
        headers=member,
    )
    session = db_session()
    team = session.scalars(select(Team)).one()
    team.members.append(TeamMember(name="Member", ordinal=1))
    session.commit()

    rows = sheet_rows(client, organizer)

    assert rows["Captain"]["teams"] == [{"name": "Red Rose", "discipline": "LS"}]
    assert rows["Member"]["teams"] == []


def test_a_hand_entered_source_row_entered_no_team(client, auth_headers):
    """A team is entered through a registration, so no source row carries one."""
    from app.models import RegistrationsKeptBy

    organizer = auth_headers()
    setup_two_team_disciplines(client, organizer)
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    session.commit()
    response = client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Door Fencer", "nationality": "CZ", "disciplines": ["RD"]},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    assert response.json()["registration_id"] is None

    assert sheet_rows(client, organizer)["Door Fencer"]["teams"] == []


# ---------------------------------------------------------------------------
# The fencer list is the tournament's start field (spec etl-console)
# ---------------------------------------------------------------------------


def set_roster(client, headers, team_id, names):
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": name} for name in names]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["members"]


def test_the_start_field_is_everyone_who_fights(client, auth_headers):
    """Three team registrations holding seven fighters between them produce
    seven fighter rows, not three contracts — and no fighter row states money
    (spec etl-console, The start field is everyone who fights)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    rosters = {
        "f1@example.com": ["A1", "A2", "A3"],
        "f2@example.com": ["B1", "B2"],
        "f3@example.com": ["C1", "C2"],
    }
    for index, (email, names) in enumerate(rosters.items()):
        fencer = auth_headers(email=email, name=f"Entrant {index}")
        team_id = register_team(client, fencer, name=f"Team {index}").json()["teams"][0]["id"]
        set_roster(client, fencer, team_id, names)

    rows = sheet_rows(client, organizer)
    fighters = [row for row in rows.values() if row["fights"]]
    assert sorted(row["name"] for row in fighters) == ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]
    # a fighter, not a contract: no variable symbol, total, balance, payment
    # state, expiry or seat (spec etl-console, A member row states no money)
    for row in fighters:
        assert row["id"].startswith("mem:")
        assert row["vs"] is None
        assert row["total_amount"] is None
        assert row["paid"] is False
        assert row["expires_at"] is None
        assert row["paid_at"] is None
        assert row["registration_id"] is None
        assert "outstanding_amount" not in row
        assert row["state"] == "member"


def test_a_team_only_registration_is_not_a_fencer(client, auth_headers):
    """Entering a team is not fighting. The registration stays fully present
    where its agenda is — Teams, Payments and the Queue — and is not listed as a
    fencer (spec etl-console, A fencer who entered a team but fights nothing)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant Only")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    set_roster(client, fencer, team_id, ["Fighter One", "Fighter Two"])

    rows = sheet_rows(client, organizer)
    entrant = rows["Entrant Only"]
    assert entrant["fights"] is False
    # and everything the payment phases read is on it, unchanged
    assert entrant["vs"] is not None
    assert entrant["total_amount"] == 3000
    assert entrant["registration_id"] is not None
    assert rows["Fighter One"]["fights"] is True


def test_an_entrant_who_also_fights_is_listed(client, auth_headers):
    """A registration holding an individual entry is a fighter whatever teams
    it also entered, and a registration that entered no team at all is one
    whatever it bought."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 5, "fee": 500},
        headers=organizer,
    )
    both = auth_headers(email="f1@example.com", name="Fights And Enters")
    register_team(client, both, name="Wolves", disciplines=["SB"])
    alone = auth_headers(email="f2@example.com", name="Fights Alone")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["SB"]}, headers=alone)

    rows = sheet_rows(client, organizer)
    assert rows["Fights And Enters"]["fights"] is True
    assert rows["Fights Alone"]["fights"] is True


def test_a_member_is_numbered_when_it_is_added(client, auth_headers):
    """The number is allocated where the row is born, survives a removal and a
    restore, and is never reissued (spec etl-console, Fixed fencer number)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    members = set_roster(client, fencer, team_id, ["A", "B"])

    numbers = {row["name"]: row["number"] for row in sheet_rows(client, organizer).values()}
    assert numbers["A"] is not None and numbers["B"] is not None
    assert numbers["A"] != numbers["B"]

    # B removed: its number is retired, not released
    set_roster(client, fencer, team_id, ["A"])
    after_removal = sheet_rows(client, organizer)
    assert "B" not in after_removal
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "A", "id": members[0]["id"]}, {"name": "C"}]},
        headers=fencer,
    )
    with_c = {row["name"]: row["number"] for row in sheet_rows(client, organizer).values()}
    assert with_c["C"] != numbers["B"]

    # and B restored by its own id comes back with the number it had
    restored = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={
            "members": [
                {"name": "A", "id": members[0]["id"]},
                {"name": "B", "id": members[1]["id"]},
            ]
        },
        headers=fencer,
    )
    assert restored.status_code == 200, restored.text
    back = {row["name"]: row["number"] for row in sheet_rows(client, organizer).values()}
    assert back["B"] == numbers["B"]


def test_a_team_stands_together_between_two_registrations(client, auth_headers):
    """A team's members take the team's own moment and stand among themselves in
    roster order (spec etl-console, Order of the fencer list)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 10, "fee": 500},
        headers=organizer,
    )
    first = auth_headers(email="first@example.com", name="First Individual")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["SB"]}, headers=first)
    entrant = auth_headers(email="team@example.com", name="Team Entrant")
    team_id = register_team(client, entrant, name="Wolves").json()["teams"][0]["id"]
    last = auth_headers(email="last@example.com", name="Last Individual")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["SB"]}, headers=last)
    # the roster is typed in after both individual registrations and still
    # stands where the team entered
    set_roster(client, entrant, team_id, ["Charlie", "Alice", "Bob"])

    response = client.get("/api/tournaments/cup/sheet", headers=organizer)
    listed = [row["name"] for row in response.json()["rows"] if row["fights"]]
    assert listed == ["First Individual", "Charlie", "Alice", "Bob", "Last Individual"]


class MemberMatcher:
    """Finds the stub index's Jan Novák for a fighter of that name, nobody for
    anyone else."""

    def __init__(self):
        self.asked: list[str] = []

    def match(self, fencers, candidates):
        from app.hr_match import HRMatchResult

        results = []
        for fencer in fencers:
            self.asked.append(fencer["name"])
            found = fencer["name"] == "Jan Novak"
            results.append(
                HRMatchResult(
                    name=fencer["name"],
                    club=fencer["club"],
                    hr_id=10234 if found else None,
                    matched_name="Jan Novák" if found else None,
                    matched_club="Prague HEMA" if found else None,
                    nationality=fencer.get("nationality"),
                )
            )
        return results


def test_a_member_is_matched_like_anybody_else(client, auth_headers):
    """The identifier a roster claims is answered the way every other row's is,
    and the organizer's verdict is a rule on the member's own row id which the
    next roster save does not disturb (spec etl-console, A member is matched
    like anybody else)."""
    from app.hr_match import get_hr_matcher
    from tests.conftest import outcome

    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    members = set_roster(client, fencer, team_id, ["Jan Novak", "Nobody At All"])

    matcher = MemberMatcher()
    app.dependency_overrides[get_hr_matcher] = lambda: matcher
    try:
        response = client.post("/api/tournaments/cup/import/match", headers=organizer)
        assert response.status_code == 202, response.text
        body = outcome(client, organizer, kind="match")
    finally:
        app.dependency_overrides.pop(get_hr_matcher, None)

    # the fighters were the population, not the one registration behind them
    assert sorted(matcher.asked) == ["Jan Novak", "Nobody At All"]
    assert body["matched"] == 1

    rows = sheet_rows(client, organizer)
    jan = rows["Jan Novak"]
    assert jan["id"] == f"mem:{members[0]['id']}"
    assert jan["hr_id"] == 10234
    assert jan["hr_name"] == "Jan Novák"
    assert jan["match_verdict"] in ("found", "proposed")

    # the organizer's verdict is a rule on the member's row id
    verdict = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "matching",
            "kind": "match_resolution",
            "target": jan["id"],
            "payload": {"field": "hr_id", "value": 3340},
        },
        headers=organizer,
    )
    assert verdict.status_code in (200, 201), verdict.text

    def member_row() -> dict:
        response = client.get("/api/tournaments/cup/sheet", headers=organizer)
        return next(row for row in response.json()["rows"] if row["id"] == jan["id"])

    assert member_row()["hr_id"] == 3340

    # and a later save of the same roster that leaves this member alone keeps it
    client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={
            "members": [
                {"name": "Jan Novak", "id": members[0]["id"]},
                {"name": "Somebody Else", "id": members[1]["id"]},
            ]
        },
        headers=fencer,
    )
    after = member_row()
    assert after["hr_id"] == 3340
    assert after["match_verdict"] == "confirmed"


def test_two_rosters_naming_one_person_are_not_duplicates(client, auth_headers):
    """Two rosters naming one fighter are two fighting places, and a member row
    beside its own entrant's registration row is one person in two roles.
    Neither is a duplicate (spec etl-console, Two rosters naming one person are
    not duplicates). That two imported rows of one person still are is
    `tests/test_dedup.py`'s `test_same_hr_id_queues_and_merges_on_confirm`."""
    from app.dedup import MergeProposal, ThreeBands, default_merge, get_dedup_llm
    from tests.conftest import outcome

    class RecordingLLM:
        def __init__(self):
            self.seen: list[list[str]] = []

        def propose_merge(self, records, language):
            self.seen.append([r["name"] for r in records])
            return MergeProposal(fields=default_merge(records), note="")

        def classify(self, records):
            self.seen.append([r["name"] for r in records])
            return ThreeBands(surely=[], likely=[], possible=[])

    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    first = auth_headers(email="f1@example.com", name="Jan Novák")
    second = auth_headers(email="f2@example.com", name="Other Entrant")
    for headers, team in ((first, "Wolves"), (second, "Bears")):
        team_id = register_team(client, headers, name=team).json()["teams"][0]["id"]
        response = client.put(
            f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
            json={"members": [{"name": "Jan Novák", "hr_id": 10234}]},
            headers=headers,
        )
        assert response.status_code == 200, response.text

    llm = RecordingLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm
    try:
        response = client.post("/api/tournaments/cup/import/dedup", headers=organizer)
        assert response.status_code == 202, response.text
        outcome(client, organizer, kind="dedup")
    finally:
        app.dependency_overrides.pop(get_dedup_llm, None)

    assert llm.seen == []
    groups = client.get("/api/tournaments/cup/import/dedup/groups", headers=organizer).json()
    assert groups == []


# ---------------------------------------------------------------------------
# Cancelling one team (spec team-disciplines, Cancelling one team)
# ---------------------------------------------------------------------------


def cancel_team(client, organizer, team_id):
    return client.post(f"/api/tournaments/cup/teams/{team_id}/cancel", headers=organizer)


def with_teams_phase(client, organizer):
    """The team disciplines feature on, which is what offers the Teams phase at
    all — and what cancelling one team is refused without."""
    set_features(client, organizer, "cup", feature_teams=True)


def test_one_team_of_two_cancelled_leaves_the_other_standing(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    with_teams_phase(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="Two Teams")
    created = client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": [],
            "teams": [{"slug": "LS", "name": "Wolves"}, {"slug": "LS", "name": "Bears"}],
        },
        headers=fencer,
    ).json()
    assert created["total_amount"] == 6000
    wolves, bears = (team["id"] for team in created["teams"])
    set_roster(client, fencer, wolves, ["A", "B", "C", "D"])
    set_roster(client, fencer, bears, ["E", "F"])

    response = cancel_team(client, organizer, wolves)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["previous_total"] == "6000"
    # repriced on its own frozen prices, less the cancelled team's fee alone
    assert body["total"] == "3000"

    # the other team and the registration stand
    mine = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert [team["name"] for team in mine["teams"]] == ["Bears"]
    assert mine["total_amount"] == 3000

    # and the cancelled team's fighters have left the fencer list
    rows = sheet_rows(client, organizer)
    assert sorted(name for name, row in rows.items() if row["fights"]) == ["E", "F"]
    for gone in ("A", "B", "C", "D"):
        assert gone not in rows


def test_a_seated_teams_cancellation_frees_a_place_and_promotes_nobody(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=1)
    with_teams_phase(client, organizer)
    seated = auth_headers(email="f1@example.com", name="Seated")
    waiting = auth_headers(email="f2@example.com", name="Waiting")
    team_id = register_team(client, seated, name="Wolves").json()["teams"][0]["id"]
    register_team(client, waiting, name="Bears")

    availability = client.get("/api/tournaments/cup/availability").json()[0]
    assert availability["free"] == 0

    assert cancel_team(client, organizer, team_id).status_code == 200

    # the place is freed and nobody is admitted into it: a freed place waits
    # for the organizer, as a freed individual seat does
    availability = client.get("/api/tournaments/cup/availability").json()[0]
    assert availability["free"] == 1
    teams = client.get("/api/tournaments/cup/teams", headers=organizer).json()[0]["teams"]
    assert [(team["name"], team["waitlisted"]) for team in teams] == [("Bears", True)]


def test_cancelling_a_team_is_refused_on_a_dead_registration(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    with_teams_phase(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="Gone")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    response = cancel_team(client, organizer, team_id)
    assert response.status_code == 409
    assert response.json()["detail"] == "registration_not_live"


def test_cancelling_a_team_is_refused_while_the_feature_is_off(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    client.patch("/api/tournaments/cup", json={"feature_teams": False}, headers=organizer)

    response = cancel_team(client, organizer, team_id)
    assert response.status_code == 409
    assert response.json()["detail"] == "team_disciplines_off"
    # the teams a hidden feature holds are retained untouched
    client.patch("/api/tournaments/cup", json={"feature_teams": True}, headers=organizer)
    teams = client.get("/api/tournaments/cup/teams", headers=organizer).json()[0]["teams"]
    assert [team["name"] for team in teams] == ["Wolves"]


@pytest.mark.parametrize(
    ("language", "needle"),
    [("cs", "zrušil tvůj tým"), ("en", "has cancelled your team")],
)
def test_the_entering_fencer_is_told_in_their_own_language(client, auth_headers, language, needle):
    """Money changes hands, so this is not the silent correction a roster edit
    is: the letter names the team and the discipline and states the balance
    (spec team-disciplines, Cancelling one team)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    # the balance is stated where Squire collects the money; on a tournament it
    # does not, there is no figure of Squire's to state
    set_features(client, organizer, "cup", feature_teams=True, feature_payments=True)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    client.patch("/api/account", json={"language": language}, headers=fencer)
    created = client.post(
        "/api/tournaments/cup/register",
        json={
            "disciplines": [],
            "teams": [{"slug": "LS", "name": "Wolves"}, {"slug": "LS", "name": "Bears"}],
        },
        headers=fencer,
    ).json()
    team_id = created["teams"][0]["id"]

    mailer = mailbox_fixture()
    try:
        response = cancel_team(client, organizer, team_id)
        assert response.status_code == 200, response.text
        assert response.json()["notified"] is True
    finally:
        app.dependency_overrides.pop(get_mailer, None)

    letters = [m for m in mailer.sent if needle in m.get_content()]
    assert len(letters) == 1
    body = letters[0].get_content()
    assert "Wolves" in body
    # the discipline, and what the registration now owes
    assert "LS" in body or "Longsword" in body
    assert "3000" in body or "3 000" in body


def test_a_registration_squire_sends_nothing_to_is_not_written_to(client, auth_headers):
    """A seat the organizer entered by hand is sent nothing, the organizer
    being the one in contact (`emails.send_team_cancelled`)."""
    from app.models import Registration

    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    with_teams_phase(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    session = db_session()
    registration = session.scalar(
        select(Registration).where(Registration.tournament_id.is_not(None))
    )
    assert registration is not None
    registration.clocks_dormant = True
    registration.source_row_id = None
    session.commit()

    mailer = mailbox_fixture()
    try:
        response = cancel_team(client, organizer, team_id)
        assert response.status_code == 200, response.text
        assert response.json()["notified"] is False
    finally:
        app.dependency_overrides.pop(get_mailer, None)
    assert mailer.sent == []


# ---------------------------------------------------------------------------
# The public roster states the identifier the console settled
# (spec public-entrants, A team roster names the team and its members)
# ---------------------------------------------------------------------------


def test_the_public_roster_states_the_settled_identifier(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={
            "members": [
                {"name": "Claimed Wrong", "hr_id": 10234},
                {"name": "Nobody Knows Me"},
            ]
        },
        headers=fencer,
    )
    assert response.status_code == 200, response.text
    members = response.json()["members"]

    # the organizer rules the first member onto another profile
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "matching",
            "kind": "match_resolution",
            "target": f"mem:{members[0]['id']}",
            "payload": {"field": "hr_id", "value": 3340},
        },
        headers=organizer,
    )

    roster = client.get("/api/tournaments/cup/entrants").json()["rosters"]
    listed = next(entry for entry in roster if entry["slug"] == "LS")
    published = {m["name"]: m["hr_id"] for team in listed["seated"] for m in team["members"]}
    # the organizer's verdict is the tournament's answer, and it is what the
    # public sees — not the identifier typed into the roster
    assert published["Anna Kowalska"] == 3340
    assert "Claimed Wrong" not in published
    # and a member nobody ruled on is published as claimed
    assert published["Nobody Knows Me"] is None


# ---------------------------------------------------------------------------
# A team discipline's export tab (spec export-tables)
# ---------------------------------------------------------------------------


def test_the_band_carries_a_tab_per_team_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=2)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 5, "fee": 500},
        headers=organizer,
    )
    tabs = client.get("/api/tournaments/cup/export/tables", headers=organizer).json()
    assert [(tab["kind"], tab["key"], tab["teams"]) for tab in tabs] == [
        ("fencers", "", False),
        ("discipline", "LS", True),
        ("discipline", "SB", False),
        ("summary", "", False),
        ("revenue", "", False),
    ]


def test_a_team_tab_reads_as_teams_with_their_fighters(client, auth_headers):
    """Teams ordered by paid then the moment the team entered, each numbered as
    a team with its fighters beneath it in roster order; a fighter carries no
    paid cell of its own (spec export-tables, A team tab reads as teams with
    their fighters)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=1)
    first = auth_headers(email="f1@example.com", name="First")
    second = auth_headers(email="f2@example.com", name="Second")
    wolves = register_team(client, first, name="Wolves").json()["teams"][0]["id"]
    bears = register_team(client, second, name="Bears").json()["teams"][0]["id"]
    set_roster(client, first, wolves, ["A One", "A Two"])
    set_roster(client, second, bears, ["B One"])

    table = client.get(
        "/api/tournaments/cup/export/table?kind=discipline&key=LS", headers=organizer
    ).json()
    assert table["teams"] is True
    listed = [(row["name"], row.get("_team") is not None) for row in table["rows"]]
    assert listed == [
        ("Wolves", True),
        ("A One", False),
        ("A Two", False),
        # the second team is over capacity and waits, so it stands below where
        # the tab draws its line
        ("Bears", True),
        ("B One", False),
    ]
    wolves_row = table["rows"][0]
    assert wolves_row["_team"] == {
        "entering_fencer": "First",
        "members": 2,
        "team_min": 3,
        "team_max": 4,
        "waitlist_position": None,
    }
    assert table["rows"][3]["_team"]["waitlist_position"] == 1
    # a team carries no identity or rating of its own, and a fighter no paid
    assert wolves_row["hr_id"] is None and wolves_row["ratings"] == {}
    assert "paid" not in table["rows"][1] or table["rows"][1]["paid"] is False

    # the band counts the tab in teams, seated against waitlisted
    tabs = client.get("/api/tournaments/cup/export/tables", headers=organizer).json()
    team_tab = next(tab for tab in tabs if tab["key"] == "LS")
    assert (team_tab["count"], team_tab["queued"]) == (1, 1)


def test_the_fencers_tab_follows_the_fencer_list(client, auth_headers):
    """It is the fencer list and follows it: member rows are on it, and a
    registration that bought nothing but team entries is not (design D8)."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant Only")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    set_roster(client, fencer, team_id, ["Fighter One", "Fighter Two"])

    table = client.get(
        "/api/tournaments/cup/export/table?kind=fencers&key=", headers=organizer
    ).json()
    assert sorted(row["name"] for row in table["rows"]) == ["Fighter One", "Fighter Two"]


def test_roster_print_typesets_a_team_tab(client, auth_headers):
    """Roster print needs no change: it typesets the rows the tab sends, and a
    team discipline is one of the tournament's disciplines like any other."""
    organizer = auth_headers()
    setup_team_tournament(client, organizer, capacity=5)
    fencer = auth_headers(email="f1@example.com", name="Entrant")
    team_id = register_team(client, fencer, name="Wolves").json()["teams"][0]["id"]
    set_roster(client, fencer, team_id, ["A One"])

    response = client.post(
        "/api/tournaments/cup/export/roster.pdf",
        json={
            "discipline": "LS",
            "rows": [
                ["1", "Wolves · entered by Entrant · 1/3–4", "", "", "", "", "No"],
                ["", "A One", "CZ", "", "", "", ""],
            ],
            "line_after": 2,
            "english": True,
        },
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    assert response.content[:4] == b"%PDF"
