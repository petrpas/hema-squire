"""What the messages say: the tournament link, dates, the payment block per
payment mode (specs outgoing-mail, registration, payments)."""

import ast
import inspect
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app import emails, spayd
from app.db import get_session
from app.i18n import format_date
from app.mail import get_mailer
from app.main import app
from app.models import Registration, Tournament
from app.setup import local_date
from tests.conftest import credit_registration, enable_payments, publish, set_fio_token


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


def body(message) -> str:
    return message.get_body(preferencelist=("plain",)).get_content()


def tournament(client, organizer, *, language="cs", fee=1000, **settings):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05", "language": language},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"reservation_validity_days": 7, "reminder_day": 5, **settings},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": fee},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def register(client, headers):
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def the_registration() -> Registration:
    registration = db_session().scalar(select(Registration))
    assert registration is not None
    return registration


# --- the tournament link ---------------------------------------------------


def test_an_account_holders_confirmation_links_the_tournament_and_no_manage_link(
    client, auth_headers, mailbox
):
    tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    text = body(mailbox.sent[-1])
    assert "http://localhost:5173/t/cup" in text
    assert "/manage#" not in text


def _sends_that_bypass_letter() -> list[str]:
    """`send_*` functions about a registration that build their message without
    `_letter` and without stating the tournament link themselves."""
    account_mail = {
        "send_signup_verification",
        "send_password_reset",
        "send_password_changed",
    }
    tree = ast.parse(inspect.getsource(emails))
    offenders = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("send_"):
            continue
        if node.name in account_mail:
            continue
        called = {
            call.func.id
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        builds = "build_message" in called
        if builds and "tournament_link" not in called:
            offenders.append(node.name)
    return offenders


def test_no_registration_send_bypasses_the_tournament_link():
    assert _sends_that_bypass_letter() == []


# --- dates -----------------------------------------------------------------


def test_no_send_formats_a_date_of_its_own():
    source = inspect.getsource(emails)
    assert ".isoformat()" not in source
    assert "strftime" not in source


def _window_close(registration: Registration) -> date:
    assert registration.expires_at is not None
    return local_date(registration.tournament, registration.expires_at)


def test_a_czech_confirmation_states_its_window_close_as_czech_writes_it(
    client, auth_headers, mailbox
):
    tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    day = _window_close(the_registration())
    assert f"{day.day}. {day.month}. {day.year}" in body(mailbox.sent[-1])
    assert not re.search(r"\d{4}-\d{2}-\d{2}", body(mailbox.sent[-1]))


def test_dates_read_as_each_language_writes_them():
    assert format_date(date(2027, 3, 1), "en") == "1 March 2027"
    assert format_date(date(2026, 10, 25), "cs") == "25. 10. 2026"


def test_an_instant_is_stated_as_its_day_where_the_tournament_is_held():
    held_in_prague = Tournament(slug="cup", display_name="Cup", timezone="Europe/Prague")
    # 23:30 UTC on 1 March is already 2 March in Prague
    instant = datetime(2027, 3, 1, 23, 30, tzinfo=UTC)
    assert emails._day(held_in_prague, instant, "cs") == "2. 3. 2027"
    assert emails._day(held_in_prague, instant - timedelta(hours=2), "cs") == "1. 3. 2027"


# --- the payment block per mode ------------------------------------------------

IBAN = "CZ6508000000192000145399"


@pytest.fixture
def readable_qr(monkeypatch):
    """QR codes as their SPAYD text, so a test reads the amount each encodes."""
    monkeypatch.setattr(spayd, "qr_png", lambda text: text.encode())


def codes(message) -> dict[str, str]:
    """Attachment filename → the SPAYD amount and currency it encodes."""
    found = {}
    for part in message.iter_attachments():
        text = part.get_content().decode()
        fields = dict(field.split(":", 1) for field in text.split("*")[2:])
        amount = Decimal(fields["AM"])
        stated = int(amount) if amount == amount.to_integral_value() else amount
        found[part.get_filename()] = f"{stated} {fields['CC']}"
    return found


def mode_tournament(client, organizer, mode, **params):
    tournament(
        client,
        organizer,
        fee=1800,
        bank_account=IBAN,
        payment_mode=mode,
        seating_deadline="2099-11-01",
        **params,
    )


def deposit_tournament(client, organizer, **params):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    set_fio_token(client, organizer, "cup", "test-feed-token")
    payload = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "reminder_day": 5,
        "payment_mode": "deposit",
        "deposit_amount": 500,
        "seating_deadline": "2099-11-01",
        **params,
    }
    response = client.patch("/api/tournaments/cup", json=payload, headers=organizer)
    assert response.status_code == 200, response.text
    discipline = {"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1800}
    if "deposit_amount_eur" in params:
        discipline["fee_eur"] = 72
    client.post("/api/tournaments/cup/disciplines", json=discipline, headers=organizer)
    publish(client, organizer, "cup")


def test_a_deposit_confirmation_carries_the_deposit_and_the_total(
    client, auth_headers, mailbox, readable_qr
):
    deposit_tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    message = mailbox.sent[-1]
    text = body(message)
    assert "Záloha: 500 Kč" in text
    assert "Celkem: 1800 Kč, doplatek do 1. 11. 2099" in text
    assert "fronty náhradníků" in text
    assert codes(message) == {
        "platba-zaloha.png": "500 CZK",
        "platba-celkem.png": "1800 CZK",
    }


def test_a_deposit_confirmation_with_eur_carries_four_labelled_codes(
    client, auth_headers, mailbox, readable_qr
):
    deposit_tournament(client, auth_headers(), eur_payments_enabled=True, deposit_amount_eur=20)
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    assert codes(mailbox.sent[-1]) == {
        "platba-zaloha.png": "500 CZK",
        "platba-zaloha-eur.png": "20 EUR",
        "platba-celkem.png": "1800 CZK",
        "platba-celkem-eur.png": "72 EUR",
    }


def test_a_reminder_after_the_deposit_asks_for_the_balance_only(
    client, auth_headers, mailbox, readable_qr
):
    deposit_tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))
    session = db_session()
    registration = session.scalar(select(Registration))
    assert registration is not None
    credit_registration(session, registration, 50000)
    registration.expires_at = None  # the deposit threshold closes the window
    session.commit()

    emails.send_payment_reminder(
        mailbox, registration.tournament, registration.fencer, registration
    )

    message = mailbox.sent[-1]
    assert "Zbývá doplatit: 1300 Kč" in body(message)
    assert "Splatné do: 1. 11. 2099" in body(message)
    assert codes(message) == {"platba-doplatek.png": "1300 CZK"}


def test_a_reservation_mode_confirmation_states_the_seating_deadline(
    client, auth_headers, mailbox, readable_qr
):
    mode_tournament(client, auth_headers(), "reservation")
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    text = body(mailbox.sent[-1])
    assert "Splatné do: 1. 11. 2099" in text
    assert "ten den přesune do fronty náhradníků" in text
    assert "uvolní" not in text
    assert "Rezervace platí do" not in text
    assert codes(mailbox.sent[-1]) == {"platba-celkem.png": "1800 CZK"}


def test_a_reservation_mode_reminder_states_the_seating_deadline(
    client, auth_headers, mailbox, readable_qr
):
    mode_tournament(client, auth_headers(), "reservation")
    register(client, auth_headers(email="jan@example.com", name="Jan"))
    registration = the_registration()

    emails.send_payment_reminder(
        mailbox, registration.tournament, registration.fencer, registration
    )

    text = body(mailbox.sent[-1])
    assert "Splatné do: 1. 11. 2099" in text
    assert "fronty náhradníků" in text
    assert "uvolní" not in text


def test_an_immediate_confirmation_states_the_window_and_the_release(
    client, auth_headers, mailbox, readable_qr
):
    mode_tournament(client, auth_headers(), "immediate")
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    day = _window_close(the_registration())
    text = body(mailbox.sent[-1])
    assert f"Celkem k úhradě: 1800 Kč\nSplatné do: {day.day}. {day.month}. {day.year}" in text
    assert "místo se automaticky uvolní" in text
    assert codes(mailbox.sent[-1]) == {"platba-celkem.png": "1800 CZK"}


def test_an_english_tournaments_confirmation_is_english_throughout(client, auth_headers, mailbox):
    tournament(client, auth_headers(), language="en")
    register(client, auth_headers(email="jan@example.com", name="Jan"))

    message = mailbox.sent[-1]
    assert message["Subject"] == "Registration for Cup — payment instructions"
    text = body(message)
    assert text.startswith("Hi Jan,")
    assert "Total due: 1000 Kč" in text
    assert "Tournament page: " in text
    assert "Cup team" in text
    for czech in ("Ahoj", "Celkem", "Účet", "Splatné", "Tým"):
        assert czech not in text
