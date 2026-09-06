"""Money the organizer took that Squire never saw (spec payments, "An organizer
may record a payment Squire never saw").

Cash at the desk, a transfer to another account, a card terminal. The amount is
credited exactly as an ingested transaction's amount is — same counter, same
tolerance, same deposit threshold, same mail — because the fencer's inbox
should not know which route their money took, and because a second settle path
would drift from the first (design add-manual-payment-entry D3).

The record itself is a `ManualPayment` and never a row in the bank
transactions: that list is the statement ledger.
"""

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    BankTransaction,
    ManualPayment,
    PaymentEvent,
    RefundState,
    Registration,
    RegistrationState,
)
from tests.conftest import enable_payments, publish, set_features
from tests.test_matching import age_reserved, import_rows

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


def make_tournament(client, organizer, *, payments=True, fee_eur=None, **params):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    if payments:
        enable_payments(client, organizer, "cup")
    else:
        set_features(client, organizer, "cup", feature_payments=False)
    payload = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
        "fio_token": "test-feed-token",
    }
    payload.update(params)
    assert client.patch("/api/tournaments/cup", json=payload, headers=organizer).status_code == 200
    discipline = {"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000}
    if fee_eur is not None:
        discipline["fee_eur"] = fee_eur
    client.post("/api/tournaments/cup/disciplines", json=discipline, headers=organizer)
    publish(client, organizer, "cup")


def enroll(client, auth_headers, email="jan@example.com", name="Jan"):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def registration_by_vs(vs) -> Registration:
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


def record(client, organizer, registration_id, **body):
    payload = {
        "registration_id": registration_id,
        "amount": "1000.00",
        "currency": "CZK",
        "received_on": "2026-08-01",
        "method": "cash",
    }
    payload.update(body)
    return client.post("/api/tournaments/cup/payments/manual", json=payload, headers=organizer)


def remove(client, organizer, payment_id):
    return client.delete(
        f"/api/tournaments/cup/payments/manual/{payment_id}", headers=organizer
    )


def listed(client, organizer):
    return client.get("/api/tournaments/cup/payments/manual", headers=organizer)


# ------------------------------------------------------------------ crediting


def test_cash_at_the_desk_settles_a_reservation(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    registration = registration_by_vs(vs)

    response = record(client, organizer, registration.id)
    assert response.status_code == 201, response.text

    row = registration_by_vs(vs)
    assert row.state == RegistrationState.PAID
    assert row.amount_paid_cents == 100000
    assert row.outstanding_cents == 0
    # the same mail a bank credit sends: the fencer's inbox does not learn
    # which route their money took (design D3)
    assert "Platba přijata" in mailbox.sent[-1]["Subject"]


def test_a_recorded_payment_can_be_partial(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)

    assert record(
        client, organizer, registration_by_vs(vs).id, amount="500.00"
    ).status_code == 201

    row = registration_by_vs(vs)
    assert row.state == RegistrationState.RESERVED
    assert row.amount_paid_cents == 50000
    assert row.outstanding_cents == 50000
    assert "Přijali jsme částečnou platbu" in mailbox.sent[-1]["Subject"]


def test_reaching_the_deposit_closes_the_window(client, auth_headers, mailbox):
    """The threshold is the machinery's, not the route's: a deposit reached in
    cash discharges the window exactly as one reached by transfer does."""
    organizer = auth_headers()
    make_tournament(client, organizer, payment_mode="deposit", deposit_amount=300)
    _, vs = enroll(client, auth_headers)
    assert registration_by_vs(vs).expires_at is not None

    assert record(
        client, organizer, registration_by_vs(vs).id, amount="300.00"
    ).status_code == 201

    row = registration_by_vs(vs)
    assert row.state == RegistrationState.RESERVED
    assert row.expires_at is None


def test_the_eur_lane_is_credited_alone(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, fee_eur=40, eur_payments_enabled=True, eur_rate="25.0")
    _, vs = enroll(client, auth_headers)

    assert record(
        client, organizer, registration_by_vs(vs).id, amount="40.00", currency="EUR"
    ).status_code == 201

    row = registration_by_vs(vs)
    # each lane is judged against its own total and the two are never summed
    assert row.amount_paid_eur_cents == 4000
    assert row.amount_paid_cents == 0
    assert row.state == RegistrationState.PAID


def test_a_currency_the_tournament_does_not_price_in_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)

    response = record(client, organizer, registration_by_vs(vs).id, currency="EUR")
    assert response.status_code == 409
    assert response.json()["detail"] == "currency_not_accepted"
    assert registration_by_vs(vs).amount_paid_eur_cents == 0


def test_it_is_not_a_bank_transaction(client, auth_headers, mailbox):
    """The statement ledger holds what statements carried, and nothing else
    (design D2)."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id)

    assert db_session().scalars(select(BankTransaction)).all() == []
    assert client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json() == []


def test_recording_is_audited_against_the_organizer(client, auth_headers, mailbox):
    organizer = auth_headers(email="org@example.com", name="Organizátor")
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id)

    events = db_session().scalars(
        select(PaymentEvent).where(PaymentEvent.kind == "manual_payment_recorded")
    ).all()
    assert len(events) == 1
    assert "org@example.com" in events[0].detail
    # no transaction behind it, and the event says so by carrying none
    assert events[0].transaction_id is None


# -------------------------------------------------------------------- removal


def test_removal_subtracts_exactly_what_was_credited(client, auth_headers, mailbox):
    """The load-bearing assertion. The registration's total is amended upward
    after the payment is recorded, so a reversal computed from today's balance
    would take back a different number — the mistake `unapply_payment_link`
    was built to avoid (design D2)."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    payment = record(client, organizer, registration_by_vs(vs).id).json()
    assert registration_by_vs(vs).state == RegistrationState.PAID

    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.total_amount = 1500
    session.commit()

    assert remove(client, organizer, payment["id"]).status_code == 200

    row = registration_by_vs(vs)
    assert row.amount_paid_cents == 0
    assert row.state == RegistrationState.RESERVED
    assert row.paid_at is None


def test_removal_is_a_soft_delete(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    payment = record(client, organizer, registration_by_vs(vs).id).json()
    remove(client, organizer, payment["id"])

    # gone from what is credited now, still on the record
    assert listed(client, organizer).json() == []
    stored = db_session().get(ManualPayment, payment["id"])
    assert stored is not None and stored.removed_at is not None
    assert remove(client, organizer, payment["id"]).status_code == 409


def test_a_registration_still_covered_stays_paid(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    registration_id = registration_by_vs(vs).id
    first = record(client, organizer, registration_id, amount="1000.00").json()
    record(client, organizer, registration_id, amount="1000.00")

    remove(client, organizer, first["id"])

    row = registration_by_vs(vs)
    assert row.amount_paid_cents == 100000
    assert row.state == RegistrationState.PAID


def test_removal_is_audited(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    payment = record(client, organizer, registration_by_vs(vs).id).json()
    remove(client, organizer, payment["id"])

    kinds = [
        event.kind
        for event in db_session().scalars(select(PaymentEvent)).all()
    ]
    assert "manual_payment_recorded" in kinds
    assert "manual_payment_removed" in kinds


# --------------------------------------------------------------- the listing


def test_the_listing_reads_as_the_console_needs_it(client, auth_headers, mailbox):
    organizer = auth_headers(email="org@example.com", name="Organizátor")
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(
        client,
        organizer,
        registration_by_vs(vs).id,
        amount="1000.00",
        method="transfer",
        note="na účet klubu",
    )

    [row] = listed(client, organizer).json()
    assert row["fencer_name"] == "Jan"
    assert row["amount"] == "1000.00"
    assert row["method"] == "transfer"
    assert row["note"] == "na účet klubu"
    assert "org@example.com" in row["recorded_by"]
    # removing it would stop the roster saying paid, and the console says so
    # before it is confirmed
    assert row["removal_unsettles"] is True


def test_a_partial_payments_removal_unsettles_nothing(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id, amount="500.00")

    [row] = listed(client, organizer).json()
    assert row["removal_unsettles"] is False


# ------------------------------------------------------------- the refusals


def test_refused_where_squire_handles_no_payments(client, auth_headers, mailbox):
    """Where Squire tracks no amounts, an amount means nothing it could keep
    (design D7)."""
    organizer = auth_headers()
    make_tournament(client, organizer, payments=False)
    _, vs = enroll(client, auth_headers)

    response = record(client, organizer, registration_by_vs(vs).id)
    assert response.status_code == 409
    assert registration_by_vs(vs).amount_paid_cents == 0
    assert listed(client, organizer).status_code == 409


def test_refused_without_console_access(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)

    outsider = auth_headers(email="nobody@example.com", name="Nobody")
    assert record(client, outsider, registration_by_vs(vs).id).status_code == 403
    assert listed(client, outsider).status_code == 403


def test_a_cancelled_registration_takes_no_payment(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    fencer, vs = enroll(client, auth_headers)
    registration_id = registration_by_vs(vs).id
    assert client.post(
        "/api/tournaments/cup/my-registration/cancel", headers=fencer
    ).status_code == 200

    response = record(client, organizer, registration_id)
    assert response.status_code == 409
    assert response.json()["detail"] == "registration_not_live"


def test_an_unknown_registration_is_not_found(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    assert record(client, organizer, 9999).status_code == 404


def test_a_zero_amount_is_not_a_payment(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    assert record(
        client, organizer, registration_by_vs(vs).id, amount="0.00"
    ).status_code == 422


# ------------------------------------------------- when a statement follows


def test_a_statement_landing_on_a_settled_registration_is_flagged(
    client, auth_headers, mailbox
):
    """No new machinery: the matcher already refuses to credit a transaction
    whose registration is not reserved, so the collision surfaces in the
    flagged queue rather than doubling the money (design D6)."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id)

    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])

    row = registration_by_vs(vs)
    # the money was not credited twice
    assert row.amount_paid_cents == 100000
    [transaction] = db_session().scalars(select(BankTransaction)).all()
    assert transaction.status == "flagged"
    assert transaction.status_reason == "registration_paid"


def test_the_flagged_row_names_the_recorded_payment(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id, method="cash")
    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])

    [flagged] = client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json()
    recorded = flagged["settled_by_recorded_payment"]
    assert recorded is not None
    assert recorded["amount"] == "1000.00"
    assert recorded["method"] == "cash"
    assert recorded["received_on"] == "2026-08-01"


def test_the_flagged_row_names_a_waiver(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    client.post(
        f"/api/tournaments/cup/registrations/{registration_by_vs(vs).id}"
        "/settled?settled=True&reason=volná účast",
        headers=organizer,
    )
    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])

    [flagged] = client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json()
    assert flagged["settled_by_hand_reason"] == "volná účast"
    assert flagged["settled_by_recorded_payment"] is None


def test_an_ordinary_conflict_makes_no_hand_settled_claim(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])
    import_rows(client, organizer, [f"2;02.08.2026;1000,00;CZK;{vs};;;;;"])

    rows = client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json()
    [flagged] = [row for row in rows if row["status"] == "flagged"]
    assert flagged["settled_by_hand_reason"] is None
    assert flagged["settled_by_recorded_payment"] is None


def test_a_partly_recorded_registration_overshoots_into_the_overpayment_flag(
    client, auth_headers, mailbox
):
    """The other door to the same queue. The registration is still reserved, so
    the bank row credits normally and the sum overshoots."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id, amount="500.00")

    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])

    row = registration_by_vs(vs)
    assert row.state == RegistrationState.PAID
    assert row.amount_paid_cents == 150000
    assert row.refund_state == RefundState.PENDING
    kinds = [
        event.kind for event in db_session().scalars(select(PaymentEvent)).all()
    ]
    assert "overpayment" in kinds


# --------------------------------------------- what the expired queue holds


def test_a_reservation_expiring_on_recorded_money_is_listed(client, auth_headers, mailbox):
    """The money is as real and the reservation is as expired; that a person
    entered it changes only who has to be found to give it back."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    record(client, organizer, registration_by_vs(vs).id, amount="600.00")
    age_reserved(vs, expires_in_hours=-1)
    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    [row] = client.get(
        "/api/tournaments/cup/payments/expired-holding", headers=organizer
    ).json()
    assert row["vs"] == vs
    assert row["credited_amount"] == "600.00"


def test_a_waived_registration_holds_no_money(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    client.post(
        f"/api/tournaments/cup/registrations/{registration_by_vs(vs).id}"
        "/settled?settled=True&reason=volná účast",
        headers=organizer,
    )

    row = registration_by_vs(vs)
    assert row.amount_paid_cents == 0
    # nothing was credited, so it can never reach the expired-holding queue
    assert client.get(
        "/api/tournaments/cup/payments/expired-holding", headers=organizer
    ).json() == []
