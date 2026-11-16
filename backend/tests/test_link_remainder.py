"""A payment link accounts for the whole transaction (`openspec/payments_gaps.md`, P4).

A link distributes a transaction across the registrations it names, each up
to what it owes. What is left after that went nowhere: the transaction read as
matched, and the remainder stood in no journal and no queue. And a link none of
whose registrations could take money credited nothing at all while still
marking the transaction matched."""

import io

import pytest
from sqlalchemy import func, select

from app.models import PaymentCredit, Registration
from tests.test_manual_matching import (
    db_session,
    enroll,
    mailbox,  # noqa: F401  # a fixture, used through usefixtures below
    setup,
    unmatched_transaction_id,
)

# the links send confirmations; the fixture keeps them off the real mailer
pytestmark = pytest.mark.usefixtures("mailbox")

HEADER = (
    "meta;data\n\n"
    "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet\n"
)


def import_amount(client, organizer, amount: str, row_id: int = 77) -> int:
    csv = (HEADER + f"{row_id};01.08.2026;{amount};CZK;;;;platba;Klubový účet;123\n").encode()
    response = client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(csv), "text/csv")},
        headers=organizer,
    )
    assert response.status_code == 202, response.text
    return unmatched_transaction_id(client, organizer)


def link(client, organizer, transaction_id: int, vs: list[str]):
    return client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction_id, "vs": vs},
        headers=organizer,
    )


def credited_total(transaction_id: int) -> int:
    return db_session().scalar(
        select(func.coalesce(func.sum(PaymentCredit.amount_cents), 0)).where(
            PaymentCredit.source_id == transaction_id,
            PaymentCredit.reversed_at.is_(None),
        )
    )


def registration(vs: str) -> tuple[int, bool, str]:
    """What a registration was credited, whether it reads as paid, and its
    refund state — read while its session is still open."""
    found = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert found is not None
    return found.credited_in("local"), found.settled, found.refund_state


def test_the_remainder_goes_to_the_last_registration(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    _, vs_b = enroll(client, auth_headers, "b@example.com", "Boris")
    transaction_id = import_amount(client, organizer, "2 600,00")

    assert link(client, organizer, transaction_id, [vs_a, vs_b]).status_code == 201

    assert credited_total(transaction_id) == 260_000
    assert registration(vs_a) == (100_000, True, "not_applicable")
    assert registration(vs_b) == (160_000, True, "pending")


def test_a_single_registration_link_keeps_the_overpayment(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    transaction_id = import_amount(client, organizer, "1 200,00")

    assert link(client, organizer, transaction_id, [vs_a]).status_code == 201

    assert credited_total(transaction_id) == 120_000
    assert registration(vs_a)[2] == "pending"


def test_a_link_to_nothing_payable_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs_a = enroll(client, auth_headers, "a@example.com", "Adéla")
    paying = import_amount(client, organizer, "1 000,00", row_id=76)
    assert link(client, organizer, paying, [vs_a]).status_code == 201
    stray = import_amount(client, organizer, "1 000,00", row_id=77)

    response = link(client, organizer, stray, [vs_a])

    assert response.status_code == 409
    assert response.json()["detail"] == "nothing_payable"
    assert credited_total(stray) == 0
    queue = client.get("/api/tournaments/cup/payments/uncredited", headers=organizer).json()
    assert [row["id"] for row in queue] == [stray]
