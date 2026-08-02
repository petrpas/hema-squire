from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import PaymentEvent, Registration
from tests.conftest import publish


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
    client.patch(
        "/api/tournaments/cup",
        json={
            "reservation_validity_days": 10,
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
    registration.expires_at = registration.registered_at + timedelta(days=10)
    session.commit()


def process(client, organizer):
    return client.post("/api/tournaments/cup/payments/process", headers=organizer).json()


def test_reminder_on_reminder_day_once(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)
    mailbox.sent.clear()

    assert process(client, organizer) == {"reminders": 0, "expired": 0}

    age_registration(2601001, days=6)
    assert process(client, organizer) == {"reminders": 1, "expired": 0}
    assert "Připomínka platby" in mailbox.sent[-1]["Subject"]
    assert len(list(mailbox.sent[-1].iter_attachments())) == 0  # no bank account set -> no QR

    # second run: already reminded, nothing happens
    assert process(client, organizer) == {"reminders": 0, "expired": 0}
    assert len(mailbox.sent) == 1

    session = db_session()
    kinds = session.scalars(select(PaymentEvent.kind)).all()
    assert kinds == ["reminder_sent"]


def test_expiry_frees_capacity_and_notifies(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer = enroll(client, auth_headers)
    mailbox.sent.clear()

    age_registration(2601001, days=11)  # past the 10-day window
    result = process(client, organizer)
    assert result == {"reminders": 0, "expired": 1}
    assert "Rezervace vypršela" in mailbox.sent[-1]["Subject"]

    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "expired"

    availability = client.get("/api/tournaments/cup/availability").json()
    assert availability[0]["free"] == 1
    assert client.get("/api/tournaments/cup/participants").json() == []

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
    from app.models import RegistrationState

    registration.registered_at = datetime.now(UTC) - timedelta(days=20)
    registration.expires_at = registration.registered_at + timedelta(days=10)
    registration.state = RegistrationState.PAID
    session.commit()

    assert process(client, organizer) == {"reminders": 0, "expired": 0}
    assert mailbox.sent == []


def test_queued_substitutes_untouched_by_lifecycle(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)
    waiting = auth_headers(email="b@example.com", name="B")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "wait_for_all": True},
        headers=waiting,
    )
    mailbox.sent.clear()

    session = db_session()
    queued = session.scalar(select(Registration).where(Registration.vs == 2601002))
    queued.registered_at = datetime.now(UTC) - timedelta(days=30)
    session.commit()

    # no expires_at on queued substitutes -> neither reminded nor expired
    assert process(client, organizer) == {"reminders": 0, "expired": 0}
    state = client.get("/api/tournaments/cup/my-registration", headers=waiting).json()
    assert state["state"] == "reserved"
