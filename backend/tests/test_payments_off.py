"""What the payments feature does when it is off (design tournament-modes D5,
D6): the machinery is suspended, not merely hidden. Squire requires no bank
account to publish, asks for no money at registration, expires nothing, sends
no payment mail and reconciles nothing — while every stored payment value
survives untouched, ready for the feature to be turned back on."""

import io
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import BankTransaction, Registration, RegistrationState, Tournament
from app.scheduler import run_tournament_tick
from tests.conftest import enable_payments, publish, set_features

IBAN = "CZ6508000000192000145399"


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


def setup(client, organizer, *, capacity=10, **patch):
    """A published, priced tournament in easy mode — no bank account anywhere."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    base = {"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]}
    response = client.patch("/api/tournaments/cup", json=base | patch, headers=organizer)
    assert response.status_code == 200, response.text
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": capacity, "fee": 1200},
        headers=organizer,
    )


def enroll(client, auth_headers, email="jan@example.com", **body):
    fencer = auth_headers(email=email, name="Jan")
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], **body},
        headers=fencer,
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()


def tournament_row():
    return db_session().scalar(select(Tournament).where(Tournament.slug == "cup"))


def statement_csv(vs: int, amount: str = "1200,00") -> bytes:
    return (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
        f"1;01.08.2026;{amount};CZK;{vs};;;;;\n"
    ).encode()


# ------------------------------------------------------------- publication


def test_priced_tournament_publishes_without_a_bank_account(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["bank_account"] is None
    assert detail["setup_missing"] == []

    published = client.post("/api/tournaments/cup/publish", headers=organizer)
    assert published.status_code == 200, published.text


def test_turning_payments_on_makes_the_account_mandatory_again(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    client.post("/api/tournaments/cup/publish", headers=organizer)

    # accepted even on a published tournament: the mode is how the organizer
    # reaches the field that fixes it
    assert enable_payments(client, organizer, "cup")["setup_missing"] == ["bank_account"]
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["setup_missing"] == ["bank_account"]


# ------------------------------------------------------------- registration


def test_registration_is_seated_with_no_due_date(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    publish(client, organizer, "cup")
    _, registration = enroll(client, auth_headers)

    assert registration["state"] == "reserved"
    assert registration["expires_at"] is None
    # the total is still computed and stored — it states what the tournament
    # costs, settled outside Squire
    assert registration["total_amount"] == 1200


def test_confirmation_carries_the_total_and_nothing_about_paying_it(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    publish(client, organizer, "cup")
    _, registration = enroll(client, auth_headers)

    message = mailbox.sent[-1]
    body = message.get_body(preferencelist=("plain",)).get_content()
    assert "1200" in body
    assert IBAN not in body
    assert str(registration["vs"]) not in body
    assert "Variabilní symbol" not in body
    assert list(message.iter_attachments()) == []


def test_no_in_app_payment_instructions(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer, bank_account=IBAN)
    publish(client, organizer, "cup")
    fencer, _ = enroll(client, auth_headers)

    response = client.get(
        "/api/tournaments/cup/my-registration/payment", headers=fencer
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "payments_disabled"


# ------------------------------------------------------------- the scheduler


def test_nothing_expires_or_is_reminded_across_a_long_tick(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer, reservation_validity_days=2, reminder_day=1)
    publish(client, organizer, "cup")
    _, registration = enroll(client, auth_headers)
    mailbox.sent.clear()

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.registered_at = datetime.now(UTC) - timedelta(days=60)
    session.commit()

    result = run_tournament_tick(session, tournament_row(), CollectingMailer())
    assert result["expired"] == 0
    assert result["reminders"] == 0
    assert mailbox.sent == []

    assert (
        db_session()
        .scalar(select(Registration).where(Registration.vs == registration["vs"]))
        .state
        == RegistrationState.RESERVED
    )


def test_lifecycle_endpoint_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    publish(client, organizer, "cup")

    response = client.post("/api/tournaments/cup/payments/process", headers=organizer)
    assert response.status_code == 409
    assert response.json()["detail"] == "payments_disabled"


# ------------------------------------------------------------- reconciliation


def test_statement_ingestion_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    publish(client, organizer, "cup")
    _, registration = enroll(client, auth_headers)

    response = client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={
            "file": ("v.csv", io.BytesIO(statement_csv(registration["vs"])), "text/csv")
        },
        headers=organizer,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "payments_disabled"
    assert db_session().scalars(select(BankTransaction)).all() == []


def test_manual_linking_is_refused(client, auth_headers):
    """Refused rather than accepted with no effect: an organizer working
    against the wrong tournament must learn that."""
    organizer = auth_headers()
    setup(client, organizer)
    publish(client, organizer, "cup")
    _, registration = enroll(client, auth_headers)

    response = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": 1, "vs": [registration["vs"]]},
        headers=organizer,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "payments_disabled"


# ------------------------------------------------------------- the queue


def test_promotion_opens_no_payment_window(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer, capacity=1)
    publish(client, organizer, "cup")
    enroll(client, auth_headers, email="first@example.com")
    _, queued = enroll(client, auth_headers, email="second@example.com")
    assert queued["entries"][0]["is_substitute"] is True

    session = db_session()
    registration_id = session.scalar(
        select(Registration.id).where(Registration.vs == queued["vs"])
    )
    # free the seat so the promotion is allowed
    seated = session.scalar(select(Registration).where(Registration.vs != queued["vs"]))
    seated.state = RegistrationState.CANCELLED
    session.commit()
    mailbox.sent.clear()

    promoted = client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/admit/LS", headers=organizer
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["expires_at"] is None
    assert promoted.json()["entries"][0]["is_substitute"] is False
    # told they have a place, with the amount as information and no QR
    assert list(mailbox.sent[-1].iter_attachments()) == []
    assert IBAN not in mailbox.sent[-1].get_body(preferencelist=("plain",)).get_content()


# ------------------------------------------------------------- turning it on


def test_stored_payment_settings_survive_the_feature_being_turned_off(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    enable_payments(client, organizer, "cup")
    configured = client.patch(
        "/api/tournaments/cup",
        json={
            "bank_account": IBAN,
            "payment_mode": "deposit",
            "deposit_amount": 300,
            "reservation_validity_days": 5,
            "reminder_day": 3,
            "registration_closes": "2026-11-01",
            "seating_deadline": "2026-10-01",
        },
        headers=organizer,
    )
    assert configured.status_code == 200, configured.text
    publish(client, organizer, "cup")
    _, paid = enroll(client, auth_headers)
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(statement_csv(paid["vs"], "300,00")), "text/csv")},
        headers=organizer,
    )
    before = client.get("/api/tournaments/cup", headers=organizer).json()
    transactions_before = client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json()
    paid_before = db_session().scalar(
        select(Registration).where(Registration.vs == paid["vs"])
    ).amount_paid_cents
    assert transactions_before and paid_before == 30000

    set_features(client, organizer, "cup")

    off = client.get("/api/tournaments/cup", headers=organizer).json()
    assert off["bank_account"] == before["bank_account"]
    assert off["payment_mode"] == "deposit"
    assert off["deposit_amount"] == 300
    assert off["reservation_validity_days"] == 5
    assert off["seating_deadline"] == before["seating_deadline"]
    assert (
        client.get("/api/tournaments/cup/payments/transactions", headers=organizer).json()
        == transactions_before
    )
    assert (
        db_session()
        .scalar(select(Registration).where(Registration.vs == paid["vs"]))
        .amount_paid_cents
        == paid_before
    )

    # and back on again, with everything present
    on = enable_payments(client, organizer, "cup")
    assert on["bank_account"] == before["bank_account"]
    assert on["payment_mode"] == "deposit"
    assert on["deposit_amount"] == 300


def test_registrations_taken_while_payments_were_off_never_expire(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer, reservation_validity_days=2, reminder_day=1)
    publish(client, organizer, "cup")
    _, registration = enroll(client, auth_headers)

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.registered_at = datetime.now(UTC) - timedelta(days=60)
    session.commit()

    client.patch(
        "/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer
    )
    enable_payments(client, organizer, "cup")
    mailbox.sent.clear()

    result = run_tournament_tick(session, tournament_row(), CollectingMailer())
    assert result["expired"] == 0
    reloaded = db_session().scalar(
        select(Registration).where(Registration.vs == registration["vs"])
    )
    assert reloaded.state == RegistrationState.RESERVED
    assert reloaded.expires_at is None
