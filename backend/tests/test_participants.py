from sqlalchemy import select

from app.db import get_session
from app.main import app
from app.models import Registration, RegistrationState


def setup_tournament(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "SB", "capacity": 1, "fee": 500},
        headers=organizer,
    )


def register(client, headers, disciplines=("LS",), **overrides):
    return client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines), **overrides},
        headers=headers,
    )


def mark_paid(vs):
    session = next(app.dependency_overrides[get_session]())
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.state = RegistrationState.PAID
    session.commit()


def test_greyed_default_shows_unpaid_as_unconfirmed(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    mark_paid(1000001)
    register(client, auth_headers(email="b@example.com", name="Boris"))

    listing = client.get("/api/tournaments/cup/participants").json()
    assert [(p["name"], p["status"]) for p in listing] == [
        ("Adéla", "confirmed"),
        ("Boris", "unconfirmed"),
    ]


def test_hidden_setting_omits_unpaid(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch(
        "/api/tournaments/cup", json={"unpaid_list_treatment": "hidden"}, headers=organizer
    )
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    mark_paid(1000001)
    register(client, auth_headers(email="b@example.com", name="Boris"))

    listing = client.get("/api/tournaments/cup/participants").json()
    assert [(p["name"], p["status"]) for p in listing] == [("Adéla", "confirmed")]


def test_substitutes_and_cancelled_never_listed(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    first = auth_headers(email="a@example.com", name="Adéla")
    register(client, first, disciplines=("SB",))
    register(
        client,
        auth_headers(email="b@example.com", name="Boris"),
        disciplines=("SB",),
        wait_for_all=True,
    )
    cancelled = auth_headers(email="c@example.com", name="Cyril")
    register(client, cancelled)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=cancelled)

    listing = client.get("/api/tournaments/cup/participants").json()
    assert [p["name"] for p in listing] == ["Adéla"]


def test_substitute_entry_not_shown_in_disciplines(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("SB",))
    mark_paid(1000001)

    listing = client.get("/api/tournaments/cup/participants").json()
    assert listing[0]["disciplines"] == ["SB"]
