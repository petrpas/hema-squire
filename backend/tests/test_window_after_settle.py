"""A paid registration is under no payment window, and losing the paid reading
opens a fresh one (spec payments; change close-window-on-settle).

Every scenario here was a fencer who paid and then expired within one tick of
something an organizer did after the window they registered under had passed
(`openspec/payments_gaps.md`, P3). Each test pays, pushes the original window
into the past as time would, takes the paid reading away, and runs the real
expiry pass."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app import ledger, scheduler
from app.db import get_session
from app.main import app
from app.models import CreditSource, Currency, Registration, RegistrationState, Tournament
from tests.conftest import credit_registration, enable_payments, publish

IBAN = "CZ6508000000192000145399"


class _Mailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


def db_session():
    return next(app.dependency_overrides[get_session]())


def make_tournament(client, organizer, *, eur: bool = False):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    patch = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "reminder_day": 2,
        "city": "Brno",
        "organizers": [{"name": "Org", "link": None}],
    }
    if eur:
        patch |= {"eur_payments_enabled": True, "bank_account_holder": "TJ Šerm Praha"}
    response = client.patch("/api/tournaments/cup", json=patch, headers=organizer)
    assert response.status_code == 200, response.text
    discipline = {"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000}
    if eur:
        discipline["fee_eur"] = 40
    client.post("/api/tournaments/cup/disciplines", json=discipline, headers=organizer)
    publish(client, organizer, "cup")


def enroll(client, auth_headers, email="jan@example.com") -> int:
    fencer = auth_headers(email=email, name=email.split("@")[0])
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    vs = response.json()["vs"]
    registration_id = db_session().scalar(select(Registration.id).where(Registration.vs == vs))
    assert registration_id is not None
    return registration_id


def window_passed(registration_id: int) -> None:
    """The registration's original window, a week gone — what it carries when
    the tick has not yet closed it, or what it carried before this change."""
    session = db_session()
    registration = session.get(Registration, registration_id)
    assert registration is not None
    registration.expires_at = datetime.now(UTC) - timedelta(days=7)
    registration.reminded_at = datetime.now(UTC) - timedelta(days=9)
    session.commit()


def tick() -> _Mailer:
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    mailer = _Mailer()
    scheduler.process_expiries(session, tournament, mailer)
    return mailer


def assert_owing_under_fresh_window(registration_id: int) -> None:
    registration = db_session().get(Registration, registration_id)
    assert registration is not None
    assert registration.state == RegistrationState.RESERVED
    assert not registration.settled
    assert registration.expires_at is not None
    expires_at = registration.expires_at.replace(tzinfo=UTC)
    assert expires_at > datetime.now(UTC) + timedelta(days=6)
    # re-armed, so the ordinary reminder follows the new window
    assert registration.reminded_at is None


def pay(registration_id: int, *, currency: Currency | None = None, cents: int = 100_000) -> int:
    """Credit the registration and return the credit's source id."""
    session = db_session()
    registration = session.get(Registration, registration_id)
    assert registration is not None
    return credit_registration(session, registration, cents, currency=currency).source_id


# ------------------------------------------------------- the window closes


def test_the_tick_closes_a_paid_registrations_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    registration_id = enroll(client, auth_headers)
    pay(registration_id)

    tick()

    registration = db_session().get(Registration, registration_id)
    assert registration is not None
    assert registration.settled
    assert registration.expires_at is None


def test_an_expired_registration_keeps_its_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    registration_id = enroll(client, auth_headers)
    window_passed(registration_id)
    assert tick().sent  # expired, and told so
    pay(registration_id)

    tick()

    registration = db_session().get(Registration, registration_id)
    assert registration is not None
    assert registration.state == RegistrationState.EXPIRED
    assert registration.expires_at is not None


# ------------------------------------------- losing the reading reopens it


def test_reversing_a_credit_after_the_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    registration_id = enroll(client, auth_headers)
    source_id = pay(registration_id)
    window_passed(registration_id)

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    ledger.reverse_for_source(
        session,
        tournament,
        CreditSource.BANK_TRANSACTION,
        source_id,
        by="test",
        reason="wrong fencer",
    )
    session.commit()
    mailer = tick()

    assert_owing_under_fresh_window(registration_id)
    assert mailer.sent == []


def test_revoking_a_waiver_after_the_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    registration_id = enroll(client, auth_headers)
    base = f"/api/tournaments/cup/registrations/{registration_id}/settled"
    assert client.post(f"{base}?settled=true&reason=host", headers=organizer).status_code == 200
    window_passed(registration_id)

    assert client.post(f"{base}?settled=false", headers=organizer).status_code == 200
    mailer = tick()

    assert_owing_under_fresh_window(registration_id)
    assert mailer.sent == []


def test_correcting_a_recorded_payment(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    registration_id = enroll(client, auth_headers)
    payment = {
        "registration_id": registration_id,
        "amount": "1000.00",
        "currency": "CZK",
        "received_on": "2026-08-01",
        "method": "cash",
    }
    recorded = client.post("/api/tournaments/cup/payments/manual", json=payment, headers=organizer)
    assert recorded.status_code == 201, recorded.text
    window_passed(registration_id)

    removed = client.delete(
        f"/api/tournaments/cup/payments/manual/{recorded.json()['id']}", headers=organizer
    )
    assert removed.status_code == 200, removed.text
    tick()
    assert_owing_under_fresh_window(registration_id)

    again = client.post("/api/tournaments/cup/payments/manual", json=payment, headers=organizer)
    assert again.status_code == 201, again.text
    registration = db_session().get(Registration, registration_id)
    assert registration is not None
    assert registration.settled


def test_tightening_the_tolerance_after_the_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    registration_id = enroll(client, auth_headers)
    pay(registration_id, cents=97_000)  # 3 % short, inside the default 5 %
    window_passed(registration_id)

    response = client.patch(
        "/api/tournaments/cup", json={"amount_tolerance_percent": 2}, headers=organizer
    )
    assert response.status_code == 200, response.text
    mailer = tick()

    assert_owing_under_fresh_window(registration_id)
    assert mailer.sent == []


def test_an_amendment_upward_still_reopens(client, auth_headers):
    """The path that already opened a fresh window now shares the rule."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    fencer = auth_headers(email="jan@example.com", name="jan")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]
    registration_id = db_session().scalar(select(Registration.id).where(Registration.vs == vs))
    assert registration_id is not None
    pay(registration_id)
    window_passed(registration_id)

    amended = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={"disciplines": ["LS", "SB"]},
        headers=fencer,
    )
    assert amended.status_code == 200, amended.text
    tick()

    assert_owing_under_fresh_window(registration_id)


# ------------------------------------------------------------------ EUR


def test_switching_eur_off_with_euro_payers_is_refused(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, eur=True)
    first = enroll(client, auth_headers, "a@example.com")
    second = enroll(client, auth_headers, "b@example.com")
    pay(first, currency=Currency.EUR, cents=4_000)
    pay(second, currency=Currency.EUR, cents=4_000)

    response = client.patch(
        "/api/tournaments/cup", json={"eur_payments_enabled": False}, headers=organizer
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "eur_credits_present: 2"
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    assert tournament.eur_payments_enabled
    for registration_id in (first, second):
        registration = session.get(Registration, registration_id)
        assert registration is not None
        assert registration.settled


def test_switching_eur_off_without_euro_money(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, eur=True)
    registration_id = enroll(client, auth_headers)
    pay(registration_id)

    response = client.patch(
        "/api/tournaments/cup", json={"eur_payments_enabled": False}, headers=organizer
    )

    assert response.status_code == 200, response.text
