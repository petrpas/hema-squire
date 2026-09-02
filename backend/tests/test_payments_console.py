"""What the payments console reads: the expired-holding queue and the
outstanding balance on the fencer table.

The expired-holding money sits in neither transaction queue — the payment
matched and was credited — so until this endpoint nothing in the console could
see it.
"""

import contextlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.mail import get_mailer
from app.main import app
from tests.test_matching import age_reserved, enroll, import_rows, setup


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


def expired_holding(client, headers, slug="cup"):
    return client.get(f"/api/tournaments/{slug}/payments/expired-holding", headers=headers)


def expire_holding_payment(client, organizer, vs, paid="600,00"):
    """Part-pay a reservation, then run the lifecycle past its window."""
    import_rows(client, organizer, [f"1;01.08.2026;{paid};CZK;{vs};;;;;"])
    age_reserved(vs, expires_in_hours=-1)
    client.post("/api/tournaments/cup/payments/process", headers=organizer)


def test_reservation_expired_holding_a_payment_is_listed(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    expire_holding_payment(client, organizer, vs)

    response = expired_holding(client, organizer)
    assert response.status_code == 200
    [row] = response.json()
    assert row["vs"] == vs
    assert row["fencer_name"] == "Jan"
    assert row["credited_amount"] == "600.00"
    # no EUR credit was taken, so the sibling is absent rather than zero
    assert row["credited_eur_amount"] is None
    assert row["expired_at"] is not None


def test_ordinary_expiry_is_not_listed(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    # never paid anything: the scheduler writes reservation_expired, not the
    # holding-payment event
    age_reserved(vs, expires_in_hours=-1)
    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    assert expired_holding(client, organizer).json() == []


def test_reinstated_reservation_drops_off_the_queue(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)
    expire_holding_payment(client, organizer, vs)
    assert len(expired_holding(client, organizer).json()) == 1

    # settling the rest reinstates it; the event stays in the log, but the
    # queue is a work list that empties
    import_rows(client, organizer, [f"2;02.08.2026;400,00;CZK;{vs};;;;;"])
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] != "expired"

    assert expired_holding(client, organizer).json() == []


def test_non_organizer_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    expire_holding_payment(client, organizer, vs)

    outsider = auth_headers(email="nosy@example.com", name="Nosy")
    assert expired_holding(client, outsider).status_code == 403


def sheet_row(client, headers, vs, slug="cup"):
    rows = client.get(f"/api/tournaments/{slug}/sheet", headers=headers).json()["rows"]
    return next(row for row in rows if row["vs"] == vs)


def test_part_paid_registration_carries_its_remaining_balance(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])

    row = sheet_row(client, organizer, vs)
    assert row["total_amount"] == 1000
    assert row["outstanding_amount"] == "400.00"
    # the tournament prices in no EUR, so the sibling says so rather than lying
    # with a zero
    assert row["outstanding_eur_amount"] is None


def test_settled_registration_reads_zero(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])

    assert sheet_row(client, organizer, vs)["outstanding_amount"] == "0.00"


def test_balance_is_recomputed_on_rerun_not_stored(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])
    assert sheet_row(client, organizer, vs)["outstanding_amount"] == "400.00"

    # no rule maintains the column: crediting the rest moves it on the next read
    import_rows(client, organizer, [f"2;02.08.2026;400,00;CZK;{vs};;;;;"])
    assert sheet_row(client, organizer, vs)["outstanding_amount"] == "0.00"


def test_credited_money_survives_a_json_round_trip(client, auth_headers, mailbox):
    """A restore reconstructed totals but not credit until v11, so every
    registration came back reading as if nothing had been paid against it while
    its state still said paid. The outstanding column is the first thing that
    looks at the credited counters, and so the first to catch it."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])
    assert sheet_row(client, organizer, vs)["outstanding_amount"] == "400.00"

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    registration = document["registrations"][0]
    assert registration["amount_paid_cents"] == 60000
    assert registration["amount_paid_eur_cents"] == 0


@contextlib.contextmanager
def fresh_deployment():
    """The same app against an empty database, so a document can be restored
    without colliding with the tournament it was exported from."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    previous = app.dependency_overrides[get_session]

    def session():
        with Session(engine) as active:
            yield active

    app.dependency_overrides[get_session] = session
    try:
        yield
    finally:
        app.dependency_overrides[get_session] = previous


def test_restoring_a_pre_v11_document_reads_as_uncredited(client, auth_headers, mailbox):
    """A document written before the counters were carried recorded no credit;
    it restores as zero, which is the reading those deployments already had —
    not a KeyError."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_rows(client, organizer, [f"1;01.08.2026;600,00;CZK;{vs};;;;;"])

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document["schema_version"] = 10
    for registration in document["registrations"]:
        registration.pop("amount_paid_cents")
        registration.pop("amount_paid_eur_cents")

    # a registration's VS is unique across the deployment, so the restore goes
    # into an empty one, as the export round-trip test does
    with fresh_deployment():
        new_organizer = auth_headers()
        restore = client.post("/api/tournaments/restore", json=document, headers=new_organizer)
        assert restore.status_code == 201, restore.text
        assert sheet_row(client, new_organizer, vs)["outstanding_amount"] == "1000.00"
