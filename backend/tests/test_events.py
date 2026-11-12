"""Events without disciplines (spec discipline-less-events): what makes one, what
it may be registered for, and how a registration of items alone owes."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app import emails
from app import setup as setup_rules
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import Fencer, PaymentMode, Registration, RegistrationState, Tournament
from tests.conftest import enable_payments, pay_registration, post_restore, publish, set_features

URL = "/api/tournaments/cup"


def db_session():
    return next(app.dependency_overrides[get_session]())


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


def setup_event(client, organizer, *, price=500, mode=None):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2030-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    set_features(client, organizer, "cup", feature_extras=True, feature_payments=True)
    item = client.post(
        f"{URL}/extra-items",
        json={"name": "Seminar", "category": "seminar", "price": price},
        headers=organizer,
    ).json()
    if mode is not None:
        session = db_session()
        session.scalars(select(Tournament)).one().payment_mode = mode
        session.commit()
    return item


def add_discipline(client, organizer, slug="LS", **fields):
    response = client.post(
        f"{URL}/disciplines",
        json={"slug": slug, "weapon": slug, "capacity": 5, "fee": 1000, **fields},
        headers=organizer,
    )
    assert response.status_code == 201, response.text


def register(client, headers, item=None, disciplines=()):
    extras = [{"extra_item_id": item["id"], "qty": 1}] if item else []
    return client.post(
        f"{URL}/register",
        json={"disciplines": list(disciplines), "extras": extras},
        headers=headers,
    )


def stored(session, email="f@example.com") -> Registration:
    registration = session.scalar(select(Registration).join(Fencer).where(Fencer.email == email))
    assert registration is not None
    return registration


def test_a_record_is_an_event_until_it_has_a_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer)
    assert client.get(URL, headers=organizer).json()["is_event"] is True

    add_discipline(client, organizer, kind="team", team_min=2, team_max=3)

    assert client.get(URL, headers=organizer).json()["is_event"] is False


def test_an_event_publishes_with_no_disciplines(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer, price=0)
    client.patch(
        URL,
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )

    assert client.get(URL, headers=organizer).json()["setup_missing"] == []
    publish(client, organizer, "cup")

    assert client.get(URL, headers=organizer).json()["published_at"] is not None


def test_a_discipline_without_a_price_still_blocks(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer)
    add_discipline(client, organizer, fee=None)

    assert "discipline_prices" in client.get(URL, headers=organizer).json()["setup_missing"]


def test_a_published_tournament_may_lose_an_unreferenced_last_discipline(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer)
    add_discipline(client, organizer)
    publish(client, organizer, "cup")

    assert client.delete(f"{URL}/disciplines/LS", headers=organizer).status_code == 204

    assert client.get(URL, headers=organizer).json()["is_event"] is True


def test_a_referenced_last_discipline_cannot_be_removed(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer)
    add_discipline(client, organizer)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), disciplines=["LS"])

    assert client.delete(f"{URL}/disciplines/LS", headers=organizer).status_code == 409


def test_items_are_billed_owed_and_mailed_as_any_registration(client, auth_headers, mailbox):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")

    response = register(client, auth_headers(email="f@example.com", name="F"), item)

    assert response.status_code == 201, response.text
    session = db_session()
    registration = stored(session)
    assert registration.total_amount == 500
    assert registration.expires_at is not None
    assert not registration.fully_queued
    assert not registration.settled
    assert "QR" in mailbox.sent[-1].get_body(("plain",)).get_content()


def test_a_paid_mail_speaks_of_the_event(client, auth_headers, mailbox):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)
    session = db_session()
    registration = stored(session)
    emails.send_payment_received(
        mailbox, registration.tournament, registration.fencer, registration
    )

    body = mailbox.sent[-1].get_body(("plain",)).get_content()

    assert "tournament" not in body.lower().replace("cup", "")
    assert "turnaj" not in body.lower()


def test_nothing_selected_is_refused_on_an_event(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer)
    publish(client, organizer, "cup")

    response = register(client, auth_headers(email="f@example.com", name="F"))

    assert response.status_code == 422
    assert response.json()["detail"] == "nothing_selected"


def test_items_alone_are_refused_on_a_tournament(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    add_discipline(client, organizer)
    publish(client, organizer, "cup")

    response = register(client, auth_headers(email="f@example.com", name="F"), item)

    assert response.json()["detail"] == "nothing_selected"


def test_preview_matches_the_registration(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")

    preview = client.post(
        f"{URL}/price-preview", json={"extras": [{"extra_item_id": item["id"], "qty": 1}]}
    ).json()
    register(client, auth_headers(email="f@example.com", name="F"), item)

    session = db_session()
    assert preview["total"] == stored(session).total_amount == 500


def test_a_queued_registration_still_owes_nothing_for_its_items(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    add_discipline(client, organizer, capacity=1)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), disciplines=["LS"])

    register(client, auth_headers(email="g@example.com", name="G"), item, ["LS"])

    session = db_session()
    queued = stored(session, "g@example.com")
    assert queued.fully_queued
    assert queued.total_amount == 0


def test_a_stored_seat_mode_does_not_reach_items(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer, mode=PaymentMode.RESERVATION)
    publish(client, organizer, "cup")

    register(client, auth_headers(email="f@example.com", name="F"), item)

    session = db_session()
    registration = stored(session)
    assert registration.expires_at is not None
    assert setup_rules.owing_mode(registration.tournament, registration) is PaymentMode.IMMEDIATE
    assert registration.tournament.payment_mode is PaymentMode.RESERVATION


def test_deposit_items_are_not_asked_of_an_event(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer, mode=PaymentMode.DEPOSIT)

    missing = client.get(URL, headers=organizer).json()["setup_missing"]

    assert "deposit_amount" not in missing
    assert "payment_feed" not in missing


def test_an_unpaid_registration_expires_even_after_seating_has_settled(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)
    session = db_session()
    registration = stored(session)
    registration.expires_at = datetime.now(UTC) - timedelta(days=1)
    registration.tournament.seating_settled_at = datetime.now(UTC)
    session.commit()

    client.post(f"{URL}/payments/process", headers=organizer)

    session = db_session()
    assert stored(session).state == RegistrationState.EXPIRED


def test_a_discipline_added_later_leaves_an_items_registration_standing(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, item)
    session = db_session()
    window = stored(session).expires_at

    add_discipline(client, organizer)

    amended = client.post(
        f"{URL}/my-registration/amend",
        json={"disciplines": [], "extras": [{"extra_item_id": item["id"], "qty": 1}]},
        headers=fencer,
    )
    assert amended.status_code == 200, amended.text
    session = db_session()
    assert stored(session).total_amount == 500
    assert stored(session).expires_at == window


def test_hand_entry_and_import_refuse_an_event(client, auth_headers):
    organizer = auth_headers()
    setup_event(client, organizer)
    publish(client, organizer, "cup")

    entry = client.post(f"{URL}/manual-rows", json={"name": "Door Fencer"}, headers=organizer)
    upload = client.post(
        f"{URL}/import", files={"file": ("a.csv", b"name\nX\n", "text/csv")}, headers=organizer
    )

    assert entry.status_code == 422
    assert upload.status_code == 409


def test_items_only_money_reaches_the_exports(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)
    session = db_session()
    pay_registration(session, stored(session))
    session.commit()

    tabs = client.get(f"{URL}/export/tables", headers=organizer)
    summary = client.get(f"{URL}/export/summary", headers=organizer)
    revenue = client.get(f"{URL}/export/revenue", headers=organizer)

    assert tabs.status_code == 200, tabs.text
    assert summary.status_code == 200, summary.text
    assert "Seminar" in summary.text
    assert revenue.status_code == 200, revenue.text
    assert "Seminar" in revenue.text


def test_an_items_registration_round_trips_through_the_export(client, auth_headers):
    organizer = auth_headers()
    item = setup_event(client, organizer)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)

    document = client.get(f"{URL}/export/json", headers=organizer).json()
    document["tournament"].update(slug="cup-again", vs_year=2031, date="2031-12-05")
    document["registrations"][0]["vs"] = 3101001
    restored = post_restore(client, organizer, document)

    assert restored.status_code == 201, restored.text
    session = db_session()
    copies = session.scalars(select(Registration).order_by(Registration.id)).all()
    assert [copy.items_only for copy in copies] == [True, True]
    assert copies[1].total_amount == 500
