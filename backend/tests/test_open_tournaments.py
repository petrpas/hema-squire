"""Task 1.4/1.5 — the fencer-facing open-tournaments list: publication/date
filtering, per-discipline counts, registration status, and own state."""

from datetime import date, timedelta

from tests.conftest import publish

TODAY = date.today()


def make_open_tournament(client, organizer, slug, **overrides):
    """Builds a setup-complete tournament and publishes it — the two steps
    that together used to be "complete setup" alone (design
    add-explicit-publishing)."""
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


def test_open_hides_drafts_cancelled_and_past(client, auth_headers):
    organizer = auth_headers()
    make_open_tournament(client, organizer, "ready")

    # draft: missing setup (no location/organizers/disciplines)
    client.post(
        "/api/tournaments",
        json={"slug": "draft", "display_name": "Draft", "date": str(TODAY + timedelta(days=30))},
        headers=organizer,
    )

    # cancelled
    make_open_tournament(client, organizer, "gone")
    client.post("/api/tournaments/gone/cancel", headers=organizer)

    # past
    make_open_tournament(client, organizer, "past", date=str(TODAY - timedelta(days=1)))

    fencer = auth_headers(email="f1@example.com", name="F1")
    listed = client.get("/api/tournaments/open", headers=fencer).json()
    assert [t["slug"] for t in listed] == ["ready"]


def test_open_carries_discipline_counts_and_own_state(client, auth_headers):
    organizer = auth_headers()
    make_open_tournament(client, organizer, "cup")
    fencer = auth_headers(email="f1@example.com", name="F1")
    other = auth_headers(email="f2@example.com", name="F2")

    client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )

    listed = client.get("/api/tournaments/open", headers=fencer).json()
    cup = next(t for t in listed if t["slug"] == "cup")
    ls = next(d for d in cup["disciplines"] if d["slug"] == "LS")
    assert (ls["fee"], ls["taken"], ls["capacity"], ls["queue_length"]) == (800, 1, 2, 0)
    assert cup["registration_status"] == "open"
    assert cup["my_registration_state"] == "reserved"
    assert cup["organizers"] == [{"name": "Org", "link": None}]
    assert cup["location"] == "Brno"

    listed_other = client.get("/api/tournaments/open", headers=other).json()
    assert next(t for t in listed_other if t["slug"] == "cup")["my_registration_state"] == "none"


def test_open_reports_substitute_paid_and_cancelled_states(client, auth_headers):
    organizer = auth_headers()
    make_open_tournament(client, organizer, "cup")
    first = auth_headers(email="a@example.com", name="A")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=first)

    third = auth_headers(email="c@example.com", name="C")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=third)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=third)

    # LS (capacity 2) is now full again with A + a decoy, so B queues as a substitute
    decoy = auth_headers(email="z@example.com", name="Z")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=decoy)
    second = auth_headers(email="b@example.com", name="B")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "wait_for_all": True},
        headers=second,
    )

    from sqlalchemy import select

    from app.db import get_session
    from app.main import app
    from app.models import Fencer, Registration, RegistrationState

    session = next(app.dependency_overrides[get_session]())
    a_id = session.scalar(select(Fencer.id).where(Fencer.email == "a@example.com"))
    reg = session.scalar(select(Registration).where(Registration.fencer_id == a_id))
    reg.state = RegistrationState.PAID
    session.commit()

    listed_first = client.get("/api/tournaments/open", headers=first).json()
    assert next(t for t in listed_first if t["slug"] == "cup")["my_registration_state"] == "paid"

    listed_second = client.get("/api/tournaments/open", headers=second).json()
    assert (
        next(t for t in listed_second if t["slug"] == "cup")["my_registration_state"]
        == "substitute"
    )

    listed_third = client.get("/api/tournaments/open", headers=third).json()
    assert (
        next(t for t in listed_third if t["slug"] == "cup")["my_registration_state"]
        == "cancelled"
    )


def test_open_registration_status_opens_on_and_closed(client, auth_headers):
    organizer = auth_headers()
    fencer = auth_headers(email="f1@example.com", name="F1")

    make_open_tournament(
        client, organizer, "future-open", registration_opens=str(TODAY + timedelta(days=1))
    )
    make_open_tournament(
        client, organizer, "past-close", registration_closes=str(TODAY - timedelta(days=1))
    )

    listed = client.get("/api/tournaments/open", headers=fencer).json()
    future_open = next(t for t in listed if t["slug"] == "future-open")
    assert future_open["registration_status"] == "opens_on"
    assert future_open["registration_opens_on"] == str(TODAY + timedelta(days=1))

    past_close = next(t for t in listed if t["slug"] == "past-close")
    assert past_close["registration_status"] == "closed"


def test_open_counts_team_disciplines_in_teams(client, auth_headers):
    """A team discipline on a published tournament must not break the list:
    its counts come from the team pair, never the fencer pair (which asserts
    on the wrong kind and used to 500 the whole endpoint)."""
    organizer = auth_headers()
    make_open_tournament(client, organizer, "cup")
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "Team-LS", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )

    fencer = auth_headers(email="f1@example.com", name="F1")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": [], "teams": [{"slug": "Team-LS", "name": "Wolves"}]},
        headers=fencer,
    )

    response = client.get("/api/tournaments/open", headers=fencer)
    assert response.status_code == 200
    cup = next(t for t in response.json() if t["slug"] == "cup")
    team = next(d for d in cup["disciplines"] if d["slug"] == "Team-LS")
    assert (team["taken"], team["capacity"], team["queue_length"]) == (1, 5, 0)


def test_mine_counts_team_disciplines_in_teams(client, auth_headers):
    """Same dispatch on the own-scope list, which builds the same DTO."""
    organizer = auth_headers()
    make_open_tournament(client, organizer, "cup", date=str(TODAY - timedelta(days=1)))
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "Team-LS", "weapon": "LS", "capacity": 5, "fee": 3000,
            "kind": "team", "team_min": 3, "team_max": 4,
        },
        headers=organizer,
    )

    response = client.get("/api/tournaments/mine", headers=organizer)
    assert response.status_code == 200
    cup = next(t for t in response.json() if t["slug"] == "cup")
    team = next(d for d in cup["disciplines"] if d["slug"] == "Team-LS")
    assert (team["taken"], team["capacity"]) == (0, 5)
