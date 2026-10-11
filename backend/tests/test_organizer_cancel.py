"""An organizer's cancellation, and deletion kept to rows holding no live
registration (spec registration, An organizer may cancel a registration; spec
etl-console, Reversible row deletion; spec imported-registrations, A cancelled
issued registration keeps its row out)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.importer import get_import_parser
from app.mail import get_mailer
from app.main import app
from app.models import (
    RefundState,
    Registration,
    RegistrationState,
    Rule,
    Tournament,
)
from tests.conftest import credit_registration, enable_payments, publish
from tests.test_issuing import RosterParser, import_roster, issue, row
from tests.test_matching import db_session


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


def setup(client, organizer, *, capacity=10):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": capacity, "fee": 1000},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"bank_account": "CZ6508000000192000145399", "refundable_until": "2026-12-01"},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def register(client, auth_headers, email, name):
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=auth_headers(email=email, name=name),
    )
    assert response.status_code == 201, response.text
    registration = db_session().scalar(
        select(Registration).where(Registration.vs == response.json()["vs"])
    )
    assert registration is not None
    return registration.id


def cancel(client, organizer, registration_id, note=None):
    return client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/cancel",
        json={} if note is None else {"note": note},
        headers=organizer,
    )


def registration(registration_id) -> Registration:
    found = db_session().get(Registration, registration_id)
    assert found is not None
    return found


def availability(client) -> dict:
    (longsword,) = [
        a for a in client.get("/api/tournaments/cup/availability").json() if a["slug"] == "LS"
    ]
    return longsword


def delete_row(client, organizer, target):
    return client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "fencers", "kind": "row_delete", "target": target, "payload": {}},
        headers=organizer,
    )


# ------------------------------------------------------------ what it does


def test_the_seat_is_freed_and_nobody_is_promoted(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer, capacity=1)
    seated = register(client, auth_headers, "a@example.com", "Adéla")
    queued = register(client, auth_headers, "b@example.com", "Boris")

    response = cancel(client, organizer, seated)

    assert response.status_code == 200, response.text
    assert registration(seated).state is RegistrationState.CANCELLED
    assert (availability(client)["taken"], availability(client)["free"]) == (0, 1)
    # the freed seat waits for the organizer's promotion
    assert all(entry.is_substitute for entry in registration(queued).entries)


def test_the_clocks_stop(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    reserved = register(client, auth_headers, "a@example.com", "Adéla")
    cancel(client, organizer, reserved)
    mailbox.sent.clear()
    session = db_session()
    held = session.get(Registration, reserved)
    assert held is not None
    held.registered_at = datetime.now(UTC) - timedelta(days=30)
    held.expires_at = datetime.now(UTC) - timedelta(days=20)
    session.commit()

    result = client.post("/api/tournaments/cup/payments/process", headers=organizer).json()

    assert (result["reminders"], result["expired"]) == (0, 0)
    assert mailbox.sent == []


def test_money_credited_is_marked_for_refund_as_the_fencers_own(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    paid = register(client, auth_headers, "a@example.com", "Adéla")
    session = db_session()
    held = session.get(Registration, paid)
    assert held is not None
    credit_registration(session, held, held.total_amount * 100)
    mailbox.sent.clear()

    cancel(client, organizer, paid)

    cancelled = registration(paid)
    assert cancelled.refund_state is RefundState.PENDING
    assert cancelled.refundable is True
    (message,) = mailbox.sent
    assert "vrácení" in message.get_body(("plain",)).get_content()


def test_the_fencer_is_told_with_the_note(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    reserved = register(client, auth_headers, "a@example.com", "Adéla")
    mailbox.sent.clear()

    cancel(client, organizer, reserved, note="duplicitní přihláška")

    (message,) = mailbox.sent
    assert message["To"] == "a@example.com"
    body = message.get_body(("plain",)).get_content()
    assert "Cup" in message["Subject"]
    assert "duplicitní přihláška" in body
    assert "vrácení" not in body


def test_a_hand_entered_seat_is_not_mailed(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    entered = client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Door Fencer", "email": "door@example.com", "disciplines": ["LS"]},
        headers=organizer,
    )
    assert entered.status_code == 201, entered.text
    registration_id = entered.json()["registration_id"]
    mailbox.sent.clear()

    response = cancel(client, organizer, registration_id)

    assert response.status_code == 200, response.text
    assert registration(registration_id).state is RegistrationState.CANCELLED
    assert mailbox.sent == []


def test_an_expired_registration_is_not_cancelled(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    lapsed = register(client, auth_headers, "a@example.com", "Adéla")
    session = db_session()
    held = session.get(Registration, lapsed)
    assert held is not None
    held.state = RegistrationState.EXPIRED
    session.commit()
    mailbox.sent.clear()

    response = cancel(client, organizer, lapsed)

    assert response.status_code == 409
    assert mailbox.sent == []


def test_a_fencer_cannot_cancel_somebody_else(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    reserved = register(client, auth_headers, "a@example.com", "Adéla")
    other = auth_headers(email="z@example.com", name="Z")

    response = client.post(
        f"/api/tournaments/cup/registrations/{reserved}/cancel", json={}, headers=other
    )

    assert response.status_code == 403
    assert registration(reserved).state is RegistrationState.RESERVED


# ------------------------------------------------------------ deletion


def test_a_live_registrations_row_cannot_be_deleted(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    reserved = register(client, auth_headers, "a@example.com", "Adéla")

    response = delete_row(client, organizer, f"reg:{reserved}")

    assert response.status_code == 409
    assert response.json()["detail"] == "row_has_registration"
    assert db_session().scalars(select(Rule)).all() == []


def test_an_expired_registrations_row_may_be_tidied(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    lapsed = register(client, auth_headers, "a@example.com", "Adéla")
    session = db_session()
    held = session.get(Registration, lapsed)
    assert held is not None
    held.state = RegistrationState.EXPIRED
    session.commit()

    assert delete_row(client, organizer, f"reg:{lapsed}").status_code == 201


def test_a_row_deleted_before_the_rule_is_restored_and_cancelled(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    reserved = register(client, auth_headers, "a@example.com", "Adéla")
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    session.add(
        Rule(
            tournament_id=tournament.id,
            phase="fencers",
            kind="row_delete",
            target=f"reg:{reserved}",
            payload={},
            created_by=1,
        )
    )
    session.commit()

    restored = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": "row_restore",
            "target": f"reg:{reserved}",
            "payload": {},
        },
        headers=organizer,
    )

    assert restored.status_code == 201, restored.text
    assert cancel(client, organizer, reserved).status_code == 200


# ------------------------------------------------------------ manual mode


def test_a_cancelled_issued_registration_is_not_reissued(client, auth_headers, mailbox):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "city": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
            "external_registration_url": "https://example.com/form",
        },
        headers=organizer,
    )
    # the mode is settled before publication, where it freezes
    response = client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "organizer"},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    publish(client, organizer, "cup")
    app.dependency_overrides[get_import_parser] = lambda: RosterParser()
    # the second fencer gave no address: a new fencer record every time, which
    # is how a reissue would go unnoticed
    import_roster(client, organizer, [row("Jan", "jan@example.com"), row("Eva", "")])
    assert issue(client, organizer)["issued"] == 2
    eva = db_session().scalar(
        select(Registration)
        .where(Registration.source_row_id.is_not(None))
        .order_by(Registration.id.desc())
    )
    assert eva is not None
    row_id = eva.source_row_id

    assert cancel(client, organizer, eva.id).status_code == 200

    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    assert row_id not in [r["id"] for r in sheet]
    assert issue(client, organizer)["issued"] == 0
    live = (
        db_session()
        .scalars(select(Registration).where(Registration.state == RegistrationState.RESERVED))
        .all()
    )
    assert len(live) == 1
