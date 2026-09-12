"""Who keeps a tournament's list of entrants (spec registration-ownership).

Squire has always assumed it owns the list. Where the organizer keeps it — a
form of their own, a spreadsheet, a club mailing list — the roster reaches
Squire by import, and Squire cleans, matches, prices and exports it while
running nothing against it.

The exclusion is made over tournaments rather than registration by
registration, so a registration created by any path is safe by construction and
not by remembering to mark it."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app import setup as app_setup
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    Fencer,
    Registration,
    RegistrationDiscipline,
    RegistrationsKeptBy,
    RegistrationState,
    Tournament,
)
from app.scheduler import (
    pending_demotions,
    run_tournament_tick,
    settle_seating,
    tournaments_to_tick,
)
from tests.conftest import enable_payments, publish, today_local, today_utc

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


def tournament_row(slug="cup", session=None):
    session = session or db_session()
    return session.scalar(select(Tournament).where(Tournament.slug == slug))


def make_tournament(client, organizer, slug="cup", **patch):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": slug.upper(), "date": "2026-12-05"},
        headers=organizer,
    )
    base = {"city": "Brno", "organizers": [{"name": "Org", "link": None}]}
    response = client.patch(f"/api/tournaments/{slug}", json=base | patch, headers=organizer)
    assert response.status_code == 200, response.text
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1200},
        headers=organizer,
    )


def set_kept_by(client, organizer, value, slug="cup"):
    response = client.patch(
        f"/api/tournaments/{slug}/registrations-kept-by",
        json={"registrations_kept_by": value},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    return response.json()


def enroll(client, auth_headers, email, slug="cup"):
    fencer = auth_headers(email=email, name=email.split("@")[0])
    response = client.post(
        f"/api/tournaments/{slug}/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    return fencer, response


# --------------------------------------------------------------- the value


def test_a_new_tournament_is_squire_kept(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["registrations_kept_by"] == "squire"


def test_the_value_round_trips(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    assert set_kept_by(client, organizer, "organizer")["registrations_kept_by"] == "organizer"
    assert (
        client.get("/api/tournaments/cup", headers=organizer).json()["registrations_kept_by"]
        == "organizer"
    )
    assert set_kept_by(client, organizer, "squire")["registrations_kept_by"] == "squire"


def test_importing_does_not_change_it(client, auth_headers):
    """Never derived from what the tournament holds (design D1): the guarantee
    has to hold from the moment the tournament exists, before anything has
    been imported or registered."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    enroll(client, auth_headers, "a@example.com")
    assert tournament_row().registrations_kept_by is RegistrationsKeptBy.SQUIRE


def test_it_is_not_one_of_the_four_features(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    set_kept_by(client, organizer, "organizer")

    mode = client.get("/api/tournaments/cup/features", headers=organizer).json()
    assert set(mode) == {
        "feature_schedule",
        "feature_payments",
        "feature_teams",
        "feature_extras",
    }
    assert not any(mode.values())
    # and moving one axis does not move the other
    enable_payments(client, organizer, "cup")
    assert tournament_row().registrations_kept_by is RegistrationsKeptBy.ORGANIZER


def test_the_change_writes_no_registration(client, auth_headers, mailbox):
    """The guarantee that no registration is moved by a change of mode, now
    kept by there being no change to make: the only tournaments that can
    switch are drafts, and a draft holds no in-app registration for the switch
    to move (spec tournament-mode, The mode is fixed at publication)."""
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    _, response = enroll(client, auth_headers, "a@example.com")
    vs = response.json()["vs"]

    before = db_session().scalar(select(Registration).where(Registration.vs == vs))
    snapshot = (before.state, before.total_amount, before.credited_in("local"), before.vs)

    refused = client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "organizer"},
        headers=organizer,
    )
    assert refused.status_code == 409
    assert refused.json()["detail"] == "mode_frozen"
    assert tournament_row().registrations_kept_by is RegistrationsKeptBy.SQUIRE

    after = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert (after.state, after.total_amount, after.credited_in("local"), after.vs) == snapshot
    assert [entry.is_substitute for entry in after.entries] == [False]


# ------------------------------------------------ fixed at publication


def test_a_draft_switches_both_ways(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    assert set_kept_by(client, organizer, "organizer")["registrations_kept_by"] == "organizer"
    assert set_kept_by(client, organizer, "squire")["registrations_kept_by"] == "squire"
    assert tournament_row().published_at is None


def test_publication_refuses_the_switch_with_its_reason(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    publish(client, organizer, "cup")

    response = client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "organizer"},
        headers=organizer,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "mode_frozen"
    assert tournament_row().registrations_kept_by is RegistrationsKeptBy.SQUIRE


def test_a_no_op_is_accepted_after_publication(client, auth_headers):
    """A client resending what is already true asks for nothing. Refusing it
    would make an idempotent write an error."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    publish(client, organizer, "cup")

    assert set_kept_by(client, organizer, "squire")["registrations_kept_by"] == "squire"


def test_the_other_settings_still_change_after_publication(client, auth_headers):
    """Being fixed is a property of the mode alone (spec tournament-mode)."""
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN)
    publish(client, organizer, "cup")

    enable_payments(client, organizer, "cup")
    assert tournament_row().feature_payments is True

    response = client.patch(
        "/api/tournaments/cup/features",
        json={
            "feature_schedule": True,
            "feature_payments": False,
            "feature_teams": True,
            "feature_extras": False,
        },
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    row = tournament_row()
    assert (row.feature_schedule, row.feature_payments, row.feature_teams) == (True, False, True)


def test_a_published_manual_tournament_keeps_its_address(client, auth_headers):
    """The completeness guarantee this makes possible (spec tournament-admin):
    a tournament complete when it was published cannot be made incomplete by a
    mode changed afterwards."""
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url="https://elsewhere.example/e")
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["setup_missing"] == []

    client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "squire"},
        headers=organizer,
    )
    after = client.get("/api/tournaments/cup", headers=organizer).json()
    assert after["registrations_kept_by"] == "organizer"
    assert after["setup_missing"] == []


# ----------------------------------------------- the tournament-level exclusion


def test_an_organizer_kept_tournament_is_not_ticked(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, slug="mine")
    make_tournament(
        client,
        organizer,
        slug="theirs",
        external_registration_url="https://elsewhere.example/e",
    )
    # the mode moves before publication and freezes at it (spec
    # tournament-mode), and both are published so that the exclusion under test
    # is the only one either could fall to
    set_kept_by(client, organizer, "organizer", slug="theirs")
    publish(client, organizer, "mine")
    publish(client, organizer, "theirs")

    session = db_session()
    considered = {t.slug for t in tournaments_to_tick(session)}
    assert considered == {"mine"}


def test_a_draft_is_not_ticked_either(client, auth_headers):
    """The third exclusion: a draft holds nobody for a clock to run against
    (spec registration, One dormancy predicate governs the lifecycle passes).
    Asserted beside its neighbours because all three are made in one place."""
    organizer = auth_headers()
    make_tournament(client, organizer, slug="draft")
    make_tournament(client, organizer, slug="live")
    publish(client, organizer, "live")

    session = db_session()
    assert {t.slug for t in tournaments_to_tick(session)} == {"live"}


def test_publication_starts_the_clocks(client, auth_headers):
    """And no registration is rewritten by it: the cause is read live off the
    tournament, so the same registration answers differently on either side of
    publication."""
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    session = db_session()
    tournament = tournament_row(session=session)
    registration = Registration(
        tournament_id=tournament.id,
        fencer_id=tournament.owner_id,
        state=RegistrationState.RESERVED,
        total_amount=1200,
        clocks_dormant=False,
    )
    session.add(registration)
    session.commit()
    assert app_setup.dormancy_cause(tournament, registration) == (app_setup.DORMANT_UNPUBLISHED)

    publish(client, organizer, "cup")
    session.refresh(tournament)
    session.refresh(registration)
    assert app_setup.dormancy_cause(tournament, registration) is None


def test_a_held_tournament_is_not_ticked_either(client, auth_headers):
    """The other exclusion, asserted here so the two are visibly different in
    kind: one is behind its clocks, the other was never under them."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    publish(client, organizer, "cup")
    session = db_session()
    tournament = tournament_row(session=session)
    tournament.date = today_utc() - timedelta(days=1)
    session.commit()
    assert tournaments_to_tick(session) == []


def test_the_lifecycle_touches_nothing_on_an_organizer_kept_tournament(
    client, auth_headers, mailbox
):
    """The strong property: a registration created **without** the per-row
    dormancy mark is still untouched, because the passes are never reached
    (design D2)."""
    organizer = auth_headers()
    make_tournament(
        client,
        organizer,
        bank_account=IBAN,
        reservation_validity_days=7,
        reminder_day=2,
    )
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    _, response = enroll(client, auth_headers, "a@example.com")
    vs = response.json()["vs"]
    mailbox.sent.clear()

    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    assert registration.clocks_dormant is False, "the per-row mark is deliberately unset"
    registration.registered_at = datetime.now(UTC) - timedelta(days=400)
    registration.expires_at = datetime.now(UTC) - timedelta(days=395)
    tournament = tournament_row(session=session)
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    tournament.registration_closes = today_local() - timedelta(days=1)
    session.commit()

    assert tournaments_to_tick(session) == []

    # and reached directly — the organizer's own "process now" action does
    # reach the passes, and the dormancy cause is what stops it there
    collector = CollectingMailer()
    result = run_tournament_tick(session, tournament_row(session=session), collector)
    assert result == {
        "seating_demoted": 0,
        "expired": 0,
        "reminders": 0,
        "composition_reminders": 0,
    }
    assert collector.sent == []
    after = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert after.state == RegistrationState.RESERVED
    assert [entry.is_substitute for entry in after.entries] == [False]


def test_payment_settings_do_not_revive_it(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN, reservation_validity_days=7)
    enable_payments(client, organizer, "cup")
    set_kept_by(client, organizer, "organizer")

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["bank_account"] == IBAN
    assert detail["reservation_validity_days"] == 7
    assert detail["feature_payments"] is True
    assert tournaments_to_tick(db_session()) == []


# ------------------------------------- the paths the exclusion does not cover


def test_manual_settlement_demotes_nobody(client, auth_headers, mailbox):
    """The registration is written straight into the session, reserved and
    **not** dormant, which the API can no longer produce on an organizer-kept
    tournament now that the mode is fixed at publication: an in-app
    registration needs an automatic tournament, and an issued one is dormant by
    origin. That state is the whole point of the test. `clocks_run` reads the
    tournament's mode before it reads the registration's own mark, so a
    registration nothing else made dormant is still safe — which is the
    module's claim that the exclusion is by construction and not by
    remembering to mark each row."""
    organizer = auth_headers()
    make_tournament(
        client,
        organizer,
        bank_account=IBAN,
        external_registration_url="https://elsewhere.example/e",
    )
    enable_payments(client, organizer, "cup")
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")

    session = db_session()
    tournament = tournament_row(session=session)
    auth_headers(email="a@example.com", name="a")
    entrant = session.scalar(select(Fencer).where(Fencer.email == "a@example.com"))
    registration = Registration(
        tournament_id=tournament.id,
        fencer_id=entrant.id,
        state=RegistrationState.RESERVED,
        total_amount=1200,
        clocks_dormant=False,
    )
    registration.entries.append(
        RegistrationDiscipline(discipline_id=tournament.disciplines[0].id, is_substitute=False)
    )
    session.add(registration)
    session.commit()

    assert pending_demotions(session, tournament) == 0
    assert settle_seating(session, tournament) == 0
    assert tournament_row().seating_settled_at is not None

    after = db_session().get(Registration, registration.id)
    assert after.state is RegistrationState.RESERVED
    assert [entry.is_substitute for entry in after.entries] == [False]


# ------------------------------------------------- registration availability


def test_registration_is_refused_with_its_own_reason(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url="https://elsewhere.example/e")
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")

    _, response = enroll(client, auth_headers, "a@example.com")
    assert response.status_code != 201
    assert app_setup.ORGANIZER_KEPT in str(response.json())


def test_it_is_refused_before_every_other_reason(client, auth_headers):
    """Not that this tournament's window is shut, but that it has no window
    here — so it is answered first, and never as `closed` (design D4)."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    session = db_session()
    tournament = tournament_row(session=session)
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    tournament.registration_closes = today_local() - timedelta(days=30)
    session.commit()

    # unpublished, and long past its close: both would otherwise answer
    assert tournament.published_at is None
    assert (
        app_setup.registration_availability(tournament, datetime.now(UTC))
        == app_setup.ORGANIZER_KEPT
    )


def test_amendment_is_refused_alike(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    publish(client, organizer, "cup")
    session = db_session()
    tournament = tournament_row(session=session)
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    session.commit()
    assert (
        app_setup.amendment_availability(tournament, datetime.now(UTC)) == app_setup.ORGANIZER_KEPT
    )


def test_a_squire_kept_tournament_still_registers(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    publish(client, organizer, "cup")
    _, response = enroll(client, auth_headers, "a@example.com")
    assert response.status_code == 201


def test_the_fencer_facing_list_says_elsewhere_not_closed(client, auth_headers):
    """Reported as open, the card would offer a Register button that answers
    400; reported as closed, it would tell the fencer they were too late for a
    window that never existed here (design D4)."""
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url="https://elsewhere.example/e")
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")

    fencer = auth_headers(email="f@example.com", name="F")
    listed = client.get("/api/tournaments/open", headers=fencer).json()
    entry = next(t for t in listed if t["slug"] == "cup")
    assert entry["registration_status"] == "elsewhere"


def test_a_squire_kept_tournament_is_still_listed_open(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    publish(client, organizer, "cup")

    fencer = auth_headers(email="f@example.com", name="F")
    listed = client.get("/api/tournaments/open", headers=fencer).json()
    entry = next(t for t in listed if t["slug"] == "cup")
    assert entry["registration_status"] == "open"


def test_the_mine_tab_needs_no_change(client, auth_headers):
    """Contrary to the working brief, which expected an organizer-kept
    tournament to vanish from Mine. Mine lists tournaments the account is bound
    to by registration **or by organizing** (spec fencer-home), so it appears
    there for its organizer, correctly, and is absent for a fencer who never
    registered in the application — which is already what it does."""
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url="https://elsewhere.example/e")
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")

    mine = client.get("/api/tournaments/mine", headers=organizer).json()
    assert [t["slug"] for t in mine] == ["cup"]

    stranger = auth_headers(email="nobody@example.com", name="Nobody")
    assert client.get("/api/tournaments/mine", headers=stranger).json() == []
