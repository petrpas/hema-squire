"""Paying substitutes take free places (spec seating-queue, A paying substitute
takes free places; payments; tournament-admin): off by default; on, a registration
waiting wholly in the queue has a claim, is told it, and a payment of it seats
everything it waits for or nothing — at once where the places are free, or on a
later pass as they free, the earliest payment first."""

import pytest
from sqlalchemy import select

from app.mail import get_mailer
from app.main import app
from app.models import BankTransaction, PaymentEvent, Registration, Tournament
from tests.conftest import credit_registration, import_statement
from tests.test_demotion import CollectingMailer, db_session, make_cup, settle


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def cup(client, organizer, capacities, *, seats=True, **params):
    make_cup(client, organizer, capacities=capacities, **params)
    if seats:
        response = client.patch(
            "/api/tournaments/cup", json={"queue_payment_seats": True}, headers=organizer
        )
        assert response.status_code == 200, response.text
        assert response.json()["queue_payment_seats"] is True


def register(client, auth_headers, name, disciplines=("LS",), condition=()):
    fencer = auth_headers(email=f"{name.lower()}@example.com", name=name)
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines), "condition": list(condition)},
        headers=fencer,
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def registration(vs) -> Registration:
    found = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert found is not None
    return found


def seated(vs) -> dict[str, bool]:
    return {e.discipline.slug: not e.is_substitute for e in registration(vs).entries}


_row = iter(range(1000, 100000))


def pay(client, organizer, vs, amount="1 000,00"):
    header = "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    row = f"{next(_row)};14.07.2026;{amount};CZK;{vs};;;;Payer;123/0800"
    return import_statement(
        client, organizer, ("meta;data\n\n" + header + "\n" + row + "\n").encode()
    )


def transactions_of(vs) -> list[BankTransaction]:
    return [
        t
        for t in db_session().scalars(select(BankTransaction).order_by(BankTransaction.id))
        if t.vs == vs
    ]


def instructions(client, fencer):
    return client.get("/api/tournaments/cup/my-registration/payment", headers=fencer)


def test_off_by_default_and_a_waiting_registration_owes_nothing(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1}, seats=False)
    register(client, auth_headers, "Holder")
    fencer, vs = register(client, auth_headers, "Waiting")

    tournament = db_session().scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament.queue_payment_seats is False
    assert registration(vs).claim_total is None
    response = instructions(client, fencer)
    assert response.status_code == 409
    assert response.json()["detail"] == "no_payment_due"


def test_a_waiting_registration_is_told_its_claim(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1, "SA": 1})
    register(client, auth_headers, "Holder", ["LS"])
    mailbox.sent.clear()
    fencer, vs = register(client, auth_headers, "Waiting", ["LS", "SA"], ["LS", "SA"])

    assert registration(vs).claim_total == 2000
    body = instructions(client, fencer).json()
    assert body["claim"] is True
    assert body["amount"] == 2000
    assert body["expires_at"] is None
    (confirmation,) = mailbox.sent
    text = confirmation.get_body(("plain",)).get_content()
    assert "můžeš zaplatit 2000 Kč" in text
    assert "volná ve všech disciplínách" in text


def test_a_forfeited_deposit_counts_toward_the_claim(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1}, mode="deposit", deposit_amount=500)
    fencer, vs = register(client, auth_headers, "Deposit")
    session = db_session()
    credit_registration(
        session, session.scalar(select(Registration).where(Registration.vs == vs)), 50000
    )
    mailbox.sent.clear()

    settle(client, organizer)

    assert registration(vs).claim_total == 1000
    assert instructions(client, fencer).json()["amount"] == 500
    (notice,) = mailbox.sent
    text = notice.get_body(("plain",)).get_content()
    assert "můžeš zaplatit 500 Kč" in text
    assert "nic prosím neposílej" not in text
    assert "zůstává evidovaná" in text


def test_a_hand_entry_has_no_claim_and_its_payment_is_held(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    register(client, auth_headers, "Holder")
    entered = client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Door", "disciplines": ["LS"]},
        headers=organizer,
    ).json()
    door = db_session().get(Registration, entered["registration_id"])
    assert door is not None
    assert door.claim_total is None

    pay(client, organizer, door.vs)

    (held,) = transactions_of(door.vs)
    assert (held.status, held.status_reason) == ("flagged", "registration_queued")


def test_a_payment_of_the_claim_seats_at_once_where_places_are_free(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    holder, _ = register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")
    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    mailbox.sent.clear()

    result = pay(client, organizer, vs)

    assert result["matched"] == 1
    assert seated(vs) == {"LS": True}
    paid = registration(vs)
    assert paid.settled and paid.total_amount == 1000 and paid.claim_total is None
    kinds = db_session().scalars(select(PaymentEvent.kind)).all()
    assert "queue_payment_seated" in kinds
    assert mailbox.subjects() == ["Máš místo — Cup"]


def test_held_while_full_then_seated_when_a_place_frees(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    holder, _ = register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")
    mailbox.sent.clear()

    pay(client, organizer, vs)
    (held,) = transactions_of(vs)
    assert held.status_reason == "queued_no_place"
    assert registration(vs).credited_in("local") == 0
    assert len(mailbox.sent) == 1  # told it is held, once

    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    pay(client, organizer, 9999999, amount="1,00")  # any statement runs a pass

    assert seated(vs) == {"LS": True}
    assert registration(vs).settled


def test_everything_or_nothing(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1, "SA": 1})
    ls_holder, _ = register(client, auth_headers, "LsHolder", ["LS"])
    register(client, auth_headers, "SaHolder", ["SA"])
    _, vs = register(client, auth_headers, "Both", ["LS", "SA"], ["LS", "SA"])
    client.post("/api/tournaments/cup/my-registration/cancel", headers=ls_holder)

    pay(client, organizer, vs, amount="2 000,00")

    assert seated(vs) == {"LS": False, "SA": False}
    (held,) = transactions_of(vs)
    assert held.status_reason == "queued_no_place"


def test_the_first_payer_takes_a_single_freed_place(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    holder, _ = register(client, auth_headers, "Holder")
    _, first = register(client, auth_headers, "First")
    _, second = register(client, auth_headers, "Second")
    # the second in the queue pays first
    pay(client, organizer, second)
    pay(client, organizer, first)

    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    pay(client, organizer, 9999999, amount="1,00")

    assert seated(second) == {"LS": True}
    assert seated(first) == {"LS": False}
    assert transactions_of(first)[0].status_reason == "queued_no_place"


def test_a_wrong_amount_never_seats_itself(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    holder, _ = register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")

    pay(client, organizer, vs, amount="600,00")
    (held,) = transactions_of(vs)
    assert held.status_reason == "queued_amount_mismatch"

    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    pay(client, organizer, 9999999, amount="1,00")

    assert seated(vs) == {"LS": False}
    assert transactions_of(vs)[0].status_reason == "queued_amount_mismatch"


def test_the_organizers_refund_is_not_undone(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    holder, _ = register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")
    pay(client, organizer, vs)
    (held,) = transactions_of(vs)
    refund = client.post(
        f"/api/tournaments/cup/payments/transactions/{held.id}/mark-for-refund", headers=organizer
    )
    assert refund.status_code in (200, 204), refund.text

    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    pay(client, organizer, 9999999, amount="1,00")

    assert seated(vs) == {"LS": False}


def test_turning_the_setting_off_holds_for_the_organizer_again(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    holder, _ = register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")
    pay(client, organizer, vs)
    client.patch("/api/tournaments/cup", json={"queue_payment_seats": False}, headers=organizer)

    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    pay(client, organizer, 9999999, amount="1,00")

    assert seated(vs) == {"LS": False}
    assert transactions_of(vs)[0].status_reason == "registration_queued"


def test_turning_the_setting_on_lets_a_held_payment_seat(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1}, seats=False)
    holder, _ = register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")
    pay(client, organizer, vs)
    assert transactions_of(vs)[0].status_reason == "registration_queued"
    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)

    client.patch("/api/tournaments/cup", json={"queue_payment_seats": True}, headers=organizer)
    pay(client, organizer, 9999999, amount="1,00")

    assert seated(vs) == {"LS": True}


def test_a_queued_row_states_its_held_payment(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    register(client, auth_headers, "Holder")
    _, vs = register(client, auth_headers, "Waiting")
    pay(client, organizer, vs)

    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    held = {row["name"]: row["payment_held"] for row in rows if "payment_held" in row}
    assert held == {"Holder": False, "Waiting": True}


def test_waitlisted_teams_are_not_part_of_the_claim(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, {"LS": 1})
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-T",
            "weapon": "LS",
            "kind": "team",
            "team_min": 1,
            "team_max": 3,
            "capacity": 1,
            "fee": 3000,
        },
        headers=organizer,
    )
    holder = auth_headers(email="holder@example.com", name="Holder")
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "teams": [{"slug": "LS-T", "name": "First"}]},
        headers=holder,
    )
    fencer = auth_headers(email="waiting@example.com", name="Waiting")
    vs = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "teams": [{"slug": "LS-T", "name": "Second"}]},
        headers=fencer,
    ).json()["vs"]

    waiting = registration(vs)
    assert waiting.teams[0].waitlisted
    assert waiting.claim_total == 1000
