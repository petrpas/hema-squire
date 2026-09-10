"""The credit journal and the waiver journal (spec payment-ledger).

What a registration has been credited is the sum of its live credits, whether
it is settled is derived from that sum and from the waivers beside it, and both
are readable in Python and in SQL. Nothing here asserts against a stored
figure, because after `derive-balances-from-credits` there is none.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app import ledger
from app.db import get_session
from app.main import app
from app.models import (
    CreditOrigin,
    CreditSource,
    Currency,
    PaymentCredit,
    Registration,
    RegistrationState,
    Rule,
)
from tests.conftest import (
    credit_registration,
    enable_payments,
    paid_at_of,
    publish,
    set_fio_token,
    waive_registration,
)

IBAN = "CZ6508000000192000145399"


def db_session():
    return next(app.dependency_overrides[get_session]())


def make_tournament(client, organizer, *, fee=1000, tolerance=None, capacity=10):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    payload = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
    }
    if tolerance is not None:
        payload["amount_tolerance_percent"] = tolerance
    assert client.patch("/api/tournaments/cup", json=payload, headers=organizer).status_code == 200
    set_fio_token(client, organizer, "cup", "test-feed-token")
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": capacity, "fee": fee},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def enroll(client, auth_headers, email="jan@example.com", name="Jan"):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def registration_by_vs(session, vs) -> Registration:
    """Fetched from the caller's own session, deliberately.

    Every derived figure reads the registration's `credits` relationship, so a
    registration loaded in one session and credited through another sees
    neither the credit nor the balance that follows from it."""
    return session.scalar(select(Registration).where(Registration.vs == vs))


@pytest.fixture
def reserved(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    return organizer, vs


# ---------------------------------------------------- appending is idempotent


def test_a_second_credit_from_one_source_writes_nothing(reserved):
    """Task 2.5, spec: appending a credit is idempotent on its source."""
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    first = credit_registration(session, registration, 40000, source_id=4242)
    second = credit_registration(session, registration, 40000, source_id=4242)

    assert second.id == first.id
    assert registration.credited_in("local") == 40000
    assert session.scalars(select(PaymentCredit)).all() == [first]


def test_one_source_may_credit_two_registrations(client, auth_headers):
    """A transaction covering two fencers is two credits, not a repeat."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, first_vs = enroll(client, auth_headers)
    _, second_vs = enroll(client, auth_headers, email="eva@example.com", name="Eva")
    session = db_session()

    credit_registration(session, registration_by_vs(session, first_vs), 100000, source_id=77)
    credit_registration(session, registration_by_vs(session, second_vs), 100000, source_id=77)

    assert registration_by_vs(session, first_vs).credited_in("local") == 100000
    assert registration_by_vs(session, second_vs).credited_in("local") == 100000


def test_a_reversed_credit_frees_the_source_to_be_credited_again(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    first = credit_registration(session, registration, 100000, source_id=99)
    ledger.reverse(session, first, by="org <o@e>", reason="wrong")
    session.commit()

    again = credit_registration(session, registration, 100000, source_id=99)

    assert again.id != first.id
    assert registration.credited_in("local") == 100000


# ------------------------------------------------------------------- reversal


def test_reversing_releases_exactly_the_entrys_own_amount(reserved):
    """Not a figure computed against today's balance — the mistake the payment
    links and `ManualPayment` were both built to avoid."""
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    entry = credit_registration(session, registration, 100000)
    registration.total_amount = 2000  # amended upward after the credit
    session.commit()

    ledger.reverse(session, entry, by="org <o@e>", reason="withdrawn")
    session.commit()

    assert registration.credited_in("local") == 0
    assert registration.outstanding_cents == 200000


def test_reversing_twice_leaves_the_first_reversal_standing(reserved):
    _, vs = reserved
    session = db_session()
    entry = credit_registration(session, registration_by_vs(session, vs), 100000)
    ledger.reverse(session, entry, by="first <f@e>", reason="one")
    first_moment = entry.reversed_at

    ledger.reverse(session, entry, by="second <s@e>", reason="two")

    assert entry.reversed_at == first_moment
    assert entry.reversed_by == "first <f@e>"
    assert entry.reversed_reason == "one"


def test_a_reversed_credit_stays_readable(reserved):
    _, vs = reserved
    session = db_session()
    entry = credit_registration(session, registration_by_vs(session, vs), 100000)
    ledger.reverse(session, entry, by="org <o@e>", reason="withdrawn")
    session.commit()

    assert entry.amount_cents == 100000
    assert entry.source_kind is CreditSource.BANK_TRANSACTION
    assert entry.reversed_by == "org <o@e>"
    assert all(credit.amount_cents > 0 for credit in session.scalars(select(PaymentCredit)))


# ----------------------------------------------------------- settled, derived


def test_crediting_settles_without_anything_being_assigned(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    assert not registration.settled

    credit_registration(session, registration, 100000)

    assert registration.settled
    assert registration.state is RegistrationState.RESERVED
    assert registration.wire_state == "paid"


def test_a_reversal_unsettles_by_derivation(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    entry = credit_registration(session, registration, 100000)
    assert registration.settled

    ledger.reverse(session, entry, by="org <o@e>", reason="withdrawn")
    session.commit()

    assert not registration.settled
    assert registration.wire_state == "reserved"


def test_the_lifecycle_wins_over_the_money(reserved):
    """An expired registration credited in full reads expired, which is why the
    expired-holding queue exists."""
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    registration.state = RegistrationState.EXPIRED
    session.commit()
    credit_registration(session, registration, 100000)

    assert registration.settled
    assert registration.wire_state == "expired"


def test_a_waiver_settles_with_no_money(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)

    waive_registration(session, registration, reason="volná účast")

    assert registration.settled
    assert registration.waived
    assert registration.waiver_reason == "volná účast"
    assert registration.credited_in("local") == 0
    assert registration.balance_cents(registration.tournament)[0] == 0


def test_an_earlier_waiver_reason_survives_a_later_one(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)

    waive_registration(session, registration, reason="první")
    ledger.revoke_waiver(session, registration, revoked_by="org <o@e>")
    session.commit()
    assert not registration.settled

    waive_registration(session, registration, reason="druhý")

    assert registration.waiver_reason == "druhý"
    assert [waiver.reason for waiver in registration.waivers] == ["první", "druhý"]


# ------------------------------------------- owing nothing is not having paid


def test_a_fully_queued_registration_is_not_paid(client, auth_headers):
    """The case a naive derivation gets wrong. `pricing` does not price a
    queued placement, so such a registration's total is zero and its
    outstanding and tolerance are both zero — and it must still read reserved
    (design D5)."""
    organizer = auth_headers()
    make_tournament(client, organizer, capacity=1)
    enroll(client, auth_headers)
    _, queued_vs = enroll(client, auth_headers, email="eva@example.com", name="Eva")
    session = db_session()

    queued = registration_by_vs(session, queued_vs)

    assert queued.fully_queued
    assert queued.total_amount == 0
    assert queued.outstanding_cents == 0
    assert not queued.settled
    assert queued.wire_state == "reserved"


def test_a_tournament_that_charges_nothing_leaves_registrations_reserved(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, fee=0)
    _, vs = enroll(client, auth_headers)
    session = db_session()

    registration = registration_by_vs(session, vs)

    assert registration.total_amount == 0
    assert not registration.settled
    assert registration.wire_state == "reserved"


def test_an_amendment_down_to_nothing_keeps_the_payment(reserved):
    """The reason the test is `credited > 0` and not `total > 0`."""
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    credit_registration(session, registration, 100000)

    registration.total_amount = 0
    session.commit()

    assert registration.settled
    assert registration.outstanding_cents == -100000


# ------------------------------------------------------ Python and SQL agree


@pytest.mark.parametrize(
    ("credit_amount", "expected"),
    [(0, False), (50000, False), (100000, True)],
)
def test_the_settled_derivation_answers_the_same_in_sql(reserved, credit_amount, expected):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    if credit_amount:
        credit_registration(session, registration, credit_amount)

    in_sql = session.scalar(
        select(Registration.id).where(Registration.id == registration.id, Registration.settled)
    )

    assert registration.settled is expected
    assert (in_sql is not None) is expected


def test_a_waived_registration_is_settled_in_sql_too(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    waive_registration(session, registration)

    found = session.scalars(select(Registration.id).where(Registration.waived)).all()

    assert found == [registration.id]


def test_the_credited_sums_answer_the_same_in_sql(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    credit_registration(session, registration, 60000)
    credit_registration(session, registration, 25000)

    in_sql = session.scalar(
        select(Registration.credited_local_cents).where(Registration.id == registration.id)
    )

    assert registration.credited_in("local") == 85000
    assert in_sql == 85000


def test_a_reversed_credit_counts_in_neither(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    entry = credit_registration(session, registration, 60000)
    credit_registration(session, registration, 25000)
    ledger.reverse(session, entry, by="org <o@e>", reason="withdrawn")
    session.commit()

    in_sql = session.scalar(
        select(Registration.credited_local_cents).where(Registration.id == registration.id)
    )

    assert registration.credited_in("local") == 25000
    assert in_sql == 25000


# ------------------------------------------------------------- the paid date


def test_the_paid_date_is_the_credit_that_completed_the_balance(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    credit_registration(session, registration, 60000, value_date=date(2026, 8, 1))
    credit_registration(session, registration, 40000, value_date=date(2026, 8, 3))

    settled_on = paid_at_of(registration)

    assert settled_on is not None
    assert settled_on.astimezone(UTC).date() in (date(2026, 8, 2), date(2026, 8, 3))


def test_a_later_credit_does_not_move_the_paid_date(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    credit_registration(session, registration, 100000, value_date=date(2026, 8, 3))
    before = paid_at_of(registration)

    credit_registration(session, registration, 5000, value_date=date(2026, 8, 10))

    assert paid_at_of(registration) == before


def test_an_unsettled_registration_has_no_paid_date(reserved):
    _, vs = reserved
    session = db_session()
    credit_registration(session, registration_by_vs(session, vs), 50000)

    assert paid_at_of(registration_by_vs(session, vs)) is None


def test_a_waiver_dates_itself(reserved):
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    waiver = waive_registration(session, registration)

    settled_on = paid_at_of(registration)

    assert settled_on is not None
    assert settled_on == waiver.created_at


# ------------------------------------------------ one transaction, reversed


def test_reversing_a_credited_transaction_unsettles_and_requeues(client, auth_headers):
    """Spec payment-ledger, One credit entry may be reversed on its own — the
    operation that was missing, and the reason a clear was the only way out."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, vs = enroll(client, auth_headers)
    session = db_session()
    registration = registration_by_vs(session, vs)
    transaction_id = 31337
    ledger.credit(
        session,
        registration.tournament,
        registration,
        amount_cents=100000,
        currency=Currency.CZK,
        value_date=date(2026, 8, 1),
        source_kind=CreditSource.BANK_TRANSACTION,
        source_id=transaction_id,
        origin=CreditOrigin.AUTO_VS,
    )
    session.commit()
    assert registration.settled

    reversed_entries = ledger.reverse_for_source(
        session,
        registration.tournament,
        CreditSource.BANK_TRANSACTION,
        transaction_id,
        by="org <o@e>",
        reason="credit reversed by organizer",
    )
    session.commit()

    assert len(reversed_entries) == 1
    assert not registration.settled


def test_reversing_a_source_reaches_every_registration_it_covered(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, first_vs = enroll(client, auth_headers)
    _, second_vs = enroll(client, auth_headers, email="eva@example.com", name="Eva")
    session = db_session()
    for who in (first_vs, second_vs):
        credit_registration(session, registration_by_vs(session, who), 100000, source_id=555)

    ledger.reverse_for_source(
        session,
        registration_by_vs(session, first_vs).tournament,
        CreditSource.BANK_TRANSACTION,
        555,
        by="org <o@e>",
        reason="reversed",
    )
    session.commit()

    assert not registration_by_vs(session, first_vs).settled
    assert not registration_by_vs(session, second_vs).settled


def test_reversing_a_rule_is_unconditional(reserved):
    """The branch the counter version got wrong: a registration that expired
    after the link was applied still had its credit reversed here, where before
    the amount stayed behind with the rule that explained it deleted."""
    _, vs = reserved
    session = db_session()
    registration = registration_by_vs(session, vs)
    entry = credit_registration(session, registration, 100000)
    rule = Rule(
        tournament_id=registration.tournament_id,
        phase="payments",
        kind="payment_link",
        target="txn:whatever",
        payload={"vs": [registration.vs]},
        created_by=registration.fencer_id,
    )
    session.add(rule)
    session.flush()
    entry.rule_id = rule.id
    # the branch the counter version got wrong: expired since the link applied
    registration.state = RegistrationState.EXPIRED
    session.commit()

    ledger.reverse_for_rule(session, rule.id, by="org <o@e>", reason="withdrawn")
    session.commit()

    assert registration.credited_in("local") == 0


def test_the_journal_records_when_and_who(reserved):
    _, vs = reserved
    session = db_session()
    entry = credit_registration(session, registration_by_vs(session, vs), 100000)

    before = datetime.now(UTC)
    ledger.reverse(session, entry, by="org <o@e>", reason="withdrawn")
    session.commit()

    assert entry.reversed_at is not None
    assert entry.reversed_at.replace(tzinfo=UTC) >= before.replace(microsecond=0)
    assert entry.reversed_by == "org <o@e>"
