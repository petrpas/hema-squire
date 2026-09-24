"""A fencer entered by hand on an automatic tournament is a registration at once
(spec registration, A registration entered by hand): placed against capacity like
an in-app submission, carrying a variable symbol, dormant by origin, and sent
nothing of any kind. Import is a manual tournament's road only (spec
table-import)."""

import datetime

import pytest
from sqlalchemy import select

from app import emails, setup
from app.mail import get_mailer
from app.main import app
from app.models import (
    Currency,
    Fencer,
    ImportBatch,
    ManualRow,
    Registration,
    RegistrationDiscipline,
    RegistrationsKeptBy,
    RegistrationState,
    Team,
    Tournament,
)
from tests.conftest import import_statement
from tests.test_demotion import (
    CollectingMailer,
    admit,
    db_session,
    make_cup,
    settle,
    statement,
)


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


ENTRY = {"name": "Door Fencer", "nationality": "CZ", "email": "door@example.com"}


def enter(client, organizer, disciplines=("LS",), **fields):
    return client.post(
        "/api/tournaments/cup/manual-rows",
        json={**ENTRY, "disciplines": list(disciplines), **fields},
        headers=organizer,
    )


def entered(response) -> Registration:
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["row_id"] is None
    found = db_session().get(Registration, body["registration_id"])
    assert found is not None
    return found


def placements(registration: Registration) -> dict[str, bool]:
    return {e.discipline.slug: e.is_substitute for e in registration.entries}


def test_seated_priced_and_given_a_symbol_in_silence(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 2})
    mailbox.sent.clear()

    registration = entered(enter(client, organizer))

    assert placements(registration) == {"LS": False}
    assert registration.vs is not None
    assert registration.total_amount == 1000
    assert registration.expires_at is None
    assert registration.clocks_dormant and registration.source_row_id is None
    assert setup.dormancy_cause(registration.tournament, registration) == (
        setup.DORMANT_ENTERED_BY_HAND
    )
    fencer = registration.fencer
    assert fencer.password_hash is None
    assert fencer.email == "door@example.com"
    assert mailbox.sent == []


def test_placed_per_discipline_like_a_submission(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 1, "SA": 2})
    enter(client, organizer, email="first@example.com", name="First")

    registration = entered(enter(client, organizer, disciplines=("LS", "SA")))

    assert placements(registration) == {"LS": True, "SA": False}
    assert registration.total_amount == 1000


def test_every_discipline_queued_after_settlement(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 5})
    settle(client, organizer)

    registration = entered(enter(client, organizer))

    assert placements(registration) == {"LS": True}
    assert registration.total_amount == 0


def test_not_demoted_at_settlement(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 5})
    registration = entered(enter(client, organizer))
    mailbox.sent.clear()

    assert settle(client, organizer) == 0

    assert placements(db_session().get(Registration, registration.id)) == {"LS": False}
    assert mailbox.sent == []


def test_promoted_without_a_window_or_a_letter(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 1})
    holder = auth_headers(email="holder@example.com", name="Holder")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=holder)
    registration = entered(enter(client, organizer))
    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    mailbox.sent.clear()

    admit(client, organizer, registration.vs)

    promoted = db_session().get(Registration, registration.id)
    assert promoted is not None
    assert placements(promoted) == {"LS": False}
    assert promoted.total_amount == 1000
    assert promoted.expires_at is None
    assert mailbox.sent == []


def test_a_bank_payment_is_credited_without_a_receipt(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 2})
    registration = entered(enter(client, organizer))
    mailbox.sent.clear()

    result = import_statement(client, organizer, statement(registration.vs))

    assert result["matched"] == 1
    assert db_session().get(Registration, registration.id).settled
    assert mailbox.sent == []


def test_an_address_already_registered_here_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 5})
    fencer = auth_headers(email="door@example.com", name="Door Fencer")
    registered = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()

    response = enter(client, organizer)

    assert response.status_code == 409
    refusal = response.json()["detail"]["already_registered"]
    assert refusal["vs"] == registered["vs"]
    assert len(db_session().scalars(select(Registration)).all()) == 1


def test_an_address_held_elsewhere_stays_with_its_holder(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities={"LS": 5})
    auth_headers(email="door@example.com", name="Someone With An Account")

    registration = entered(enter(client, organizer))

    assert registration.fencer.email is None
    assert registration.fencer.display_name == "Door Fencer"


def test_a_manual_tournament_still_takes_a_source_row(client, auth_headers):
    organizer = auth_headers()
    make_cup(client, organizer, external_registration_url="https://elsewhere.example/e")
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    # the mode is fixed at publication; this tournament is made manual the way
    # one that was set so before publishing reads
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    session.commit()

    response = enter(client, organizer)

    assert response.status_code == 201, response.text
    assert response.json()["registration_id"] is None
    assert db_session().scalars(select(ManualRow)).one().name == "Door Fencer"
    assert db_session().scalars(select(Registration)).all() == []


def test_an_import_into_an_automatic_tournament_is_refused(client, auth_headers):
    organizer = auth_headers()
    make_cup(client, organizer)

    response = client.post(
        "/api/tournaments/cup/import",
        files={"file": ("roster.csv", b"Name,Club\nA,B\n", "text/csv")},
        headers=organizer,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "import_needs_manual_mode"
    assert db_session().scalars(select(ImportBatch)).all() == []


def _hand_entry(dormant_source: str | None) -> tuple[Tournament, Fencer, Registration]:
    """Unsaved models of a registration dormant by origin on a tournament that
    collects — issued for a source row, or entered by hand where it has none."""
    tournament = Tournament(
        slug="cup",
        display_name="Cup",
        date=datetime.date(2026, 12, 5),
        language="cs",
        feature_payments=True,
        local_currency=Currency.CZK,
        bank_account="CZ6508000000192000145399",
        amount_tolerance_percent=0,
        eur_payments_enabled=False,
    )
    fencer = Fencer(display_name="Door Fencer", email="door@example.com", language="cs")
    registration = Registration(
        tournament=tournament,
        fencer=fencer,
        state=RegistrationState.RESERVED,
        registered_at=datetime.datetime(2026, 9, 1, tzinfo=datetime.UTC),
        vs=2601001,
        total_amount=1000,
        clocks_dormant=True,
        source_row_id=dormant_source,
        expires_at=None,
        weapon_rentals=[],
        afterparty=False,
        aftersparring=False,
    )
    registration.entries = [
        RegistrationDiscipline(is_substitute=False, queued_since=registration.registered_at)
    ]
    registration.teams = list[Team]()
    return tournament, fencer, registration


def test_no_letter_of_any_kind_reaches_a_hand_entry():
    """Every letter Squire composes about a registration, asked of a hand entry,
    sends nothing — including the surcharge that reaches an issued one despite
    its dormancy."""
    tournament, fencer, registration = _hand_entry(None)
    mailer = CollectingMailer()
    sends = [
        lambda: emails.send_registration_confirmation(mailer, tournament, fencer, registration),
        lambda: emails.send_amendment_confirmation(mailer, tournament, fencer, registration),
        lambda: emails.send_payment_reminder(mailer, tournament, fencer, registration),
        lambda: emails.send_reservation_expired(mailer, tournament, fencer, registration),
        lambda: emails.send_payment_received(mailer, tournament, fencer, registration),
        lambda: emails.send_partial_payment_received(
            mailer, tournament, fencer, registration, "local"
        ),
        lambda: emails.send_surcharge_due(
            mailer, tournament, fencer, registration, despite_dormancy=True
        ),
        lambda: emails.send_promoted(mailer, tournament, fencer, registration, "Longsword"),
        lambda: emails.send_reservation_reinstated(mailer, tournament, fencer, registration),
        lambda: emails.send_payment_after_expiry(mailer, tournament, fencer, registration),
        lambda: emails.send_demoted(mailer, tournament, fencer, registration, [], []),
        lambda: emails.send_payment_while_queued(mailer, tournament, fencer, registration),
    ]
    for send in sends:
        send()
    assert mailer.sent == []


def test_an_issued_registration_is_still_told_of_a_surcharge():
    tournament, fencer, registration = _hand_entry("imp:row")
    mailer = CollectingMailer()

    assert emails.send_surcharge_due(
        mailer, tournament, fencer, registration, despite_dormancy=True
    )
    assert len(mailer.sent) == 1
