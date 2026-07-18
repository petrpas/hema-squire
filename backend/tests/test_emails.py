import pytest

from app.mail import get_mailer
from app.main import app
from app.spayd import qr_png, spayd_string


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


def test_spayd_string_format():
    result = spayd_string("CZ6508000000192000145399", 1300, 1000001, "VS1000001 Na Duel!")
    assert result == (
        "SPD*1.0*ACC:CZ6508000000192000145399*AM:1300.00*CC:CZK"
        "*X-VS:1000001*MSG:VS1000001 Na Duel!"
    )


def test_spayd_sanitizes_message():
    result = spayd_string("CZ65 0800 0000 1920 0014 5399", 100, 7, "a*b\nc" + "x" * 100)
    assert "ACC:CZ6508000000192000145399" in result
    msg = result.split("MSG:")[1]
    assert "*" not in msg and "\n" not in msg
    assert len(msg) <= 60


def test_qr_png_magic_bytes():
    png = qr_png("SPD*1.0*ACC:CZ00*AM:1.00*CC:CZK*X-VS:1*MSG:test")
    assert png.startswith(b"\x89PNG")


def _setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Na Duel! 2026", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"bank_account": "CZ6508000000192000145399", "afterparty_fee": 300},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": 1, "fee": 800},
        headers=organizer,
    )


def test_confirmation_email_localized_with_qr(client, auth_headers, mailbox):
    organizer = auth_headers()
    _setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan")
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "afterparty": True},
        headers=fencer,
    )
    assert response.status_code == 201

    assert len(mailbox.sent) == 1
    message = mailbox.sent[0]
    assert message["To"] == "jan@example.com"
    assert "pokyny k platbě" in message["Subject"]
    body = message.get_body(("plain",)).get_content()
    assert "Variabilní symbol: 1000001" in body
    assert "1100 Kč" in body
    assert "CZ6508000000192000145399" in body

    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "image/png"


def test_queued_email_has_no_qr_and_no_amount(client, auth_headers, mailbox):
    organizer = auth_headers()
    _setup(client, organizer)
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=auth_headers(email="a@example.com", name="A"),
    )
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "wait_for_all": True},
        headers=auth_headers(email="b@example.com", name="B"),
    )
    assert response.status_code == 201

    queued_message = mailbox.sent[-1]
    assert "náhradník" in queued_message["Subject"]
    assert list(queued_message.iter_attachments()) == []


def test_admission_sends_payment_email(client, auth_headers, mailbox):
    organizer = auth_headers()
    _setup(client, organizer)
    first = auth_headers(email="a@example.com", name="A")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=first)
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "wait_for_all": True},
        headers=auth_headers(email="b@example.com", name="B"),
    )
    client.post("/api/tournaments/cup/my-registration/cancel", headers=first)

    from sqlalchemy import select

    from app.db import get_session
    from app.models import Registration

    session = next(app.dependency_overrides[get_session]())
    waiting_id = session.scalar(select(Registration.id).where(Registration.vs == 1000002))

    admitted = client.post(
        f"/api/tournaments/cup/registrations/{waiting_id}/admit/LS", headers=organizer
    )
    assert admitted.status_code == 200

    payment_message = mailbox.sent[-1]
    assert payment_message["To"] == "b@example.com"
    assert "pokyny k platbě" in payment_message["Subject"]
    assert "Variabilní symbol: 1000002" in payment_message.get_body(("plain",)).get_content()
    assert len(list(payment_message.iter_attachments())) == 1
