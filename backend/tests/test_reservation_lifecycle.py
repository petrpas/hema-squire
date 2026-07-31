"""fix-reservation-lifecycle: re-registration after expiry, the amendment
endpoint, grace reinstatement in matching, the organizer's flagged-transaction
actions, and the amount_paid_cents / outstanding_cents accounting they share.

Task 9.1: neither test_registration_gating.py nor test_registrations.py
asserted a blanket 409 for an expired registration specifically (only for a
still-RESERVED double registration, which stays a 409). There was nothing to
turn into positive coverage there; that coverage is added fresh here.
"""

import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import PaymentEvent, RefundState, Registration, RegistrationState, Tournament

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
    from app.bank import get_fio_client

    client = FakeFio()
    app.dependency_overrides[get_fio_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_fio_client, None)


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup_tournament(client, organizer, capacity=10, **patch):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    base = {
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
        "bank_account": IBAN,
        "fio_token": "test-token",
    }
    client.patch("/api/tournaments/cup", json=base | patch, headers=organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "LS", "capacity": capacity, "fee": 1000},
        headers=organizer,
    )


def register(client, headers, **overrides):
    payload = {"disciplines": ["LS"], **overrides}
    return client.post("/api/tournaments/cup/register", json=payload, headers=headers)


def amend(client, headers, **overrides):
    payload = {"disciplines": ["LS"], **overrides}
    return client.post(
        "/api/tournaments/cup/my-registration/amend", json=payload, headers=headers
    )


def registration_by_vs(vs) -> Registration:
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


def expire(vs, hours_ago=1):
    """Force a registration straight to EXPIRED, `hours_ago` past its window."""
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.state = RegistrationState.EXPIRED
    registration.expires_at = datetime.now(UTC) - timedelta(hours=hours_ago)
    session.commit()


def mark_paid(vs):
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.state = RegistrationState.PAID
    registration.paid_at = datetime.now(UTC)
    registration.amount_paid_cents = registration.total_amount * 100
    session.commit()


def event_kinds(vs):
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    return [
        e.kind
        for e in session.scalars(
            select(PaymentEvent)
            .where(PaymentEvent.registration_id == registration.id)
            .order_by(PaymentEvent.id)
        ).all()
    ]


def transfer(vs, amount_czk, external_id="9001", currency="CZK"):
    from app.bank import IncomingTransaction

    return IncomingTransaction(
        external_id=external_id,
        date=datetime(2026, 7, 15).date(),
        amount_cents=amount_czk * 100,
        currency=currency,
        vs=vs,
        message=f"VS {vs}",
        payer_name="Jan Novák",
        payer_account="123/0800",
    )


def unmatched_transaction(client, organizer):
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    (flagged,) = [t for t in queue if t["status"] == "flagged"]
    return flagged


# --- 9.2 Re-registration after expiry ---------------------------------------


def test_reregistration_after_expiry_with_seat_free(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    first = register(client, fencer).json()
    expire(first["vs"])

    # the blanket already_registered guard no longer blocks this
    second = register(client, fencer)
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["state"] == "reserved"
    assert body["vs"] != first["vs"]  # a fresh VS every cycle
    assert body["expires_at"] is not None
    assert body["entries"][0]["is_substitute"] is False


def test_reregistration_after_expiry_into_full_discipline_queues(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=1)
    fencer = auth_headers(email="f1@example.com", name="F1")
    first = register(client, fencer).json()
    expire(first["vs"])

    other = auth_headers(email="f2@example.com", name="F2")
    register(client, other)  # takes the only seat

    second = register(client, fencer, wait_for_all=True).json()
    assert second["entries"][0]["is_substitute"] is True


def test_repeated_expiry_not_penalized(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    first = register(client, fencer).json()
    expire(first["vs"])
    second = register(client, fencer).json()
    expire(second["vs"])
    third = register(client, fencer)
    assert third.status_code == 201


# --- 9.3 Reserved amendment --------------------------------------------------


def test_reserved_amendment_keeps_vs_and_window_and_recomputes_total(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Afterparty ticket", "category": "afterparty", "price": 300},
        headers=organizer,
    ).json()
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    mailbox.sent.clear()

    amended = amend(
        client, fencer, extras=[{"extra_item_id": item["id"], "qty": 1}]
    )
    assert amended.status_code == 200, amended.text
    body = amended.json()
    assert body["vs"] == initial["vs"]
    assert body["expires_at"] == initial["expires_at"]
    assert body["total_amount"] == initial["total_amount"] + 300
    assert body["state"] == "reserved"
    assert len(mailbox.sent) == 1  # amendment confirmation reissued


# --- 9.4 Paid amendment ------------------------------------------------------


def test_paid_amendment_upward_stays_paid_with_outstanding_and_surcharge_email(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Afterparty ticket", "category": "afterparty", "price": 300},
        headers=organizer,
    ).json()
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    mark_paid(initial["vs"])
    mailbox.sent.clear()

    amended = amend(client, fencer, extras=[{"extra_item_id": item["id"], "qty": 1}]).json()
    assert amended["state"] == "paid"
    assert amended["total_amount"] == 1300
    assert amended["outstanding_amount"] == "300.00"
    assert amended["refund_state"] == "not_applicable"
    assert len(mailbox.sent) == 1  # surcharge instructions, not a plain confirmation


def test_paid_amendment_downward_records_overpayment_pending_refund(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Afterparty ticket", "category": "afterparty", "price": 300},
        headers=organizer,
    ).json()
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(
        client, fencer, extras=[{"extra_item_id": item["id"], "qty": 1}]
    ).json()
    assert initial["total_amount"] == 1300
    mark_paid(initial["vs"])

    amended = amend(client, fencer, extras=[]).json()
    assert amended["state"] == "paid"
    assert amended["total_amount"] == 1000
    assert amended["outstanding_amount"] == "-300.00"
    assert amended["refund_state"] == "pending"


# --- 9.5 Amendment edge cases -------------------------------------------------


def test_amendment_adding_full_discipline_is_accepted_as_substitute(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"code": "SB", "capacity": 1, "fee": 500},
        headers=organizer,
    )
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer, disciplines=["LS"])
    other = auth_headers(email="f2@example.com", name="F2")
    register(client, other, disciplines=["SB"])  # fills SB

    amended = amend(client, fencer, disciplines=["LS", "SB"])
    assert amended.status_code == 200, amended.text
    entries = {e["code"]: e["is_substitute"] for e in amended.json()["entries"]}
    # the kept, still-open discipline is unaffected; only the full one queues
    assert entries == {"LS": False, "SB": True}


def test_amendment_refused_after_amendments_close(client, auth_headers):
    organizer = auth_headers()
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    setup_tournament(client, organizer, amendments_close=yesterday)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer)

    response = amend(client, fencer)
    assert response.status_code == 403


def test_amendment_refused_on_expired_registration(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"])

    response = amend(client, fencer)
    assert response.status_code == 409


def test_amendment_refused_on_cancelled_registration(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    response = amend(client, fencer)
    assert response.status_code == 404  # cancelled is invisible to get_my_registration


# --- 9.6 / 9.7 Grace reinstatement in matching --------------------------------


def test_payment_inside_grace_with_free_seat_reinstates_and_pays(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"], hours_ago=12)  # within the default 48h grace

    fio.transactions = [transfer(initial["vs"], 1000)]
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll == {"new": 1, "duplicate": 0, "matched": 1, "flagged": 0, "unmatched": 0}

    registration = client.get(
        "/api/tournaments/cup/my-registration", headers=fencer
    ).json()
    assert registration["state"] == "paid"
    assert "reinstated_in_grace" in event_kinds(initial["vs"])


def test_payment_inside_grace_with_seat_taken_stays_flagged_no_substitute_displaced(
    client, auth_headers, fio
):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=1)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"], hours_ago=12)

    other = auth_headers(email="f2@example.com", name="F2")
    other_reg = register(client, other).json()  # takes the freed seat

    fio.transactions = [transfer(initial["vs"], 1000)]
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll["flagged"] == 1 and poll["matched"] == 0

    assert (
        client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
        == "expired"
    )
    # the seat-holder is unaffected and not queued as a substitute
    other_now = client.get("/api/tournaments/cup/my-registration", headers=other).json()
    assert other_now["state"] == "reserved"
    assert other_now["entries"][0]["is_substitute"] is False
    assert unmatched_transaction(client, organizer)["status_reason"] == "expired_seat_taken"


def test_payment_outside_grace_stays_flagged_with_its_own_reason(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"], hours_ago=72)  # past the default 48h grace

    fio.transactions = [transfer(initial["vs"], 1000)]
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll["flagged"] == 1 and poll["matched"] == 0
    assert unmatched_transaction(client, organizer)["status_reason"] == "expired_outside_grace"
    assert (
        client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["state"]
        == "expired"
    )


# --- 9.8 Cancelled registration never reinstates ------------------------------


def test_payment_on_cancelled_registration_never_reinstates(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    fio.transactions = [transfer(initial["vs"], 1000)]
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll["flagged"] == 1 and poll["matched"] == 0
    assert registration_by_vs(initial["vs"]).state == RegistrationState.CANCELLED


# --- 9.9 Organizer actions on a flagged transaction ---------------------------


def test_organizer_reinstate_resolves_transaction_and_audits(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"], hours_ago=72)  # outside grace, so it stays flagged

    fio.transactions = [transfer(initial["vs"], 1000)]
    client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    flagged = unmatched_transaction(client, organizer)
    assert flagged["reinstate_available"] is True

    reinstated = client.post(
        f"/api/tournaments/cup/payments/transactions/{flagged['id']}/reinstate",
        headers=organizer,
    )
    assert reinstated.status_code == 200, reinstated.text
    assert reinstated.json()["status"] == "matched"

    registration = client.get(
        "/api/tournaments/cup/my-registration", headers=fencer
    ).json()
    assert registration["state"] == "paid"
    assert "reinstated_by_organizer" in event_kinds(initial["vs"])

    # no longer in the flagged queue
    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert flagged["id"] not in [t["id"] for t in queue]


def test_organizer_mark_for_refund_resolves_transaction_and_audits(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"], hours_ago=72)

    fio.transactions = [transfer(initial["vs"], 1000)]
    client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    flagged = unmatched_transaction(client, organizer)

    resolved = client.post(
        f"/api/tournaments/cup/payments/transactions/{flagged['id']}/mark-for-refund",
        headers=organizer,
    )
    assert resolved.status_code == 200, resolved.text

    registration = registration_by_vs(initial["vs"])
    assert registration.state == RegistrationState.EXPIRED  # unchanged, just resolved
    assert registration.refund_state == RefundState.PENDING
    assert "marked_for_refund" in event_kinds(initial["vs"])

    queue = client.get("/api/tournaments/cup/payments/unmatched", headers=organizer).json()
    assert flagged["id"] not in [t["id"] for t in queue]


def test_reinstate_offered_only_where_capacity_allows(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=1)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    expire(initial["vs"], hours_ago=72)
    other = auth_headers(email="f2@example.com", name="F2")
    register(client, other)  # takes the only seat

    fio.transactions = [transfer(initial["vs"], 1000)]
    client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    flagged = unmatched_transaction(client, organizer)
    assert flagged["reinstate_available"] is False

    refused = client.post(
        f"/api/tournaments/cup/payments/transactions/{flagged['id']}/reinstate",
        headers=organizer,
    )
    assert refused.status_code == 409


# --- 9.10 amount_paid_cents symmetry ------------------------------------------


def test_amount_paid_cents_credited_on_match_and_reverted_by_unapply(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()

    csv = (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
        "77;01.08.2026;1 000,00;CZK;;;;platba za registraci;Klubový účet;123\n"
    ).encode()
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(csv), "text/csv")},
        headers=organizer,
    )
    unmatched = client.get(
        "/api/tournaments/cup/payments/unmatched", headers=organizer
    ).json()
    transaction_id = unmatched[0]["id"]
    rule = client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": [initial["vs"]]},
        headers=organizer,
    ).json()
    assert registration_by_vs(initial["vs"]).amount_paid_cents == 100000

    client.delete(f"/api/tournaments/cup/rules/{rule['rule_id']}", headers=organizer)
    assert registration_by_vs(initial["vs"]).amount_paid_cents == 0


def test_foreign_currency_credit_unchanged_by_later_rate_edit(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(
        client, organizer, capacity=10,
        eur_payments_enabled=True, eur_rate="25.5",
    )
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    assert initial["total_amount"] == 1000

    fio.transactions = [transfer(initial["vs"], 40, currency="EUR")]  # 40 EUR ~ 1020 CZK
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll["matched"] == 1

    credited_before = registration_by_vs(initial["vs"]).amount_paid_cents
    assert credited_before == 40 * 25.5 * 100

    client.patch("/api/tournaments/cup", json={"eur_rate": "30"}, headers=organizer)
    assert registration_by_vs(initial["vs"]).amount_paid_cents == credited_before


# --- 9.11 Tournament parameter validation -------------------------------------


def test_amendments_close_after_registration_closes_rejected(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    response = client.patch(
        "/api/tournaments/cup",
        json={
            "registration_closes": "2026-11-01",
            "amendments_close": "2026-11-15",
        },
        headers=organizer,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "amendments_close_after_registration_closes"


def test_expiry_grace_hours_zero_disables_automatic_reinstatement(client, auth_headers, fio):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=10, expiry_grace_hours=0)
    fencer = auth_headers(email="f1@example.com", name="F1")
    initial = register(client, fencer).json()
    # 1 hour past expiry: well within the default 48h grace, but grace is 0 here
    expire(initial["vs"], hours_ago=1)

    fio.transactions = [transfer(initial["vs"], 1000)]
    poll = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer).json()
    assert poll["flagged"] == 1 and poll["matched"] == 0
    assert unmatched_transaction(client, organizer)["status_reason"] == "expired_outside_grace"
