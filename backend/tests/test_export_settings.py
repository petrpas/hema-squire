"""The canonical document carries the tournament's settings (spec data-export,
The document carries the tournament's settings; change
export-tournament-settings).

A restore that drops them reconstructs a different tournament: a manual one
comes back automatic with live clocks, and once published the scheduler would
start windows, reminders and expiries against people who were never meant to
receive them.
"""

import datetime
import io

import pytest
from sqlalchemy import select

from app import managekey, setup
from app.db import get_session
from app.importer import get_import_parser
from app.main import app
from app.models import PaymentMode, Registration, RegistrationsKeptBy, Tournament
from tests.conftest import outcome, post_restore, publish
from tests.test_export_json import fresh_deployment
from tests.test_export_json import setup as automatic_setup
from tests.test_guest_registration import guest_register
from tests.test_guest_registration import setup as guest_setup
from tests.test_issuing import HEADER, RosterParser, row
from tests.test_matching import db_session

URL = "https://example.com/register"

# the new keys of v24, as the restore of an older document must do without them
_V24_TOURNAMENT_KEYS = (
    "registrations_kept_by",
    "payment_mode",
    "deposit_amount",
    "deposit_amount_eur",
    "seating_deadline",
    "seating_settled_at",
    "amendments_close",
    "expiry_grace_hours",
    "external_registration_url",
    "feature_payments",
    "feature_teams",
    "feature_extras",
    "feature_schedule",
    "subtitle",
    "short_code",
    "logo_tint",
    "cover_tint",
    "hr_category_map",
)
_V24_REGISTRATION_KEYS = ("clocks_dormant", "source_row_id", "contact_email")


def session_now():
    """The session of whichever database the app is pointed at: the original's
    before `fresh_deployment`, the restored one's after."""
    override = app.dependency_overrides.get(get_session)
    return next(override()) if override is not None else db_session()


def tournament(slug="cup") -> Tournament:
    return session_now().scalars(select(Tournament).where(Tournament.slug == slug)).one()


def registrations_of(slug="cup") -> list[Registration]:
    session = session_now()
    held = session.scalars(select(Tournament).where(Tournament.slug == slug)).one()
    return list(
        session.scalars(
            select(Registration)
            .where(Registration.tournament_id == held.id)
            .order_by(Registration.id)
        ).all()
    )


def export(client, organizer, slug="cup") -> dict:
    response = client.get(f"/api/tournaments/{slug}/export/json", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()


def sheet_ids(client, organizer, slug="cup") -> list[str]:
    body = client.get(f"/api/tournaments/{slug}/sheet", headers=organizer).json()
    return sorted(r["id"] for r in body["rows"] if not r["_deleted"])


def manual_with_issued_roster(client, organizer):
    """A published manual tournament whose imported fencer list has been
    issued, as an organizer keeping their own registrations builds one."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "city": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
            "external_registration_url": URL,
        },
        headers=organizer,
    )
    response = client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "organizer"},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    publish(client, organizer, "cup")
    app.dependency_overrides[get_import_parser] = lambda: RosterParser()
    content = (HEADER + row("Jan", "jan@example.com") + row("Eva", "eva@example.com")).encode()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("roster.csv", io.BytesIO(content), "text/csv")},
        headers=organizer,
    )
    outcome(client, organizer, "cup", "parse")
    issued = client.post("/api/tournaments/cup/import/issue", headers=organizer)
    assert issued.status_code == 200, issued.text
    assert issued.json()["issued"] == 2


@pytest.fixture
def roster_parser():
    yield
    app.dependency_overrides.pop(get_import_parser, None)


def test_a_manual_tournament_round_trips_as_manual(client, auth_headers, roster_parser):
    organizer = auth_headers()
    manual_with_issued_roster(client, organizer)
    original_sources = sorted(r.source_row_id or "" for r in registrations_of())
    assert all(s.startswith("imp:") for s in original_sources)
    original_rows = sheet_ids(client, organizer)
    assert len(original_rows) == 2, "each issued registration stands in its row's place"
    document = export(client, organizer)

    new_organizer, _ = fresh_deployment(client, auth_headers)
    restore = post_restore(client, new_organizer, document)
    assert restore.status_code == 201, restore.text

    restored = tournament()
    assert restored.registrations_kept_by is RegistrationsKeptBy.ORGANIZER
    assert restored.external_registration_url == URL
    issued = registrations_of()
    assert all(r.clocks_dormant for r in issued)
    assert sorted(r.source_row_id or "" for r in issued) == original_sources
    # listed once each, under the row's own id, not once as a row and again
    # as the registration standing in for it
    assert sheet_ids(client, new_organizer) == original_rows


def test_payment_settings_round_trip(client, auth_headers):
    organizer = auth_headers()
    automatic_setup(client, organizer)
    session = db_session()
    held = session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
    settled = datetime.datetime(2099, 11, 20, 18, 0, tzinfo=datetime.UTC)
    held.payment_mode = PaymentMode.DEPOSIT
    held.deposit_amount = 300
    held.deposit_amount_eur = 12
    held.seating_deadline = datetime.date(2099, 11, 20)
    held.amendments_close = datetime.date(2099, 11, 25)
    held.seating_settled_at = settled
    held.expiry_grace_hours = 12
    held.feature_teams = True
    held.hr_category_map = {"LS-O-S": "Steel Longsword (Mixed & Men's)"}
    session.commit()
    document = export(client, organizer)

    new_organizer, _ = fresh_deployment(client, auth_headers)
    assert post_restore(client, new_organizer, document).status_code == 201

    restored = tournament()
    assert restored.payment_mode is PaymentMode.DEPOSIT
    assert (restored.deposit_amount, restored.deposit_amount_eur) == (300, 12)
    assert restored.seating_deadline == datetime.date(2099, 11, 20)
    assert restored.amendments_close == datetime.date(2099, 11, 25)
    assert restored.expiry_grace_hours == 12
    assert (restored.feature_payments, restored.feature_teams) == (True, True)
    assert restored.hr_category_map == {"LS-O-S": "Steel Longsword (Mixed & Men's)"}
    # settlement is one-shot and keyed on this stamp: a restore that dropped it
    # would let the next pass demote the fencers promoted after it
    stamp = restored.seating_settled_at
    assert stamp is not None
    assert stamp.replace(tzinfo=stamp.tzinfo or datetime.UTC) == settled


@pytest.mark.parametrize(("ground", "restored_ground"), [("green", "green"), ("photo", None)])
def test_tints_travel_and_images_stay_behind(client, auth_headers, ground, restored_ground):
    organizer = auth_headers()
    automatic_setup(client, organizer)
    session = db_session()
    held = session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
    held.subtitle = "Twentieth year"
    held.short_code = "CP"
    held.logo_bytes, held.logo_mime, held.logo_tint = b"logo", "image/png", "blue"
    held.cover_photo_bytes, held.cover_photo_mime = b"photo", "image/jpeg"
    held.cover_tint = ground
    session.commit()
    document = export(client, organizer)
    assert "logo_bytes" not in document["tournament"]
    assert "cover_photo_bytes" not in document["tournament"]

    new_organizer, _ = fresh_deployment(client, auth_headers)
    assert post_restore(client, new_organizer, document).status_code == 201

    restored = tournament()
    assert (restored.subtitle, restored.short_code) == ("Twentieth year", "CP")
    assert not restored.has_logo
    assert not restored.has_cover_photo
    # each is read from or chosen beside an image that did not travel, and
    # means nothing without it
    assert restored.logo_tint is None
    assert restored.cover_tint == restored_ground


def test_a_guest_address_comes_back_and_the_old_link_does_not(client, auth_headers):
    organizer = auth_headers()
    guest_setup(client, organizer)
    out = guest_register(client).json()
    old_key = out["manage_key"]
    session = db_session()
    (registration,) = session.scalars(select(Registration)).all()
    registration.contact_email = "family@example.com"
    session.commit()
    document = export(client, organizer)

    new_organizer, _ = fresh_deployment(client, auth_headers)
    assert post_restore(client, new_organizer, document).status_code == 201

    (restored,) = registrations_of()
    assert restored.contact_email == "family@example.com"
    assert restored.manage_key_generation is None
    # a fresh deployment numbers its first registration as the original did,
    # so the old key names the restored record's id and is refused only
    # because no generation travelled
    assert restored.id == registration.id
    assert managekey.resolve(session_now(), old_key) is None


def test_a_v23_document_restores_manual(client, auth_headers):
    organizer = auth_headers()
    automatic_setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    registered = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert registered.status_code == 201, registered.text
    document = export(client, organizer)
    document["schema_version"] = 23
    for key in _V24_TOURNAMENT_KEYS:
        document["tournament"].pop(key)
    for entry in document["registrations"]:
        for key in _V24_REGISTRATION_KEYS:
            entry.pop(key)

    new_organizer, _ = fresh_deployment(client, auth_headers)
    assert post_restore(client, new_organizer, document).status_code == 201

    assert tournament().registrations_kept_by is RegistrationsKeptBy.ORGANIZER
    refused = client.post("/api/tournaments/cup/publish", headers=new_organizer)
    assert refused.status_code == 422, refused.text
    assert setup.MISSING_EXTERNAL_REGISTRATION in refused.json()["detail"]["missing"]

    # whatever is turned on later, the mode alone keeps every clock stopped
    session = session_now()
    held = session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
    held.feature_payments = True
    held.published_at = datetime.datetime.now(datetime.UTC)
    session.commit()
    restored = registrations_of()
    assert restored
    assert {setup.dormancy_cause(held, r) for r in restored} == {setup.DORMANT_ORGANIZER_KEPT}


def test_a_copy_restores_beside_its_original(client, auth_headers, roster_parser):
    organizer = auth_headers()
    manual_with_issued_roster(client, organizer)
    document = export(client, organizer)
    document["tournament"]["slug"] = "cup-copy"

    restore = post_restore(client, organizer, document)
    assert restore.status_code == 201, restore.text

    original, copy = registrations_of("cup"), registrations_of("cup-copy")
    assert len(original) == len(copy) == 2
    assert {r.source_row_id for r in original} == {r.source_row_id for r in copy}
    assert sheet_ids(client, organizer, "cup-copy") == sheet_ids(client, organizer, "cup")
    # the series is unique across the deployment, so the copy draws from its own
    first, second = tournament("cup"), tournament("cup-copy")
    assert first.vs_year == second.vs_year
    assert first.vs_series != second.vs_series
    assert second.vs_next_seq == 1


def test_a_copy_whose_symbols_are_taken_is_refused(client, auth_headers):
    """A symbol is what a fencer was told to quote, so it is never renumbered;
    a copy holding one the deployment already holds cannot be restored."""
    organizer = auth_headers()
    automatic_setup(client, organizer)
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    registered = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert registered.status_code == 201, registered.text
    document = export(client, organizer)
    document["tournament"]["slug"] = "cup-copy"

    refused = post_restore(client, organizer, document)

    assert refused.status_code == 409
    assert refused.json()["detail"] == "vs_taken"
    assert session_now().scalar(select(Tournament).where(Tournament.slug == "cup-copy")) is None
