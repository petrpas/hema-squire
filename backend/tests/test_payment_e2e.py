"""Task 6.2 — payment lifecycle end-to-end.

One continuous narrative per path, through the public API only:
- happy path: register → reservation with VS and expiry → confirmation email
  carrying the SPAYD QR → Fio poll ingests the bank transfer → VS match →
  paid → receipt email → confirmed on the public participant list;
- expiry path: reminder on the reminder day → expiry after the validity
  window → capacity freed for the next fencer → a payment arriving after
  expiry is flagged for review, never silently accepted.
"""

import datetime
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

from app.bank import IncomingTransaction, get_fio_client
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import Registration
from app.spayd import spayd_string

IBAN = "CZ6508000000192000145399"


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def to(self, address):
        return [m for m in self.sent if m["To"] == address]


class FakeFio:
    def __init__(self):
        self.transactions = []

    def fetch(self, token, date_from, date_to):
        return self.transactions


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


@pytest.fixture
def fio():
    client = FakeFio()
    app.dependency_overrides[get_fio_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_fio_client, None)


def transfer(vs: int, amount_czk: int, external_id: str = "9001") -> IncomingTransaction:
    return IncomingTransaction(
        external_id=external_id,
        date=datetime.date(2026, 7, 15),
        amount_cents=amount_czk * 100,
        currency="CZK",
        vs=vs,
        message=f"VS {vs}",
        payer_name="Jan Novák",
        payer_account="123/0800",
    )


def setup(client, organizer, capacity=10):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"bank_account": IBAN, "fio_token": "test-token",
              "reservation_validity_days": 10, "reminder_day": 5,
              "amount_tolerance_percent": 5,
              "location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": capacity, "fee": 1000},
        headers=organizer,
    )


def age_registration(vs, days):
    session = next(app.dependency_overrides[get_session]())
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.registered_at = datetime.datetime.now(UTC) - timedelta(days=days)
    registration.expires_at = registration.registered_at + timedelta(days=10)
    session.commit()


def test_happy_path_reserve_qr_match_paid(client, auth_headers, mailbox, fio):
    organizer = auth_headers()
    setup(client, organizer)

    # reserve: state, VS, expiry window
    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    registration = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()
    vs, amount = registration["vs"], registration["total_amount"]
    assert registration["state"] == "reserved"
    assert amount == 1000
    expires = datetime.datetime.fromisoformat(registration["expires_at"])
    registered = datetime.datetime.fromisoformat(registration["registered_at"])
    assert (expires - registered).days == 10

    # confirmation email carries the SPAYD QR for exactly this payment
    (confirmation,) = mailbox.to("jan@example.com")
    (attachment,) = list(confirmation.iter_attachments())
    assert attachment.get_filename() == "platba-qr.png"
    assert attachment.get_content().startswith(b"\x89PNG")
    expected_spayd = spayd_string(IBAN, amount, vs, f"VS{vs} Cup", "CZK")
    assert f"AM:{amount}.00" in expected_spayd and f"X-VS:{vs}" in expected_spayd
    body = confirmation.get_body(("plain",)).get_content()
    assert str(vs) in body  # VS quoted in the body too

    # public list before payment: greyed unconfirmed (owner default)
    (entry,) = client.get("/api/tournaments/cup/participants").json()
    assert entry["status"] == "unconfirmed"

    # the fencer pays within tolerance (980 vs 1000 at 5%); Fio poll picks it up
    fio.transactions = [transfer(vs, 980)]
    poll = client.post(
        "/api/tournaments/cup/payments/fio-poll", headers=organizer
    ).json()
    assert poll == {"new": 1, "duplicate": 0, "matched": 1, "flagged": 0, "unmatched": 0}

    registration = client.get(
        "/api/tournaments/cup/my-registration", headers=fencer
    ).json()
    assert registration["state"] == "paid"
    assert registration["paid_at"] is not None

    # receipt email and public confirmation
    assert len(mailbox.to("jan@example.com")) == 2
    (entry,) = client.get("/api/tournaments/cup/participants").json()
    assert entry["status"] == "confirmed"

    # idempotence: polling the same transaction again changes nothing
    again = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert again["new"] == 0 and again["matched"] == 0
    assert len(mailbox.to("jan@example.com")) == 2


def test_expiry_path_reminder_expire_free_capacity_flag_late_payment(
    client, auth_headers, mailbox, fio
):
    organizer = auth_headers()
    setup(client, organizer, capacity=1)
    fencer = auth_headers(email="jan@example.com", name="Jan Novák")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]

    def process():
        return client.post(
            "/api/tournaments/cup/payments/process", headers=organizer
        ).json()

    # day 5: one reminder, not repeated
    age_registration(vs, days=5)
    assert process() == {"reminders": 1, "expired": 0}
    assert process() == {"reminders": 0, "expired": 0}
    assert len(mailbox.to("jan@example.com")) == 2  # confirmation + reminder

    # day 11: reservation expires, fencer notified
    age_registration(vs, days=11)
    assert process() == {"reminders": 0, "expired": 1}
    registration = client.get(
        "/api/tournaments/cup/my-registration", headers=fencer
    ).json()
    assert registration["state"] == "expired"
    assert len(mailbox.to("jan@example.com")) == 3
    assert client.get("/api/tournaments/cup/participants").json() == []

    # the freed slot is available again: the discipline was at capacity 1
    (availability,) = client.get("/api/tournaments/cup/availability").json()
    assert availability["free"] == 1
    other = auth_headers(email="eva@example.com", name="Eva Malá")
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=other
    )
    assert response.status_code == 201
    assert not response.json()["entries"][0]["is_substitute"]

    # money arriving after expiry is flagged for review, never auto-accepted
    fio.transactions = [transfer(vs, 1000, external_id="9002")]
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll["flagged"] == 1 and poll["matched"] == 0
    assert client.get(
        "/api/tournaments/cup/my-registration", headers=fencer
    ).json()["state"] == "expired"
    (queued,) = client.get(
        "/api/tournaments/cup/payments/unmatched", headers=organizer
    ).json()
    assert queued["status"] == "flagged"
    assert queued["vs"] == vs
