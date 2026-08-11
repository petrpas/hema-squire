"""Payment modes, the seating deadline, and the settlement pass.

Covers the two clocks the change turns on (design add-payment-modes Decision
1): the payment window, private to one registration, whose lapse *expires*;
and the seating deadline, one date for the whole tournament, whose passing
*queues*. Also the deposit threshold, promotion/return-to-queue, and the
validation the new parameters carry.
"""

import datetime
import io
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    PaymentEvent,
    PaymentMode,
    Registration,
    RegistrationState,
    Tournament,
)
from tests.conftest import publish

IBAN = "CZ6508000000192000145399"
TOURNAMENT_DATE = "2026-12-05"


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


def make_tournament(client, organizer, *, mode="immediate", capacity=2, fee_eur=None, **params):
    """A published tournament in `mode`, priced at 1000 with a 7-day payment
    window. Every test's starting point; `params` patches anything else."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": TOURNAMENT_DATE},
        headers=organizer,
    )
    payload = {
        "bank_account": IBAN,
        "reservation_validity_days": 7,
        "reminder_day": 5,
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
        "payment_mode": mode,
    }
    payload.update(params)
    response = client.patch("/api/tournaments/cup", json=payload, headers=organizer)
    assert response.status_code == 200, response.text
    discipline = {"slug": "LS", "weapon": "LS", "capacity": capacity, "fee": 1000}
    if fee_eur is not None:
        discipline["fee_eur"] = fee_eur
    client.post("/api/tournaments/cup/disciplines", json=discipline, headers=organizer)
    publish(client, organizer, "cup")
    return response.json()


def enroll(client, auth_headers, email="jan@example.com", name="Jan", **body):
    fencer = auth_headers(email=email, name=name)
    payload = {"disciplines": ["LS"]}
    payload.update(body)
    response = client.post("/api/tournaments/cup/register", json=payload, headers=fencer)
    assert response.status_code == 201, response.text
    return fencer, response.json()


def set_seating_deadline(days_ago):
    """Move the tournament's seating deadline into the past. It is validated
    against the registration close on write, so tests that want a *passed*
    deadline set it directly rather than through the API."""
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.seating_deadline = datetime.date.today() - timedelta(days=days_ago)
    session.commit()


def process(client, organizer):
    return client.post("/api/tournaments/cup/payments/process", headers=organizer).json()


def registration_by_vs(vs):
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


def event_kinds(vs=None):
    session = db_session()
    query = select(PaymentEvent.kind)
    if vs is not None:
        registration = session.scalar(select(Registration).where(Registration.vs == vs))
        query = query.where(PaymentEvent.registration_id == registration.id)
    return session.scalars(query.order_by(PaymentEvent.id)).all()


# ---------------------------------------------------------------- 1. defaults


def test_pre_mode_tournament_is_immediate_with_no_deposit(client, auth_headers):
    """A tournament that never chose a mode behaves exactly as it did before
    modes existed: full amount at registration, a payment window, no deposit
    and no seating behaviour (design Decision 9)."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": TOURNAMENT_DATE},
        headers=organizer,
    )
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["payment_mode"] == "immediate"
    assert detail["seating_deadline"] is None
    assert detail["seating_settled_at"] is None
    assert detail["deposit_amount"] is None
    assert detail["deposit_amount_eur"] is None
    # the stored window is untouched by the new 2-7 range
    assert detail["reservation_validity_days"] == 10


# ------------------------------------------------- 2. seating deadline helpers


@pytest.mark.parametrize(
    ("deadline", "closes", "expected"),
    [
        ("2026-09-01", "2026-10-01", "2026-09-01"),  # explicit deadline wins
        (None, "2026-10-01", "2026-10-01"),  # falls back to registration close
        (None, None, TOURNAMENT_DATE),  # and then to the tournament date
    ],
)
def test_seating_deadline_resolution(deadline, closes, expected):
    from app.setup import seating_deadline_for

    tournament = Tournament(
        date=datetime.date.fromisoformat(TOURNAMENT_DATE),
        registration_closes=datetime.date.fromisoformat(closes) if closes else None,
        seating_deadline=datetime.date.fromisoformat(deadline) if deadline else None,
    )
    assert seating_deadline_for(tournament) == datetime.date.fromisoformat(expected)


def test_seating_deadline_explicit_wins_over_both_fallbacks():
    from app.setup import seating_deadline_for

    tournament = Tournament(
        date=datetime.date(2026, 12, 5),
        registration_closes=None,
        seating_deadline=datetime.date(2026, 9, 1),
    )
    assert seating_deadline_for(tournament) == datetime.date(2026, 9, 1)


def test_seating_has_settled_by_stamp_or_by_deadline():
    """Both disjuncts matter (Decision 6a): the stamp alone leaves the gap
    between the deadline and the next tick, the deadline alone ignores an
    organizer who settled early."""
    from app.setup import seating_has_settled

    tournament = Tournament(
        date=datetime.date(2026, 12, 5), seating_deadline=datetime.date(2026, 10, 1)
    )
    assert not seating_has_settled(tournament, datetime.date(2026, 9, 1))
    # the deadline day itself is still open; it settles once it has passed
    assert not seating_has_settled(tournament, datetime.date(2026, 10, 1))
    assert seating_has_settled(tournament, datetime.date(2026, 10, 2))

    tournament.seating_settled_at = datetime.datetime(2026, 9, 1, tzinfo=UTC)
    assert seating_has_settled(tournament, datetime.date(2026, 9, 1))


# --------------------------------------------- 3. registration, per mode


def test_reservation_mode_holds_a_seat_with_no_payment_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    _, registration = enroll(client, auth_headers)

    assert registration["expires_at"] is None
    assert registration["entries"][0]["is_substitute"] is False
    # `taken_seats` reads a null expires_at as holding, so the seat is taken
    (availability,) = client.get("/api/tournaments/cup/availability").json()
    assert availability["taken"] == 1
    assert availability["free"] == 1


@pytest.mark.parametrize("mode", ["immediate", "deposit"])
def test_immediate_and_deposit_open_a_payment_window(client, auth_headers, mode):
    organizer = auth_headers()
    make_tournament(client, organizer, mode=mode, deposit_amount=300)
    _, registration = enroll(client, auth_headers)

    expires = datetime.datetime.fromisoformat(registration["expires_at"])
    registered = datetime.datetime.fromisoformat(registration["registered_at"])
    assert (expires - registered).days == 7


def test_registration_after_the_deadline_is_queued_and_owes_nothing(client, auth_headers):
    """Free seats are irrelevant once seating has settled (spec:
    "Registration after seating has settled")."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    set_seating_deadline(days_ago=1)

    fencer, registration = enroll(client, auth_headers)
    assert registration["entries"][0]["is_substitute"] is True
    assert registration["entries"][0]["queue_position"] == 1
    assert registration["expires_at"] is None
    # substitute placements are unbilled at the pricing level (pricing.py)
    assert registration["total_amount"] == 0

    (availability,) = client.get("/api/tournaments/cup/availability").json()
    assert availability["free"] == 2  # the seat was never taken
    assert availability["queue_length"] == 1
    # nothing is owed, so there are no payment instructions to fetch
    assert (
        client.get("/api/tournaments/cup/my-registration/payment", headers=fencer).status_code
        == 409
    )


def test_registration_after_an_early_manual_settlement_is_queued(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    assert client.post("/api/tournaments/cup/settle-seating", headers=organizer).status_code == 200

    _, registration = enroll(client, auth_headers)
    assert registration["entries"][0]["is_substitute"] is True


def test_registration_close_still_refuses_after_the_seating_deadline(client, auth_headers):
    """The seating deadline is a soft boundary inside the hard close, never a
    replacement for it."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.registration_closes = datetime.date.today() - timedelta(days=1)
    tournament.seating_deadline = datetime.date.today() - timedelta(days=2)
    session.commit()

    fencer = auth_headers(email="late@example.com", name="Late")
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "closed"


# --------------------------------------------------- 4. settlement pass


def test_settlement_demotes_the_unpaid_and_leaves_the_paid_alone(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation", capacity=4)
    _, unpaid = enroll(client, auth_headers)
    paid_fencer, paid = enroll(client, auth_headers, email="eva@example.com", name="Eva")

    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == paid["vs"]))
    registration.state = RegistrationState.PAID
    session.commit()

    set_seating_deadline(days_ago=1)
    assert process(client, organizer)["seating_demoted"] == 1

    demoted = registration_by_vs(unpaid["vs"])
    assert demoted.state == RegistrationState.RESERVED  # queued, never expired
    assert demoted.vs == unpaid["vs"]
    assert demoted.expires_at is None
    assert [e.is_substitute for e in demoted.entries] == [True]
    assert event_kinds(unpaid["vs"]) == ["seating_demoted"]

    still_seated = registration_by_vs(paid["vs"])
    assert [e.is_substitute for e in still_seated.entries] == [False]
    assert event_kinds(paid["vs"]) == []

    (availability,) = client.get("/api/tournaments/cup/availability").json()
    assert availability["taken"] == 1  # only the paid one still holds a seat
    assert availability["queue_length"] == 1


def test_settlement_preserves_registration_order_in_the_queue(client, auth_headers):
    """`queue_position` ranks by `registered_at`, so demotion places everyone
    in registration order with no sorting code (design Context)."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation", capacity=5)
    fencers = []
    for index, email in enumerate(("a@example.com", "b@example.com", "c@example.com")):
        fencer, registration = enroll(client, auth_headers, email=email, name=email[0].upper())
        session = db_session()
        row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
        row.registered_at = datetime.datetime.now(UTC) - timedelta(days=10 - index)
        session.commit()
        fencers.append(fencer)

    set_seating_deadline(days_ago=1)
    assert process(client, organizer)["seating_demoted"] == 3

    positions = [
        client.get("/api/tournaments/cup/my-registration", headers=fencer).json()["entries"][0][
            "queue_position"
        ]
        for fencer in fencers
    ]
    assert positions == [1, 2, 3]


def test_settlement_waitlists_teams_with_their_registration(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "Team-LS",
            "weapon": "LS",
            "kind": "team",
            "capacity": 4,
            "fee": 2000,
            "team_min": 2,
            "team_max": 3,
        },
        headers=organizer,
    )
    _, registration = enroll(
        client, auth_headers, disciplines=[], teams=[{"slug": "Team-LS", "name": "Alpha"}]
    )
    assert registration["teams"][0]["waitlisted"] is False

    set_seating_deadline(days_ago=1)
    assert process(client, organizer)["seating_demoted"] == 1

    demoted = registration_by_vs(registration["vs"])
    assert [team.waitlisted for team in demoted.teams] == [True]


def test_settlement_runs_once_and_never_unwinds_a_promotion(client, auth_headers, mailbox):
    """Settlement's predicate is "reserved and seated", which is exactly what
    promotion produces — the stamp is what stops the next tick undoing the
    organizer's work (design Decision 6)."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    fencer, registration = enroll(client, auth_headers)

    set_seating_deadline(days_ago=1)
    assert process(client, organizer)["seating_demoted"] == 1
    demoted = registration_by_vs(registration["vs"])

    assert (
        client.post(
            f"/api/tournaments/cup/registrations/{demoted.id}/admit/LS", headers=organizer
        ).status_code
        == 200
    )
    assert process(client, organizer)["seating_demoted"] == 0
    promoted = registration_by_vs(registration["vs"])
    assert [e.is_substitute for e in promoted.entries] == [False]


def test_settlement_keeps_a_credited_deposit_recorded(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="deposit", deposit_amount=300)
    _, registration = enroll(client, auth_headers)

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.amount_paid_cents = 30000
    row.expires_at = None  # the deposit closed the window
    session.commit()

    set_seating_deadline(days_ago=1)
    assert process(client, organizer)["seating_demoted"] == 1

    demoted = registration_by_vs(registration["vs"])
    assert demoted.amount_paid_cents == 30000  # not refunded, still recorded
    assert [e.is_substitute for e in demoted.entries] == [True]


def test_immediate_mode_settles_without_demoting_anyone(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="immediate")
    _, registration = enroll(client, auth_headers)
    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.state = RegistrationState.PAID
    session.commit()

    response = client.post("/api/tournaments/cup/settle-seating", headers=organizer)
    assert response.status_code == 200
    assert response.json()["demoted"] == 0
    assert response.json()["seating_settled_at"] is not None


def test_manual_settlement_stamps_and_the_later_deadline_does_nothing(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    _, registration = enroll(client, auth_headers)

    response = client.post("/api/tournaments/cup/settle-seating", headers=organizer)
    assert response.json()["demoted"] == 1
    stamped = client.get("/api/tournaments/cup", headers=organizer).json()["seating_settled_at"]
    assert stamped is not None

    set_seating_deadline(days_ago=1)
    assert process(client, organizer)["seating_demoted"] == 0
    assert (
        client.get("/api/tournaments/cup", headers=organizer).json()["seating_settled_at"]
        == stamped
    )


def test_settling_twice_is_refused(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    assert client.post("/api/tournaments/cup/settle-seating", headers=organizer).status_code == 200
    response = client.post("/api/tournaments/cup/settle-seating", headers=organizer)
    assert response.status_code == 409
    assert response.json()["detail"] == "seating_already_settled"


def test_non_organizer_cannot_settle_seating(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    intruder = auth_headers(email="intruder@example.com", name="Intruder")
    assert client.post("/api/tournaments/cup/settle-seating", headers=intruder).status_code == 403


def test_settlement_precedes_expiry_in_one_pass(client, auth_headers, mailbox):
    """Deposit mode can put a registration under both clocks at once; settling
    first makes the outcome independent of tick timing (Decision 1)."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="deposit", deposit_amount=300)
    _, registration = enroll(client, auth_headers)

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    session.commit()
    set_seating_deadline(days_ago=1)

    result = process(client, organizer)
    assert result["seating_demoted"] == 1
    assert result["expired"] == 0

    queued = registration_by_vs(registration["vs"])
    assert queued.state == RegistrationState.RESERVED  # queued, not expired
    assert [e.is_substitute for e in queued.entries] == [True]


# ------------------------------------------------------- 5. reminders


def test_reservation_mode_is_reminded_before_the_seating_deadline(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    enroll(client, auth_headers)
    mailbox.sent.clear()

    # deadline still far off: nothing owed yet as far as the reminder cares
    assert process(client, organizer)["reminders"] == 0

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.seating_deadline = datetime.date.today() + timedelta(days=5)
    session.commit()

    assert process(client, organizer)["reminders"] == 1
    assert process(client, organizer)["reminders"] == 0  # sent once


def test_fully_queued_registration_is_never_reminded(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    set_seating_deadline(days_ago=1)
    enroll(client, auth_headers)
    mailbox.sent.clear()

    assert process(client, organizer)["reminders"] == 0


def test_deposit_paid_registration_is_reminded_about_its_balance(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="deposit", deposit_amount=300)
    _, registration = enroll(client, auth_headers)
    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.amount_paid_cents = 30000
    row.expires_at = None  # deposit closed the window; the deadline remains
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.seating_deadline = datetime.date.today() + timedelta(days=5)
    session.commit()
    mailbox.sent.clear()

    assert process(client, organizer)["reminders"] == 1


# ------------------------------------------------- 6. the deposit threshold


def make_csv(rows):
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    )
    return ("meta;data\n\n" + header + "\n" + "\n".join(rows) + "\n").encode()


def import_rows(client, organizer, rows):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(make_csv(rows)), "text/csv")},
        headers=organizer,
    ).json()


def test_credit_reaching_the_deposit_closes_the_payment_window(
    client, auth_headers, mailbox
):
    """The deposit discharges the window rather than extending it, so
    `harden-payment-matching` Decision 3 stands unmodified (Decision 3)."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="deposit", deposit_amount=300)
    fencer, registration = enroll(client, auth_headers)
    vs = registration["vs"]

    import_rows(client, organizer, [f"1;01.08.2026;300,00;CZK;{vs};;;;;"])
    credited = registration_by_vs(vs)
    assert credited.state == RegistrationState.RESERVED
    assert credited.expires_at is None
    assert "deposit_settled" in event_kinds(vs)

    # the window it used to be under has now passed; it survives
    assert process(client, organizer)["expired"] == 0
    assert registration_by_vs(vs).state == RegistrationState.RESERVED


def test_credit_below_the_deposit_leaves_the_window_running(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="deposit", deposit_amount=300)
    _, registration = enroll(client, auth_headers)
    vs = registration["vs"]

    import_rows(client, organizer, [f"1;01.08.2026;200,00;CZK;{vs};;;;;"])
    credited = registration_by_vs(vs)
    assert credited.expires_at is not None
    assert "deposit_settled" not in event_kinds(vs)

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == vs))
    row.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    session.commit()
    assert process(client, organizer)["expired"] == 1


def test_credit_reaching_the_full_total_still_marks_paid(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="deposit", deposit_amount=300)
    _, registration = enroll(client, auth_headers)
    vs = registration["vs"]

    import_rows(client, organizer, [f"1;01.08.2026;1000,00;CZK;{vs};;;;;"])
    settled = registration_by_vs(vs)
    assert settled.state == RegistrationState.PAID
    assert "deposit_settled" not in event_kinds(vs)


def test_the_eur_lane_is_judged_against_the_eur_deposit(client, auth_headers, mailbox):
    """Each currency lane is judged against its own deposit figure, never
    summed — exactly as totals are (design Decision 5 of the currency work)."""
    organizer = auth_headers()
    make_tournament(
        client,
        organizer,
        mode="deposit",
        fee_eur=40,
        eur_payments_enabled=True,
        deposit_amount=300,
        deposit_amount_eur=12,
    )
    _, registration = enroll(client, auth_headers)
    vs = registration["vs"]

    import_rows(client, organizer, [f"1;01.08.2026;8,00;EUR;{vs};;;;;"])
    assert registration_by_vs(vs).expires_at is not None  # short of the EUR deposit

    import_rows(client, organizer, [f"2;02.08.2026;4,00;EUR;{vs};;;;;"])
    reached = registration_by_vs(vs)
    assert reached.amount_paid_eur_cents == 1200
    assert reached.expires_at is None
    assert "deposit_settled" in event_kinds(vs)


# ------------------------------------------------- 7. promotion / return


def test_promotion_clamps_the_window_to_the_tournament(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    _, registration = enroll(client, auth_headers)
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.date = datetime.date.today() + timedelta(days=3)
    session.commit()

    set_seating_deadline(days_ago=1)
    process(client, organizer)
    demoted = registration_by_vs(registration["vs"])

    response = client.post(
        f"/api/tournaments/cup/registrations/{demoted.id}/admit/LS", headers=organizer
    )
    assert response.status_code == 200
    expires = datetime.datetime.fromisoformat(response.json()["expires_at"])
    # the 7-day window would outlive the event; the tournament date wins
    assert expires.date() <= datetime.date.today() + timedelta(days=4)


def test_return_to_queue_frees_the_seat_and_closes_the_window(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, capacity=1)
    _, registration = enroll(client, auth_headers)
    row = registration_by_vs(registration["vs"])

    response = client.post(
        f"/api/tournaments/cup/registrations/{row.id}/return-to-queue/LS", headers=organizer
    )
    assert response.status_code == 200
    assert response.json()["expires_at"] is None
    assert response.json()["entries"][0]["is_substitute"] is True
    assert response.json()["total_amount"] == 0

    (availability,) = client.get("/api/tournaments/cup/availability").json()
    assert availability["free"] == 1
    assert event_kinds(registration["vs"]) == ["returned_to_queue"]


def test_returning_a_paid_registration_is_refused(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, registration = enroll(client, auth_headers)
    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.state = RegistrationState.PAID
    session.commit()

    response = client.post(
        f"/api/tournaments/cup/registrations/{row.id}/return-to-queue/LS", headers=organizer
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "registration_paid_cancel_instead"
    assert [e.is_substitute for e in registration_by_vs(registration["vs"]).entries] == [False]


def test_returned_registration_keeps_its_place_in_the_queue(client, auth_headers):
    """Returning and promoting again must not cost the fencer their place
    relative to other substitutes."""
    organizer = auth_headers()
    make_tournament(client, organizer, capacity=1)
    _, early = enroll(client, auth_headers, email="a@example.com", name="A")
    _, middle = enroll(
        client, auth_headers, email="b@example.com", name="B", wait_for_all=True
    )
    _, late = enroll(client, auth_headers, email="c@example.com", name="C", wait_for_all=True)

    session = db_session()
    for offset, entry in enumerate((early, middle, late)):
        row = session.scalar(select(Registration).where(Registration.vs == entry["vs"]))
        row.registered_at = datetime.datetime.now(UTC) - timedelta(days=10 - offset)
    session.commit()

    # A is seated; B and C are queued behind them. Returning A puts them
    # first, since the queue ranks by registration time.
    seated = registration_by_vs(early["vs"])
    client.post(
        f"/api/tournaments/cup/registrations/{seated.id}/return-to-queue/LS", headers=organizer
    )

    from app.routers.registrations import queue_position

    session = db_session()
    positions = {}
    for entry in (early, middle, late):
        row = session.scalar(select(Registration).where(Registration.vs == entry["vs"]))
        positions[entry["vs"]] = queue_position(session, row.entries[0])
    assert positions == {early["vs"]: 1, middle["vs"]: 2, late["vs"]: 3}


def test_lapsed_promotion_returns_to_the_queue_after_settlement(client, auth_headers, mailbox):
    """After settlement the queue is the tournament's holding area: expiring
    would discard a fencer the organizer deliberately chose (Decision 8)."""
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    _, registration = enroll(client, auth_headers)
    set_seating_deadline(days_ago=1)
    process(client, organizer)

    demoted = registration_by_vs(registration["vs"])
    client.post(f"/api/tournaments/cup/registrations/{demoted.id}/admit/LS", headers=organizer)

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    result = process(client, organizer)
    assert result["expired"] == 1
    lapsed = registration_by_vs(registration["vs"])
    assert lapsed.state == RegistrationState.RESERVED  # back in the queue, not gone
    assert [e.is_substitute for e in lapsed.entries] == [True]
    assert lapsed.expires_at is None
    assert "promotion_lapsed" in event_kinds(registration["vs"])


def test_lapsed_window_before_settlement_still_expires(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer)
    _, registration = enroll(client, auth_headers)
    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == registration["vs"]))
    row.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    assert process(client, organizer)["expired"] == 1
    assert registration_by_vs(registration["vs"]).state == RegistrationState.EXPIRED


# ------------------------------------------------------- 8. validation


@pytest.mark.parametrize("days", [1, 8])
def test_payment_window_outside_the_range_is_rejected(client, auth_headers, days):
    organizer = auth_headers()
    make_tournament(client, organizer)
    response = client.patch(
        "/api/tournaments/cup", json={"reservation_validity_days": days}, headers=organizer
    )
    assert response.status_code == 422


def test_seating_deadline_after_registration_close_is_rejected(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, registration_closes="2026-10-01")
    response = client.patch(
        "/api/tournaments/cup", json={"seating_deadline": "2026-11-01"}, headers=organizer
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "2026-11-01" in detail and "2026-10-01" in detail


def test_seating_deadline_inside_the_registration_window_is_accepted(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, registration_closes="2026-11-01")
    response = client.patch(
        "/api/tournaments/cup", json={"seating_deadline": "2026-10-01"}, headers=organizer
    )
    assert response.status_code == 200
    assert response.json()["seating_deadline"] == "2026-10-01"


def test_deposit_mode_requires_a_deposit(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    response = client.patch(
        "/api/tournaments/cup", json={"payment_mode": "deposit"}, headers=organizer
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "deposit_amount_required"


def test_deposit_mode_requires_the_eur_deposit_when_the_tournament_shows_eur(
    client, auth_headers
):
    organizer = auth_headers()
    make_tournament(client, organizer, fee_eur=40, eur_payments_enabled=True)
    response = client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "deposit", "deposit_amount": 300},
        headers=organizer,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "deposit_amount_eur_required"

    assert (
        client.patch(
            "/api/tournaments/cup",
            json={"payment_mode": "deposit", "deposit_amount": 300, "deposit_amount_eur": 12},
            headers=organizer,
        ).status_code
        == 200
    )


def test_deposit_is_ignored_in_the_other_modes(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation")
    assert (
        client.patch(
            "/api/tournaments/cup", json={"payment_mode": "immediate"}, headers=organizer
        ).status_code
        == 200
    )


def test_reminder_day_must_fall_before_the_window_closes(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    response = client.patch(
        "/api/tournaments/cup",
        json={"reservation_validity_days": 5, "reminder_day": 5},
        headers=organizer,
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "reminder_day=5" in detail and "reservation_validity_days=5" in detail


def test_deposit_amount_is_a_setup_completeness_item(client, auth_headers):
    from app.setup import MISSING_DEPOSIT_AMOUNT, setup_missing

    session = db_session()
    tournament = Tournament(
        date=datetime.date(2026, 12, 5),
        payment_mode=PaymentMode.DEPOSIT,
        location="Brno",
        organizers=[{"name": "Org", "link": None}],
    )
    assert MISSING_DEPOSIT_AMOUNT in setup_missing(tournament)
    tournament.deposit_amount = 300
    assert MISSING_DEPOSIT_AMOUNT not in setup_missing(tournament)
    session.close()


# ------------------------------------------------------- queue view


def test_queue_view_lists_every_discipline_including_empty_ones(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation", capacity=2)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 3, "fee": 900},
        headers=organizer,
    )
    enroll(client, auth_headers)

    queue = client.get("/api/tournaments/cup/queue", headers=organizer).json()
    assert queue["seating_settled_at"] is None
    assert queue["pending_demotions"] == 1
    by_slug = {d["slug"]: d for d in queue["disciplines"]}
    assert by_slug["LS"]["free"] == 1
    assert [row["fencer"] for row in by_slug["LS"]["seated"]] == ["Jan"]
    assert by_slug["LS"]["queued"] == []
    # a discipline nobody entered is stated, not hidden
    assert by_slug["SA"]["seated"] == [] and by_slug["SA"]["queued"] == []


def test_queue_view_numbers_the_queue_in_registration_order(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, mode="reservation", capacity=1)
    enroll(client, auth_headers, email="a@example.com", name="A")
    enroll(client, auth_headers, email="b@example.com", name="B", wait_for_all=True)
    enroll(client, auth_headers, email="c@example.com", name="C", wait_for_all=True)

    queue = client.get("/api/tournaments/cup/queue", headers=organizer).json()
    (discipline,) = queue["disciplines"]
    assert [(row["fencer"], row["queue_position"]) for row in discipline["queued"]] == [
        ("B", 1),
        ("C", 2),
    ]


def test_non_organizer_cannot_read_the_queue(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    intruder = auth_headers(email="intruder@example.com", name="Intruder")
    assert client.get("/api/tournaments/cup/queue", headers=intruder).status_code == 403
