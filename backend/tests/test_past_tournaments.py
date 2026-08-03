"""The held and own scopes of the fencer-facing list: the Past tab is a public
archive of tournaments already run, and Mine is every tournament the caller is
bound to — by a registration in any state, or by organizing it — in either
direction of today."""

from datetime import date, timedelta

from tests.conftest import publish

TODAY = date.today()


def publish_future(client, organizer, slug, **overrides):
    """Create a published tournament with registration open, so a
    registration can be taken before the tournament is moved into the past."""
    payload = {"slug": slug, "display_name": slug.title(), "date": str(TODAY + timedelta(days=30))}
    payload.update({k: v for k, v in overrides.items() if k in ("slug", "display_name", "date")})
    client.post("/api/tournaments", json=payload, headers=organizer)
    patch = {"location": "Brno", "organizers": [{"name": "Org", "link": None}]}
    patch.update({k: v for k, v in overrides.items() if k not in ("slug", "display_name", "date")})
    client.patch(f"/api/tournaments/{slug}", json=patch, headers=organizer)
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 2, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, slug)


def move_to_past(client, organizer, slug, past_date):
    client.patch(f"/api/tournaments/{slug}", json={"date": str(past_date)}, headers=organizer)


def publish_past(client, organizer, slug, **overrides):
    """Create a tournament directly in the past — for organizer-only cases
    that never need an open registration window."""
    overrides.setdefault("date", str(TODAY - timedelta(days=30)))
    publish_future(client, organizer, slug, **overrides)


# ---------------------------------------------------------------------------
# held scope — the public Past tab
# ---------------------------------------------------------------------------


def test_held_lists_every_past_tournament_for_anyone(client, auth_headers):
    organizer = auth_headers()
    stranger = auth_headers(email="f1@example.com", name="F1")

    publish_past(client, organizer, "unrelated")

    listed = client.get("/api/tournaments/held", headers=stranger).json()
    unrelated = next(t for t in listed if t["slug"] == "unrelated")
    assert unrelated["my_registration_state"] == "none"
    assert unrelated["organized"] is False
    assert unrelated["registration_status"] == "closed"


def test_held_carries_own_state_and_organizer_mark(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "attended")
    client.post("/api/tournaments/attended/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "attended", TODAY - timedelta(days=5))

    mine = next(
        t
        for t in client.get("/api/tournaments/held", headers=fencer).json()
        if t["slug"] == "attended"
    )
    assert (mine["my_registration_state"], mine["organized"]) == ("reserved", False)

    theirs = next(
        t
        for t in client.get("/api/tournaments/held", headers=organizer).json()
        if t["slug"] == "attended"
    )
    assert (theirs["my_registration_state"], theirs["organized"]) == ("none", True)


def test_held_excludes_drafts_cancelled_and_upcoming(client, auth_headers):
    organizer = auth_headers()

    client.post(
        "/api/tournaments",
        json={"slug": "draft", "display_name": "Draft", "date": str(TODAY - timedelta(days=30))},
        headers=organizer,
    )
    publish_past(client, organizer, "gone")
    client.post("/api/tournaments/gone/cancel", headers=organizer)
    publish_future(client, organizer, "future")

    listed = client.get("/api/tournaments/held", headers=organizer).json()
    assert [t["slug"] for t in listed] == []


def test_held_orders_by_date_descending(client, auth_headers):
    organizer = auth_headers()
    publish_past(client, organizer, "older", date=str(TODAY - timedelta(days=60)))
    publish_past(client, organizer, "newer", date=str(TODAY - timedelta(days=10)))

    listed = client.get("/api/tournaments/held", headers=organizer).json()
    assert [t["slug"] for t in listed] == ["newer", "older"]


def test_held_counts_team_disciplines_in_teams(client, auth_headers):
    organizer = auth_headers()
    publish_past(client, organizer, "cup")
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "Team-LS", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )

    response = client.get("/api/tournaments/held", headers=organizer)
    assert response.status_code == 200
    cup = next(t for t in response.json() if t["slug"] == "cup")
    team = next(d for d in cup["disciplines"] if d["slug"] == "Team-LS")
    assert (team["taken"], team["capacity"]) == (0, 5)


# ---------------------------------------------------------------------------
# own scope — the Mine tab
# ---------------------------------------------------------------------------


def test_mine_lists_registered_and_organized_only(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "attended")
    client.post("/api/tournaments/attended/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "attended", TODAY - timedelta(days=5))
    publish_past(client, organizer, "unrelated")

    listed = client.get("/api/tournaments/mine", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["attended"]

    listed_org = client.get("/api/tournaments/mine", headers=organizer).json()
    assert {t["slug"] for t in listed_org} == {"attended", "unrelated"}
    assert all(t["organized"] for t in listed_org)


def test_mine_spans_both_directions_of_today(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "upcoming")
    client.post("/api/tournaments/upcoming/register", json={"disciplines": ["LS"]}, headers=fencer)

    publish_future(client, organizer, "held")
    client.post("/api/tournaments/held/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "held", TODAY - timedelta(days=5))

    listed = client.get("/api/tournaments/mine", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["upcoming", "held"]
    assert listed[0]["registration_status"] == "open"


def test_mine_keeps_a_cancelled_registration(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "left")
    client.post("/api/tournaments/left/register", json={"disciplines": ["LS"]}, headers=fencer)
    client.post("/api/tournaments/left/my-registration/cancel", headers=fencer)
    move_to_past(client, organizer, "left", TODAY - timedelta(days=5))

    listed = client.get("/api/tournaments/mine", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["left"]
    assert listed[0]["my_registration_state"] == "cancelled"


def test_mine_keeps_an_expired_reservation(client, auth_headers):
    """An expired reservation is still a tournament the account was in: Mine
    stands on any registration, and reports the lapsed one as cancelled."""
    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Fencer, Registration, RegistrationState

    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "lapsed")
    client.post("/api/tournaments/lapsed/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "lapsed", TODAY - timedelta(days=5))

    session = next(app.dependency_overrides[get_session]())
    fencer_id = session.scalar(select(Fencer.id).where(Fencer.email == "f1@example.com"))
    reg = session.scalar(select(Registration).where(Registration.fencer_id == fencer_id))
    reg.state = RegistrationState.EXPIRED
    session.commit()

    listed = client.get("/api/tournaments/mine", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["lapsed"]
    assert listed[0]["my_registration_state"] == "cancelled"


def test_mine_excludes_drafts_and_cancelled_tournaments(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    client.post(
        "/api/tournaments",
        json={"slug": "draft", "display_name": "Draft", "date": str(TODAY - timedelta(days=30))},
        headers=organizer,
    )

    publish_future(client, organizer, "gone")
    client.post("/api/tournaments/gone/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "gone", TODAY - timedelta(days=5))
    client.post("/api/tournaments/gone/cancel", headers=organizer)

    assert client.get("/api/tournaments/mine", headers=organizer).json() == []
    assert client.get("/api/tournaments/mine", headers=fencer).json() == []


def test_mine_orders_by_date_descending(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "older")
    client.post("/api/tournaments/older/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "older", TODAY - timedelta(days=60))

    publish_future(client, organizer, "newer")
    client.post("/api/tournaments/newer/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "newer", TODAY - timedelta(days=10))

    listed = client.get("/api/tournaments/mine", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["newer", "older"]


def test_mine_marks_organizer_only_tournament_without_registration_state(client, auth_headers):
    organizer = auth_headers()
    publish_past(client, organizer, "ran-it")

    listed = client.get("/api/tournaments/mine", headers=organizer).json()
    ran_it = next(t for t in listed if t["slug"] == "ran-it")
    assert ran_it["organized"] is True
    assert ran_it["my_registration_state"] == "none"
    assert ran_it["registration_status"] == "closed"


def test_mine_includes_team_member_organizers(client, auth_headers):
    organizer = auth_headers()
    publish_past(client, organizer, "team-run")

    member = auth_headers(email="member@example.com", name="Member")
    client.post(
        "/api/tournaments/team-run/team", json={"email": "member@example.com"}, headers=organizer
    )

    listed = client.get("/api/tournaments/mine", headers=member).json()
    assert [t["slug"] for t in listed] == ["team-run"]
    assert listed[0]["organized"] is True


def test_mine_reports_both_bonds_when_organizer_also_registered(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "cup")
    client.post("/api/tournaments/cup/team", json={"email": "f1@example.com"}, headers=organizer)
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer)

    listed = client.get("/api/tournaments/mine", headers=fencer).json()
    cup = next(t for t in listed if t["slug"] == "cup")
    assert (cup["my_registration_state"], cup["organized"]) == ("reserved", True)
