"""A submission that mixes a full discipline with an open one.

Each discipline is placed against its own capacity (spec: registration,
"Capacity and substitutes"), so one registration can hold a seat it owes for
and a queue place it does not. That shape is what the rest of this module
exercises: the queue counted from the placement rather than the registration's
state, promotion of a registration that has already paid, and a lapsed window
demoting instead of expiring.
"""

import datetime
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import Registration, RegistrationState
from tests.conftest import enable_payments, publish

TOURNAMENT_DATE = "2026-12-05"
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


# The session override yields inside a `with`, so the session closes as soon as
# its generator is finalized — and every row read through it detaches with it.
# Tests here read a registration, make another request, then read more of it,
# so the generator is held rather than discarded.
_open_sessions: list = []


def db_session():
    generator = app.dependency_overrides[get_session]()
    _open_sessions.append(generator)
    return next(generator)


def registration_by_vs(vs):
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


def make_tournament(client, organizer, **params):
    """Two individual disciplines: OPEN with room for two, TIGHT with room for
    one, so a single earlier registration fills TIGHT and every later
    submission naming both mixes a full discipline with an open one."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": TOURNAMENT_DATE},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    payload = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "reminder_day": 5,
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
        "payment_mode": "immediate",
    }
    payload.update(params)
    response = client.patch("/api/tournaments/cup", json=payload, headers=organizer)
    assert response.status_code == 200, response.text
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 2, "fee": 1000},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": 1, "fee": 400},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def enroll(client, auth_headers, email, name, **body):
    fencer = auth_headers(email=email, name=name)
    payload = {"disciplines": ["LS"]}
    payload.update(body)
    response = client.post("/api/tournaments/cup/register", json=payload, headers=fencer)
    assert response.status_code == 201, response.text
    return fencer, response.json()


def fill_tight(client, auth_headers):
    """One registration that takes SB's single seat."""
    return enroll(client, auth_headers, "first@example.com", "First", disciplines=["SB"])


def mark_paid(vs):
    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == vs))
    row.state = RegistrationState.PAID
    row.amount_paid_cents = row.total_amount * 100
    row.paid_at = datetime.datetime.now(UTC)
    session.commit()
    return row


def availability(client, slug):
    rows = client.get("/api/tournaments/cup/availability").json()
    return next(row for row in rows if row["slug"] == slug)


def test_mixed_submission_seats_the_open_and_queues_the_full(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    fill_tight(client, auth_headers)

    _, mixed = enroll(
        client, auth_headers, "mixed@example.com", "Mixed", disciplines=["LS", "SB"]
    )

    entries = {e["slug"]: e for e in mixed["entries"]}
    assert entries["LS"]["is_substitute"] is False
    assert entries["SB"]["is_substitute"] is True
    # billed for the seat alone; the queued placement adds nothing
    assert mixed["total_amount"] == 1000
    assert mixed["expires_at"] is not None


def test_paid_registration_is_counted_in_the_queue_it_waits_in(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    fill_tight(client, auth_headers)
    _, mixed = enroll(
        client, auth_headers, "mixed@example.com", "Mixed", disciplines=["LS", "SB"]
    )
    mark_paid(mixed["vs"])

    assert availability(client, "SB")["queue_length"] == 1


def test_paid_fencer_keeps_position_ahead_of_a_later_reserved_one(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    fill_tight(client, auth_headers)
    mixed_fencer, mixed = enroll(
        client, auth_headers, "mixed@example.com", "Mixed", disciplines=["LS", "SB"]
    )
    mark_paid(mixed["vs"])
    later_fencer, _ = enroll(
        client, auth_headers, "later@example.com", "Later", disciplines=["SB"]
    )

    def position(headers):
        body = client.get("/api/tournaments/cup/my-registration", headers=headers).json()
        return next(e["queue_position"] for e in body["entries"] if e["slug"] == "SB")

    assert position(mixed_fencer) == 1
    assert position(later_fencer) == 2
    assert availability(client, "SB")["queue_length"] == 2


def admit(client, organizer, registration_id, slug):
    return client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/admit/{slug}",
        headers=organizer,
    )


def free_tight_seat(client, first_fencer):
    """Cancel the registration holding SB's only seat, so a queued placement
    can be promoted into it."""
    response = client.post(
        "/api/tournaments/cup/my-registration/cancel", headers=first_fencer
    )
    assert response.status_code == 200, response.text


def test_paid_registration_can_be_promoted_and_owes_only_the_difference(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_tournament(client, organizer)
    first, _ = fill_tight(client, auth_headers)
    _, mixed = enroll(
        client, auth_headers, "mixed@example.com", "Mixed", disciplines=["LS", "SB"]
    )
    paid = mark_paid(mixed["vs"])
    paid_id = paid.id
    assert paid.total_amount == 1000  # the seated LS alone
    free_tight_seat(client, first)

    response = admit(client, organizer, paid_id, "SB")
    assert response.status_code == 200, response.text

    promoted = registration_by_vs(mixed["vs"])
    assert promoted.state == RegistrationState.PAID  # not reverted to unpaid
    assert promoted.total_amount == 1400  # LS + the promoted SB
    assert promoted.outstanding_cents == 40000  # only SB's fee is now due
    assert promoted.expires_at is not None  # a fresh window opened
    assert [e.is_substitute for e in promoted.entries] == [False, False]

    notice = mailbox.sent[-1]
    body = notice.get_body(("plain",)).get_content()
    assert "Uvolnilo se místo" in notice["Subject"]
    assert "400" in body  # the difference, not the 1400 total
    assert "1 400" not in body and "1400" not in body


def test_promotion_of_a_cancelled_registration_is_still_refused(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    first, _ = fill_tight(client, auth_headers)
    queued_fencer, queued = enroll(
        client, auth_headers, "queued@example.com", "Queued", disciplines=["SB"]
    )
    row_id = registration_by_vs(queued["vs"]).id
    free_tight_seat(client, first)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=queued_fencer)

    response = admit(client, organizer, row_id, "SB")
    assert response.status_code == 409
    assert response.json()["detail"] == "registration_not_active"


def lapse_window(vs):
    """Push a registration's payment window into the past."""
    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == vs))
    row.expires_at = datetime.datetime.now(UTC) - timedelta(days=1)
    session.commit()


def run_expiries(client, organizer):
    return client.post("/api/tournaments/cup/payments/process", headers=organizer).json()


def test_mixed_registration_is_demoted_not_expired(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    fill_tight(client, auth_headers)
    _, mixed = enroll(
        client, auth_headers, "mixed@example.com", "Mixed", disciplines=["LS", "SB"]
    )
    lapse_window(mixed["vs"])

    result = run_expiries(client, organizer)
    assert result["expired"] == 0

    demoted = registration_by_vs(mixed["vs"])
    assert demoted.state == RegistrationState.RESERVED  # still exists
    assert all(e.is_substitute for e in demoted.entries)  # the seat is given up
    assert demoted.expires_at is None  # nothing is owed from the queue
    # the queue place it never owed for is kept, in its original order
    assert availability(client, "SB")["queue_length"] == 1
    assert availability(client, "LS")["taken"] == 0  # the seat is freed


def test_registration_with_no_queued_placement_still_expires(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, seated = enroll(client, auth_headers, "seated@example.com", "Seated", disciplines=["LS"])
    lapse_window(seated["vs"])

    result = run_expiries(client, organizer)
    assert result["expired"] == 1
    assert registration_by_vs(seated["vs"]).state == RegistrationState.EXPIRED
