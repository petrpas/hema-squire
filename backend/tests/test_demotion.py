"""A demotion for non-payment, and the money around it (design demotion-hardening).

A registration moved below the line for not paying goes to the end of the queue,
is repriced, and is told; money arriving while it sits entirely in the queue is
held for the organizer rather than credited, and never makes it read as paid; a
promotion credits what was held; and a lapsed promotion takes back only what it
seated. The order everything is read in is the placement's queue moment
(spec seating-queue, registration, payment-ledger, payments).
"""

import datetime
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

from app.availability import queue_position, team_waitlist_position
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    BankTransaction,
    PaymentEvent,
    Registration,
    RegistrationState,
    Team,
    Tournament,
)
from tests.conftest import (
    credit_registration,
    deadline_passed,
    enable_payments,
    import_statement,
    pay_registration,
    publish,
    set_fio_token,
    waive_registration,
)

IBAN = "CZ6508000000192000145399"


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def subjects(self) -> list[str]:
        return [message["Subject"] for message in self.sent]

    def bodies(self, subject_part: str) -> list[str]:
        return [
            message.get_body(("plain",)).get_content()
            for message in self.sent
            if subject_part in message["Subject"]
        ]


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


DEMOTED = "Přesun do fronty náhradníků"
HELD = "čekáš ve frontě"
PROMOTED = "Uvolnilo se místo"


def db_session():
    return next(app.dependency_overrides[get_session]())


def make_cup(client, organizer, *, mode="reservation", capacities=None, **params):
    """A published tournament in `mode`, each discipline priced at 1000."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    payload = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "reminder_day": 5,
        "city": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
        "payment_mode": mode,
    }
    payload.update(params)
    set_fio_token(client, organizer, "cup", "test-feed-token")
    response = client.patch("/api/tournaments/cup", json=payload, headers=organizer)
    assert response.status_code == 200, response.text
    for slug, capacity in (capacities or {"LS": 1}).items():
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": slug, "weapon": slug, "capacity": capacity, "fee": 1000},
            headers=organizer,
        )
    publish(client, organizer, "cup")


def enroll(client, auth_headers, name, disciplines=("LS",)):
    fencer = auth_headers(email=f"{name.lower()}@example.com", name=name)
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines)},
        headers=fencer,
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def registration(vs, session=None) -> Registration:
    session = session or db_session()
    found = session.scalar(select(Registration).where(Registration.vs == vs))
    assert found is not None
    return found


def entry(vs, slug, session=None):
    return next(e for e in registration(vs, session).entries if e.discipline.slug == slug)


def positions(slug, *vss) -> list[int | None]:
    session = db_session()
    result = []
    for vs in vss:
        placement = entry(vs, slug, session)
        result.append(queue_position(session, placement) if placement.is_substitute else None)
    return result


def settle(client, organizer):
    response = client.post("/api/tournaments/cup/settle-seating", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()["demoted"]


def process(client, organizer):
    return client.post("/api/tournaments/cup/payments/process", headers=organizer).json()


def admit(client, organizer, vs, slug="LS"):
    registration_id = registration(vs).id
    response = client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/admit/{slug}", headers=organizer
    )
    assert response.status_code == 200, response.text
    return response.json()


def lapse_window(vs):
    session = db_session()
    row = registration(vs, session)
    assert row.expires_at is not None, "a promotion opens a window"
    row.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    session.commit()


def cancel(client, fencer):
    response = client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)
    assert response.status_code == 200, response.text


def statement(vs, amount="1 000,00", row_id=1):
    header = "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    row = f"{row_id};14.07.2026;{amount};CZK;{vs};;;;Jan Novak;123/0800"
    return ("meta;data\n\n" + header + "\n" + row + "\n").encode()


def settled_in_sql(vs) -> bool:
    session = db_session()
    return (
        session.scalar(select(Registration.id).where(Registration.vs == vs, Registration.settled))
        is not None
    )


def kinds(vs) -> list[str]:
    session = db_session()
    return list(
        session.scalars(
            select(PaymentEvent.kind)
            .where(PaymentEvent.registration_id == registration(vs, session).id)
            .order_by(PaymentEvent.id)
        )
    )


# ------------------------------------------------------------ settlement


def test_settlement_sends_the_demoted_to_the_end_of_the_queue(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 2})
    _, first = enroll(client, auth_headers, "First")
    _, second = enroll(client, auth_headers, "Second")
    _, waiting = enroll(client, auth_headers, "Waiting")  # full: queued from the start
    assert positions("LS", waiting) == [1]

    assert settle(client, organizer) == 2

    # the one who waited from the start ranks first, however early the two
    # demoted registered, and the two demoted together keep their own order
    assert positions("LS", waiting, first, second) == [1, 2, 3]
    demoted = registration(first)
    assert entry(first, "LS").queued_since != demoted.registered_at
    assert entry(waiting, "LS").queued_since == registration(waiting).registered_at


def test_settlement_reprices_and_announces_each_demotion_once(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 2})
    _, first = enroll(client, auth_headers, "First")
    _, second = enroll(client, auth_headers, "Second")
    assert registration(first).total_amount == 1000
    mailbox.sent.clear()

    settle(client, organizer)

    demoted = registration(first)
    assert demoted.total_amount == 0
    assert demoted.outstanding_cents == 0
    assert demoted.wire_state == "reserved"
    notices = mailbox.bodies(DEMOTED)
    assert len(notices) == 2
    assert any("1. ve frontě" in body for body in notices)
    assert any("2. ve frontě" in body for body in notices)
    assert all("neposílej" in body for body in notices)
    assert all("zůstává evidovaná" not in body for body in notices)
    assert kinds(first) == ["seating_demoted", "demotion_notified"]


def test_settlement_moving_nobody_mails_nobody(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer)
    _, paid = enroll(client, auth_headers, "Paid")
    session = db_session()
    pay_registration(session, registration(paid, session))
    mailbox.sent.clear()

    assert settle(client, organizer) == 0
    assert mailbox.bodies(DEMOTED) == []


def test_a_forfeited_deposit_is_named_counts_on_promotion_and_never_reads_paid(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_cup(client, organizer, mode="deposit", deposit_amount=500)
    _, vs = enroll(client, auth_headers, "Deposit")
    session = db_session()
    credit_registration(session, registration(vs, session), 50000)

    settle(client, organizer)

    demoted = registration(vs)
    assert demoted.waiting_in_queue
    assert demoted.credited_in("local") == 50000
    assert demoted.total_amount == 0
    # overpaid against a total of nothing, and still not a paid fencer in the
    # queue — in both halves of the derivation
    assert demoted.settled is False
    assert settled_in_sql(vs) is False
    assert demoted.wire_state == "reserved"
    (notice,) = mailbox.bodies(DEMOTED)
    assert "500 Kč" in notice
    assert "zůstává evidovaná" in notice
    assert "vrát" not in notice  # no refund promised

    mailbox.sent.clear()
    admit(client, organizer, vs)
    promoted = registration(vs)
    assert promoted.outstanding_cents == 50000
    (promotion,) = mailbox.bodies(PROMOTED)
    assert "zbývá 500" in promotion


# ------------------------------------------------ lapses and the organizer's return


def test_a_lapsed_promotion_after_settlement_goes_to_the_end(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer)
    _, early = enroll(client, auth_headers, "Early")
    _, waiting = enroll(client, auth_headers, "Waiting")
    settle(client, organizer)
    assert positions("LS", waiting, early) == [1, 2]
    demoted_at = entry(early, "LS").queued_since

    admit(client, organizer, early)
    assert entry(early, "LS").promoted_unpaid
    lapse_window(early)
    mailbox.sent.clear()
    process(client, organizer)

    lapsed = registration(early)
    assert lapsed.state is RegistrationState.RESERVED
    assert lapsed.expires_at is None
    assert entry(early, "LS").queued_since > demoted_at
    assert positions("LS", waiting, early) == [1, 2]
    assert len(mailbox.bodies(DEMOTED)) == 1
    assert "promotion_lapsed" in kinds(early)


def test_a_lapsed_mixed_window_moves_the_seat_and_keeps_the_queue_place(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_cup(client, organizer, mode="immediate", capacities={"LS": 1, "SA": 1})
    enroll(client, auth_headers, "Holder", disciplines=("SA",))
    _, mixed = enroll(client, auth_headers, "Mixed", disciplines=("LS", "SA"))
    _, later = enroll(client, auth_headers, "Later", disciplines=("SA",))
    _, ls_waiting = enroll(client, auth_headers, "Behind", disciplines=("LS",))
    queued_since = entry(mixed, "SA").queued_since
    lapse_window(mixed)
    mailbox.sent.clear()

    process(client, organizer)

    assert registration(mixed).state is RegistrationState.RESERVED
    # the unpaid seat goes to the end of its queue, behind a later registrant
    assert positions("LS", ls_waiting, mixed) == [1, 2]
    # and the placement already queued keeps its moment and its place
    assert entry(mixed, "SA").queued_since == queued_since
    assert positions("SA", mixed, later) == [1, 2]
    (notice,) = mailbox.bodies(DEMOTED)
    assert "2. ve frontě" in notice
    assert "seat_lapsed_to_queue" in kinds(mixed)


def test_the_organizers_return_restores_the_place_the_demotion_gave(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 2})
    _, never_queued = enroll(client, auth_headers, "Never")
    _, early = enroll(client, auth_headers, "Early")
    _, waiting = enroll(client, auth_headers, "Waiting")
    session = db_session()
    pay_registration(session, registration(never_queued, session))
    settle(client, organizer)
    demoted_at = entry(early, "LS").queued_since

    admit(client, organizer, early)
    mailbox.sent.clear()
    response = client.post(
        f"/api/tournaments/cup/registrations/{registration(early).id}/return-to-queue/LS",
        headers=organizer,
    )
    assert response.status_code == 200, response.text

    returned = entry(early, "LS")
    assert returned.queued_since == demoted_at
    assert returned.promoted_unpaid is False
    assert positions("LS", waiting, early) == [1, 2]
    assert mailbox.bodies(DEMOTED) == []


# ---------------------------------------------- a lapse takes back only the promotion


def test_a_paid_seat_survives_an_unpaid_promotion_before_settlement(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, mode="immediate", capacities={"LS": 2, "SA": 1})
    holder, _ = enroll(client, auth_headers, "Holder", disciplines=("SA",))
    _, both = enroll(client, auth_headers, "Both", disciplines=("LS", "SA"))
    session = db_session()
    pay_registration(session, registration(both, session))
    assert registration(both).settled
    cancel(client, holder)

    admit(client, organizer, both, "SA")
    assert registration(both).settled is False
    assert entry(both, "SA").promoted_unpaid
    lapse_window(both)
    mailbox.sent.clear()
    process(client, organizer)

    kept = registration(both)
    assert kept.state is RegistrationState.RESERVED
    assert entry(both, "LS").is_substitute is False
    assert entry(both, "SA").is_substitute is True
    assert kept.total_amount == 1000
    assert kept.settled
    assert kept.expires_at is None
    assert len(mailbox.bodies(DEMOTED)) == 1


def test_a_paid_seat_survives_a_lapsed_team_promotion_after_settlement(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 2})
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-T",
            "weapon": "LS",
            "kind": "team",
            "team_min": 1,
            "team_max": 3,
            "capacity": 1,
            "fee": 1000,
        },
        headers=organizer,
    )
    fencer = auth_headers(email="team@example.com", name="Team")
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "teams": [{"slug": "LS-T", "name": "Wolves"}]},
        headers=fencer,
    )
    assert response.status_code == 201, response.text
    vs = response.json()["vs"]
    session = db_session()
    row = registration(vs, session)
    team = row.teams[0]
    # no route promotes a team yet (design Non-Goals), so the team is
    # entered waitlisted and seated here as a promotion would seat it
    team.waitlisted = True
    row.total_amount = 1000  # the waitlisted team is not priced
    session.commit()
    row = registration(vs, session)
    credit_registration(session, row, row.outstanding_cents)
    settle(client, organizer)
    assert registration(vs).settled

    session = db_session()
    row = registration(vs, session)
    team = row.teams[0]
    team.waitlisted = False
    team.promoted_unpaid = True
    row.total_amount = 2000
    row.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    session.commit()
    mailbox.sent.clear()
    process(client, organizer)

    kept = registration(vs)
    assert entry(vs, "LS").is_substitute is False
    assert kept.teams[0].waitlisted is True
    assert kept.teams[0].promoted_unpaid is False
    assert kept.total_amount == 1000
    assert kept.settled
    session = db_session()
    assert team_waitlist_position(session, registration(vs, session).teams[0]) == 1
    (notice,) = mailbox.bodies(DEMOTED)
    assert "Wolves" in notice


def test_a_fully_queued_promotion_lapsing_before_settlement_returns_to_the_queue(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_cup(client, organizer, mode="immediate")
    holder, _ = enroll(client, auth_headers, "Holder")
    _, waiting = enroll(client, auth_headers, "Waiting")
    cancel(client, holder)
    admit(client, organizer, waiting)
    lapse_window(waiting)
    mailbox.sent.clear()

    assert process(client, organizer)["expired"] == 0

    back = registration(waiting)
    assert back.state is RegistrationState.RESERVED
    assert back.waiting_in_queue
    assert back.total_amount == 0
    assert len(mailbox.bodies(DEMOTED)) == 1
    assert "reservation_expired" not in kinds(waiting)


def test_promotion_marks_clear_once_the_registration_is_paid(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, mode="immediate")
    holder, _ = enroll(client, auth_headers, "Holder")
    _, waiting = enroll(client, auth_headers, "Waiting")
    cancel(client, holder)
    admit(client, organizer, waiting)
    assert entry(waiting, "LS").promoted_unpaid

    session = db_session()
    pay_registration(session, registration(waiting, session))

    assert entry(waiting, "LS").promoted_unpaid is False


# ------------------------------------------------------------- settled


def test_a_waiver_still_settles_a_queued_registration(client, auth_headers):
    organizer = auth_headers()
    make_cup(client, organizer)
    enroll(client, auth_headers, "Holder")
    _, waiting = enroll(client, auth_headers, "Waiting")
    session = db_session()
    waive_registration(session, registration(waiting, session))

    assert registration(waiting).settled
    assert settled_in_sql(waiting)


def test_an_amendment_to_nothing_with_a_seat_still_reads_paid(client, auth_headers):
    organizer = auth_headers()
    make_cup(client, organizer)
    _, vs = enroll(client, auth_headers, "Seated")
    session = db_session()
    pay_registration(session, registration(vs, session))
    row = registration(vs, session)
    row.total_amount = 0
    session.commit()

    assert registration(vs).settled
    assert settled_in_sql(vs)


# -------------------------------------------------- money on a queued registration


def test_a_payment_on_a_queued_registration_is_held_once_and_not_credited(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_cup(client, organizer)
    enroll(client, auth_headers, "Holder")
    _, waiting = enroll(client, auth_headers, "Waiting")
    mailbox.sent.clear()

    import_statement(client, organizer, statement(waiting))

    held = registration(waiting)
    assert held.credited_in("local") == 0
    assert held.wire_state == "reserved"
    transaction = db_session().scalar(select(BankTransaction))
    assert (transaction.status, transaction.status_reason) == ("flagged", "registration_queued")
    assert len(mailbox.bodies(HELD)) == 1
    assert kinds(waiting) == ["match_conflict"]

    # every pass re-evaluates a flagged transaction; the fencer is told once
    import_statement(client, organizer, statement(waiting, row_id=2))
    assert len(mailbox.bodies(HELD)) == 2  # the second transfer, not the first again
    assert kinds(waiting).count("match_conflict") == 2


def test_a_mixed_registration_is_paid_as_usual(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 1, "SA": 1})
    enroll(client, auth_headers, "Holder", disciplines=("SA",))
    _, mixed = enroll(client, auth_headers, "Mixed", disciplines=("LS", "SA"))

    result = import_statement(client, organizer, statement(mixed))

    assert result["matched"] == 1
    assert registration(mixed).settled


def test_promotion_credits_the_held_payment_and_confirms_the_place(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer)
    holder, _ = enroll(client, auth_headers, "Holder")
    _, waiting = enroll(client, auth_headers, "Waiting")
    import_statement(client, organizer, statement(waiting))
    cancel(client, holder)
    mailbox.sent.clear()

    admit(client, organizer, waiting)

    promoted = registration(waiting)
    assert promoted.credited_in("local") == 100000
    assert promoted.settled
    assert promoted.expires_at is None
    assert entry(waiting, "LS").promoted_unpaid is False
    transaction = db_session().scalar(select(BankTransaction))
    assert transaction.status == "matched"
    # one letter: the place, confirmed, and no demand and no second receipt
    assert mailbox.subjects() == ["Uvolnilo se místo — Cup"]
    (notice,) = mailbox.bodies(PROMOTED)
    assert "už uhrazené" in notice


def test_the_deadline_settles_and_announces_like_the_organizer(client, auth_headers, mailbox):
    """The deadline tick demotes and mails exactly as the organizer's action."""
    organizer = auth_headers()
    make_cup(client, organizer)
    _, vs = enroll(client, auth_headers, "Late")
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.seating_deadline = deadline_passed(1)
    session.commit()
    mailbox.sent.clear()

    assert process(client, organizer)["seating_demoted"] == 1
    assert entry(vs, "LS").is_substitute
    assert len(mailbox.bodies(DEMOTED)) == 1


def test_team_waitlist_orders_by_moment(client, auth_headers):
    organizer = auth_headers()
    make_cup(client, organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-T",
            "weapon": "LS",
            "kind": "team",
            "team_min": 1,
            "team_max": 3,
            "capacity": 1,
            "fee": 1000,
        },
        headers=organizer,
    )
    for name in ("Seated", "Alpha", "Beta"):
        fencer = auth_headers(email=f"{name}@example.com", name=name)
        response = client.post(
            "/api/tournaments/cup/register",
            json={"teams": [{"slug": "LS-T", "name": name}]},
            headers=fencer,
        )
        assert response.status_code == 201, response.text
    session = db_session()
    _, alpha, beta = session.scalars(select(Team).order_by(Team.id)).all()
    assert (alpha.waitlisted, beta.waitlisted) == (True, True)
    assert team_waitlist_position(session, alpha) == 1
    alpha.waitlisted_since = beta.waitlisted_since + timedelta(minutes=1)
    session.commit()
    assert team_waitlist_position(session, alpha) == 2
    assert team_waitlist_position(session, beta) == 1
