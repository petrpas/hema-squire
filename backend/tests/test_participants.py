from sqlalchemy import select

from app.db import get_session
from app.main import app
from app.models import Registration, RegistrationState
from tests.conftest import enable_payments, publish


def setup_tournament(client, organizer, *, payments=True):
    """Payments on by default: the unpaid-list setting these tests are about
    only means anything where Squire collects. A tournament it does not collect
    for draws no confirmed/unconfirmed distinction at all (spec registration,
    Public participant list)."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 1, "fee": 500},
        headers=organizer,
    )
    if payments:
        enable_payments(client, organizer, "cup")
        client.patch(
            "/api/tournaments/cup",
            json={"bank_account": "CZ6508000000192000145399"},
            headers=organizer,
        )
    publish(client, organizer, "cup")


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
    mark_paid(2601001)
    register(client, auth_headers(email="b@example.com", name="Boris"))

    listing = client.get("/api/tournaments/cup/participants").json()["participants"]
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
    mark_paid(2601001)
    register(client, auth_headers(email="b@example.com", name="Boris"))

    listing = client.get("/api/tournaments/cup/participants").json()["participants"]
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
    )
    cancelled = auth_headers(email="c@example.com", name="Cyril")
    register(client, cancelled)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=cancelled)

    listing = client.get("/api/tournaments/cup/participants").json()["participants"]
    assert [p["name"] for p in listing] == ["Adéla"]


def test_substitute_entry_not_shown_in_disciplines(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("SB",))
    mark_paid(2601001)

    listing = client.get("/api/tournaments/cup/participants").json()["participants"]
    assert listing[0]["disciplines"] == ["SB"]


# ------------------------------- where Squire guarantees no payment state


def test_a_payments_off_list_shows_entrants_without_a_payment_claim(
    client, auth_headers
):
    """The defect this fixes, and it was live: nothing on a payments-off
    tournament ever reaches PAID, so the list was either empty or entirely
    "unconfirmed" — while `registration`'s own lifecycle rule says such a
    registration is presented as confirmed."""
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    register(client, auth_headers(email="b@example.com", name="Boris"))

    body = client.get("/api/tournaments/cup/participants").json()
    assert body["payment_state_known"] is False
    assert [(p["name"], p["status"]) for p in body["participants"]] == [
        ("Adéla", None),
        ("Boris", None),
    ]


def test_the_unpaid_setting_does_not_apply_where_nothing_is_owed(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    client.patch(
        "/api/tournaments/cup",
        json={"unpaid_list_treatment": "hidden"},
        headers=organizer,
    )
    register(client, auth_headers(email="a@example.com", name="Adéla"))

    body = client.get("/api/tournaments/cup/participants").json()
    # `hidden` would have emptied the list entirely; there are no unpaid
    # reservations in the sense that setting means
    assert [p["name"] for p in body["participants"]] == ["Adéla"]


def test_a_live_list_does_not_date_itself(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    assert client.get("/api/tournaments/cup/participants").json()["as_of"] is None


def test_an_organizer_kept_list_states_when_the_roster_reached_squire(
    client, auth_headers
):
    from datetime import UTC, datetime

    from app.models import ImportBatch, Tournament

    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    register(client, auth_headers(email="a@example.com", name="Adéla"))

    session = next(app.dependency_overrides[get_session]())
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.registrations_kept_by = "organizer"
    uploaded = datetime(2026, 8, 30, 9, 15, tzinfo=UTC)
    session.add(
        ImportBatch(
            tournament_id=tournament.id,
            filename="roster.csv",
            uploaded_by=1,
            uploaded_at=uploaded,
            row_count=54,
        )
    )
    session.commit()

    body = client.get("/api/tournaments/cup/participants").json()
    assert body["payment_state_known"] is False
    assert body["as_of"] is not None
    assert body["as_of"].startswith("2026-08-30")
    # a fact about when, never a judgement about currency
    assert [p["name"] for p in body["participants"]] == ["Adéla"]
