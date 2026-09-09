"""One predicate decides whether Squire runs its lifecycle clocks against a
registration, and every pass consults it (design unify-lifecycle-dormancy).

The bug this change exists for: `settle_seating` read RESERVED as "still owes
money", which is true only where money was asked for. On a payments-off
tournament nothing ever leaves RESERVED, so the day after registration closed
the scheduler moved the entire field into the substitute queue — seats taken
from people who were never billed. It was invisible because a demoted
registration is still RESERVED, which is all the payments-off test asserted."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app import setup as app_setup
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    PaymentEvent,
    Registration,
    RegistrationsKeptBy,
    RegistrationState,
    Tournament,
)
from app.scheduler import (
    pending_demotions,
    run_tournament_tick,
    settle_seating,
)
from tests.conftest import deadline_passed, enable_payments, publish


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


def tournament_row(session=None):
    session = session or db_session()
    return session.scalar(select(Tournament).where(Tournament.slug == "cup"))


def setup_tournament(client, organizer, *, capacity=10, **patch):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    base = {"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]}
    response = client.patch("/api/tournaments/cup", json=base | patch, headers=organizer)
    assert response.status_code == 200, response.text
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": capacity, "fee": 1200},
        headers=organizer,
    )


def enroll(client, auth_headers, email):
    fencer = auth_headers(email=email, name=email.split("@")[0])
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()


def close_registration_yesterday(session):
    """Bring the seating deadline into the past while leaving the tournament
    itself ahead, so the scheduler still selects it — the exact shape of a
    tournament whose entries have closed and whose event has not happened."""
    tournament = tournament_row(session)
    # with no explicit seating deadline this date is also the seating deadline
    # (setup.seating_deadline_for), so it has to be past on every clock that
    # reads it, not just the tournament's own
    tournament.registration_closes = deadline_passed()
    session.commit()
    return tournament


def placements(vs):
    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    return [entry.is_substitute for entry in registration.entries]


# ------------------------------------------------------------- the predicate


class FakeTournament:
    def __init__(self, feature_payments, kept_by=RegistrationsKeptBy.SQUIRE, published=True):
        self.feature_payments = feature_payments
        self.registrations_kept_by = kept_by
        self.published_at = datetime(2026, 1, 1, tzinfo=UTC) if published else None


class FakeRegistration:
    def __init__(self, clocks_dormant):
        self.clocks_dormant = clocks_dormant


SQUIRE = RegistrationsKeptBy.SQUIRE
ORGANIZER = RegistrationsKeptBy.ORGANIZER


@pytest.mark.parametrize(
    "payments,kept_by,issued,expected",
    [
        (True, SQUIRE, False, None),
        (False, SQUIRE, False, app_setup.DORMANT_PAYMENTS_OFF),
        (True, ORGANIZER, False, app_setup.DORMANT_ORGANIZER_KEPT),
        (True, SQUIRE, True, app_setup.DORMANT_ISSUED_FROM_IMPORT),
        # several at once report the widest cause: it explains every
        # registration rather than one, which is what a reader asking "why is
        # nothing moving?" needs first
        (False, ORGANIZER, True, app_setup.DORMANT_PAYMENTS_OFF),
        (True, ORGANIZER, True, app_setup.DORMANT_ORGANIZER_KEPT),
    ],
)
def test_dormancy_cause_over_the_closed_set(payments, kept_by, issued, expected):
    """No session, no scheduler, no tournament row — the predicate is a pure
    function over two values, which is what lets every pass ask it."""
    tournament = FakeTournament(payments, kept_by)
    registration = FakeRegistration(issued)
    assert app_setup.dormancy_cause(tournament, registration) == expected
    assert app_setup.clocks_run(tournament, registration) == (expected is None)


@pytest.mark.parametrize(
    "payments,kept_by,issued",
    [
        (True, SQUIRE, False),
        (False, ORGANIZER, True),
    ],
)
def test_a_draft_is_dormant_whatever_else_holds(payments, kept_by, issued):
    """Unpublished is the widest cause and answers first: a draft holds nobody
    for a clock to run against, whatever its payments setting or the origin of
    the registration (spec registration, One dormancy predicate governs the
    lifecycle passes)."""
    tournament = FakeTournament(payments, kept_by, published=False)
    registration = FakeRegistration(issued)
    assert app_setup.dormancy_cause(tournament, registration) == app_setup.DORMANT_UNPUBLISHED
    assert app_setup.clocks_run(tournament, registration) is False


# ------------------------------------------- the regression: nobody is demoted


def test_payments_off_seating_deadline_demotes_nobody(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    publish(client, organizer, "cup")
    _, one = enroll(client, auth_headers, "a@example.com")
    _, two = enroll(client, auth_headers, "b@example.com")
    # the confirmations are what registering sends; what this asserts is that
    # the lifecycle adds nothing to them
    mailbox.sent.clear()

    session = db_session()
    close_registration_yesterday(session)
    result = run_tournament_tick(session, tournament_row(session), CollectingMailer())

    assert result["seating_demoted"] == 0
    # asserted on the placements, not the state: a demoted registration is
    # still RESERVED, which is what hid this
    assert placements(one["vs"]) == [False]
    assert placements(two["vs"]) == [False]
    assert mailbox.sent == []
    assert (
        db_session().scalar(select(PaymentEvent).where(PaymentEvent.kind == "seating_demoted"))
        is None
    )


def test_payments_off_settlement_still_closes_seating(client, auth_headers, mailbox):
    """Demoting nobody is not the same as skipping settlement. Seats are finite
    whether or not anyone paid for them (design D3)."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    publish(client, organizer, "cup")
    enroll(client, auth_headers, "a@example.com")

    session = db_session()
    close_registration_yesterday(session)
    run_tournament_tick(session, tournament_row(session), CollectingMailer())

    assert tournament_row().seating_settled_at is not None


def test_registration_after_a_payments_off_deadline_joins_the_queue(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    publish(client, organizer, "cup")

    session = db_session()
    tournament = close_registration_yesterday(session)
    # registration_closes gates new submissions, so reopen the window while
    # leaving the seating deadline in the past — what an organizer does when
    # they take late entries after seating has closed
    tournament.seating_deadline = deadline_passed()
    tournament.registration_closes = None
    session.commit()

    _, late = enroll(client, auth_headers, "late@example.com")
    assert placements(late["vs"]) == [True]


def test_dormant_by_origin_is_not_demoted_either(client, auth_headers, mailbox):
    """The other cause reaches settlement the same way, on a tournament that
    does collect — the case `issue-imported-registrations` built the mark for."""
    organizer = auth_headers()
    setup_tournament(client, organizer, bank_account="CZ6508000000192000145399")
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    _, one = enroll(client, auth_headers, "a@example.com")

    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == one["vs"]))
    registration.clocks_dormant = True
    registration.expires_at = None
    close_registration_yesterday(session)

    result = run_tournament_tick(session, tournament_row(session), CollectingMailer())
    assert result["seating_demoted"] == 0
    assert placements(one["vs"]) == [False]
    assert tournament_row().seating_settled_at is not None


# ----------------------------------- the count and the settlement select alike


def test_pending_demotions_and_settlement_agree(client, auth_headers, mailbox):
    """The console states a number before the organizer confirms something
    irreversible. It has to be the number that then happens (design D5)."""
    organizer = auth_headers()
    setup_tournament(client, organizer, bank_account="CZ6508000000192000145399")
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")

    owing = [enroll(client, auth_headers, f"owes{n}@example.com")[1] for n in range(4)]
    dormant = [enroll(client, auth_headers, f"dorm{n}@example.com")[1] for n in range(6)]

    session = db_session()
    for registration in session.scalars(
        select(Registration).where(Registration.vs.in_([r["vs"] for r in dormant]))
    ).all():
        registration.clocks_dormant = True
    session.commit()

    tournament = tournament_row(session)
    assert pending_demotions(session, tournament) == 4
    assert settle_seating(session, tournament) == 4

    for registration in owing:
        assert placements(registration["vs"]) == [True]
    for registration in dormant:
        assert placements(registration["vs"]) == [False]


def test_pending_demotions_is_zero_where_nothing_is_owed(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    publish(client, organizer, "cup")
    enroll(client, auth_headers, "a@example.com")

    session = db_session()
    assert pending_demotions(session, tournament_row(session)) == 0


# ------------------------------------- a collecting tournament is not disturbed


def test_a_collecting_tournament_still_reminds_expires_and_demotes(client, auth_headers, mailbox):
    """The load-bearing test (design, Risks): the predicate returning the right
    value proves little. What matters is that a tournament Squire collects for
    produces the same events, mail and placements it produced before."""
    organizer = auth_headers()
    setup_tournament(
        client,
        organizer,
        bank_account="CZ6508000000192000145399",
        reservation_validity_days=5,
        reminder_day=2,
    )
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")

    _, reminded = enroll(client, auth_headers, "remind@example.com")
    _, expiring = enroll(client, auth_headers, "expire@example.com")

    session = db_session()
    now = datetime.now(UTC)
    session.scalar(select(Registration).where(Registration.vs == reminded["vs"])).expires_at = (
        now + timedelta(days=1)
    )
    session.scalar(select(Registration).where(Registration.vs == expiring["vs"])).expires_at = (
        now - timedelta(hours=1)
    )
    session.commit()

    collector = CollectingMailer()
    result = run_tournament_tick(session, tournament_row(session), collector)

    assert result["expired"] == 1
    assert result["reminders"] == 1
    assert len(collector.sent) == 2
    assert (
        db_session().scalar(select(Registration).where(Registration.vs == expiring["vs"])).state
        == RegistrationState.EXPIRED
    )
