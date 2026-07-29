"""Task 1.2 — the fencer-facing past-tournaments list (design D1): personal
history via non-cancelled registration or organizer link, disjoint from the
draft/cancelled/unrelated tournaments the tab must never show."""

from datetime import date, timedelta

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
        json={"code": "LS", "capacity": 2, "fee": 800},
        headers=organizer,
    )


def move_to_past(client, organizer, slug, past_date):
    client.patch(f"/api/tournaments/{slug}", json={"date": str(past_date)}, headers=organizer)


def publish_past(client, organizer, slug, **overrides):
    """Create a tournament directly in the past — for organizer-only cases
    that never need an open registration window."""
    overrides.setdefault("date", str(TODAY - timedelta(days=30)))
    publish_future(client, organizer, slug, **overrides)


def test_past_lists_participated_and_organized_only(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "attended")
    client.post("/api/tournaments/attended/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "attended", TODAY - timedelta(days=5))

    # unrelated past tournament: fencer neither registered nor organized
    publish_past(client, organizer, "unrelated")

    listed = client.get("/api/tournaments/mine/past", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["attended"]

    listed_org = client.get("/api/tournaments/mine/past", headers=organizer).json()
    assert {t["slug"] for t in listed_org} == {"attended", "unrelated"}
    assert all(t["organized"] for t in listed_org)


def test_past_excludes_cancelled_registration(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "left")
    client.post("/api/tournaments/left/register", json={"disciplines": ["LS"]}, headers=fencer)
    client.post("/api/tournaments/left/my-registration/cancel", headers=fencer)
    move_to_past(client, organizer, "left", TODAY - timedelta(days=5))

    listed = client.get("/api/tournaments/mine/past", headers=fencer).json()
    assert listed == []


def test_past_excludes_drafts_and_cancelled_tournaments(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    # draft: missing setup, past-dated, organized by this account
    client.post(
        "/api/tournaments",
        json={"slug": "draft", "display_name": "Draft", "date": str(TODAY - timedelta(days=30))},
        headers=organizer,
    )

    # cancelled: organized and registered, but retired
    publish_future(client, organizer, "gone")
    client.post("/api/tournaments/gone/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "gone", TODAY - timedelta(days=5))
    client.post("/api/tournaments/gone/cancel", headers=organizer)

    listed_organizer = client.get("/api/tournaments/mine/past", headers=organizer).json()
    assert listed_organizer == []

    listed_fencer = client.get("/api/tournaments/mine/past", headers=fencer).json()
    assert listed_fencer == []


def test_past_orders_by_date_descending(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "older")
    client.post("/api/tournaments/older/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "older", TODAY - timedelta(days=60))

    publish_future(client, organizer, "newer")
    client.post("/api/tournaments/newer/register", json={"disciplines": ["LS"]}, headers=fencer)
    move_to_past(client, organizer, "newer", TODAY - timedelta(days=10))

    listed = client.get("/api/tournaments/mine/past", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["newer", "older"]


def test_past_marks_organizer_only_tournament_without_registration_state(client, auth_headers):
    organizer = auth_headers()
    publish_past(client, organizer, "ran-it")

    listed = client.get("/api/tournaments/mine/past", headers=organizer).json()
    ran_it = next(t for t in listed if t["slug"] == "ran-it")
    assert ran_it["organized"] is True
    assert ran_it["my_registration_state"] == "none"
    assert ran_it["registration_status"] == "closed"


def test_past_includes_team_member_organizers(client, auth_headers):
    organizer = auth_headers()
    publish_past(client, organizer, "team-run")

    member = auth_headers(email="member@example.com", name="Member")
    client.post(
        "/api/tournaments/team-run/team", json={"email": "member@example.com"}, headers=organizer
    )

    listed = client.get("/api/tournaments/mine/past", headers=member).json()
    assert [t["slug"] for t in listed] == ["team-run"]
    assert listed[0]["organized"] is True


def test_past_excludes_expired_reservation(client, auth_headers):
    """An expired (never paid) reservation is not "participation" per design
    D1: only paid, reserved, or substitute registrations count."""
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

    listed = client.get("/api/tournaments/mine/past", headers=fencer).json()
    assert listed == []


def test_upcoming_tournament_never_appears_in_past(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    publish_future(client, organizer, "future")
    client.post("/api/tournaments/future/register", json={"disciplines": ["LS"]}, headers=fencer)

    listed = client.get("/api/tournaments/mine/past", headers=fencer).json()
    assert listed == []
