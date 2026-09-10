from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import ExtraCategory, ExtraItem, PaymentEvent, Registration, Tournament
from tests.conftest import credit_registration, enable_payments, publish


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={
            "reservation_validity_days": 7,
            "reminder_day": 5,
            "location": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
        },
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 1, "fee": 1000},
        headers=organizer,
    )
    publish(client, organizer, "cup")
    # simulate a tournament published before the bank account became
    # mandatory (design Decision 4) — the API guard cannot reach it
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.bank_account = None
    session.commit()


def enroll(client, auth_headers, email="jan@example.com"):
    fencer = auth_headers(email=email, name="Jan")
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201
    return fencer


def age_registration(vs, days):
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.registered_at = datetime.now(UTC) - timedelta(days=days)
    registration.expires_at = registration.registered_at + timedelta(days=7)
    session.commit()


def process(client, organizer):
    return client.post("/api/tournaments/cup/payments/process", headers=organizer).json()


def test_reminder_on_reminder_day_once(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)
    mailbox.sent.clear()

    assert process(client, organizer) == {"reminders": 0, "expired": 0, "seating_demoted": 0}

    age_registration(2601001, days=6)
    assert process(client, organizer) == {"reminders": 1, "expired": 0, "seating_demoted": 0}
    assert "Připomínka platby" in mailbox.sent[-1]["Subject"]
    assert len(list(mailbox.sent[-1].iter_attachments())) == 0  # no bank account set -> no QR

    # second run: already reminded, nothing happens
    assert process(client, organizer) == {"reminders": 0, "expired": 0, "seating_demoted": 0}
    assert len(mailbox.sent) == 1

    session = db_session()
    kinds = session.scalars(select(PaymentEvent.kind)).all()
    assert kinds == ["reminder_sent"]


def test_expiry_frees_capacity_and_notifies(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = enroll(client, auth_headers)
    mailbox.sent.clear()

    age_registration(2601001, days=8)  # past the 7-day window
    result = process(client, organizer)
    assert result == {"reminders": 0, "expired": 1, "seating_demoted": 0}
    assert "Rezervace vypršela" in mailbox.sent[-1]["Subject"]

    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "expired"

    availability = client.get("/api/tournaments/cup/availability").json()
    assert availability[0]["free"] == 1
    assert client.get("/api/tournaments/cup/participants").json()["participants"] == []

    session = db_session()
    kinds = session.scalars(select(PaymentEvent.kind)).all()
    assert kinds == ["reservation_expired"]


def test_paid_registrations_never_reminded_or_expired(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)
    mailbox.sent.clear()

    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == 2601001))

    registration.registered_at = datetime.now(UTC) - timedelta(days=20)
    registration.expires_at = registration.registered_at + timedelta(days=7)
    session.commit()
    credit_registration(session, registration, registration.total_amount * 100)

    assert process(client, organizer) == {"reminders": 0, "expired": 0, "seating_demoted": 0}
    assert mailbox.sent == []


def test_a_surcharge_does_not_expire_a_registration_on_its_old_deadline(
    client, auth_headers, mailbox
):
    """A raise beyond tolerance unsettles the registration, and the deadline it
    registered under is long past — so without the fresh window the amendment
    opens, the very next pass would expire a fencer who had paid, over a
    correction the organizer made."""
    organizer = auth_headers()
    setup(client, organizer)
    fencer = enroll(client, auth_headers)
    # written directly: `setup` above clears the bank account to model a
    # tournament published before it was mandatory, and the extra-items
    # endpoint refuses an incomplete setup
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    item = ExtraItem(
        tournament_id=tournament.id,
        name="Afterparty ticket",
        category=ExtraCategory.AFTERPARTY,
        price=300,
    )
    session.add(item)
    session.commit()

    registration = session.scalar(select(Registration).where(Registration.vs == 2601001))
    registration.registered_at = datetime.now(UTC) - timedelta(days=20)
    registration.expires_at = registration.registered_at + timedelta(days=7)
    session.commit()
    credit_registration(session, registration, registration.total_amount * 100)

    amended = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={
            "disciplines": ["LS"],
            "extras": [{"extra_item_id": item.id, "qty": 1}],
        },
        headers=fencer,
    ).json()
    assert amended["state"] == "reserved"  # 1000 credited against 1300 owed
    mailbox.sent.clear()

    assert process(client, organizer) == {"reminders": 0, "expired": 0, "seating_demoted": 0}
    assert mailbox.sent == []
    assert client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"] == (
        "reserved"
    )


def test_queued_substitutes_untouched_by_lifecycle(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)
    waiting = auth_headers(email="b@example.com", name="B")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=waiting,
    )
    mailbox.sent.clear()

    session = db_session()
    queued = session.scalar(select(Registration).where(Registration.vs == 2601002))
    queued.registered_at = datetime.now(UTC) - timedelta(days=30)
    session.commit()

    # no expires_at on queued substitutes -> neither reminded nor expired
    assert process(client, organizer) == {"reminders": 0, "expired": 0, "seating_demoted": 0}
    state = client.get("/api/tournaments/cup/my-registration", headers=waiting).json()
    assert state["state"] == "reserved"
