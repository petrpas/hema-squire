"""Where a tournament's registration lives when Squire does not hold it, and
what mandatory setup asks of each kind of tournament (spec
external-registration, tournament-admin).

Also the constraint that rides with them: the deposit payment mode expires a
seat on a sliding per-registration window, which only a feed arriving by itself
can answer."""

import pytest
from sqlalchemy import select

from app import setup as app_setup
from app.db import get_session
from app.main import app
from app.models import RegistrationsKeptBy, Tournament
from tests.conftest import enable_payments, publish

IBAN = "CZ6508000000192000145399"
URL = "https://prihlasky.example.org/turnaj-2026"


def db_session():
    return next(app.dependency_overrides[get_session]())


def tournament_row(slug="cup"):
    return db_session().scalar(select(Tournament).where(Tournament.slug == slug))


def make_tournament(client, organizer, **patch):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    base = {"location": "Brno", "organizers": [{"name": "Org", "link": None}]}
    response = client.patch(
        "/api/tournaments/cup", json=base | patch, headers=organizer
    )
    assert response.status_code == 200, response.text
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1200},
        headers=organizer,
    )
    return response


def kept_by_organizer(client, organizer):
    response = client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "organizer"},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    return response.json()


# ------------------------------------------------------------- the address


def test_the_address_round_trips(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url=URL)
    assert (
        client.get("/api/tournaments/cup", headers=organizer).json()[
            "external_registration_url"
        ]
        == URL
    )


@pytest.mark.parametrize("bad", ["not a url", "javascript:alert(1)", "/relative/path"])
def test_a_malformed_address_is_refused(client, auth_headers, bad):
    organizer = auth_headers()
    make_tournament(client, organizer)
    response = client.patch(
        "/api/tournaments/cup",
        json={"external_registration_url": bad},
        headers=organizer,
    )
    assert response.status_code == 422
    assert tournament_row().external_registration_url is None


def test_an_unreachable_address_is_not_the_systems_business(client, auth_headers):
    """Squire stores it and presents it. It does not fetch it, does not check
    that it resolves and does not warn (design D1) — a check at save time
    proves nothing about the moment a fencer follows the link."""
    organizer = auth_headers()
    make_tournament(
        client, organizer, external_registration_url="https://no-such-host.invalid/x"
    )
    assert tournament_row().external_registration_url.endswith("/x")


# ------------------------------------------------------- completeness branches


def test_an_organizer_kept_tournament_needs_its_address(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    kept_by_organizer(client, organizer)

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert app_setup.MISSING_EXTERNAL_REGISTRATION in detail["setup_missing"]

    response = client.post("/api/tournaments/cup/publish", headers=organizer)
    assert response.status_code == 422
    assert app_setup.MISSING_EXTERNAL_REGISTRATION in response.json()["detail"]["missing"]


def test_supplying_the_address_clears_it(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer)
    kept_by_organizer(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"external_registration_url": URL},
        headers=organizer,
    )
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["setup_missing"] == []
    assert client.post("/api/tournaments/cup/publish", headers=organizer).status_code == 200


def test_an_organizer_kept_tournament_needs_no_bank_account(client, auth_headers):
    """Priced, and publishable with nothing to collect into: Squire collects
    nothing for it."""
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url=URL)
    enable_payments(client, organizer, "cup")
    kept_by_organizer(client, organizer)

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["setup_missing"] == []
    assert client.post("/api/tournaments/cup/publish", headers=organizer).status_code == 200


def test_the_registration_window_does_not_block_it(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url=URL)
    kept_by_organizer(client, organizer)
    assert tournament_row().registration_opens is None
    assert tournament_row().registration_closes is None
    assert client.get("/api/tournaments/cup", headers=organizer).json()["setup_missing"] == []


def test_a_squire_kept_tournament_is_unaffected(client, auth_headers):
    """Every other item stands: an organizer-kept tournament is no less a
    tournament, and a Squire-kept one is exactly what it was."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    enable_payments(client, organizer, "cup")
    missing = client.get("/api/tournaments/cup", headers=organizer).json()["setup_missing"]
    assert missing == [app_setup.MISSING_BANK_ACCOUNT]


def test_the_other_mandatory_items_still_apply_when_organizer_kept(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    kept_by_organizer(client, organizer)
    missing = set(
        client.get("/api/tournaments/cup", headers=organizer).json()["setup_missing"]
    )
    assert app_setup.MISSING_LOCATION in missing
    assert app_setup.MISSING_ORGANIZERS in missing
    assert app_setup.MISSING_DISCIPLINES in missing
    assert app_setup.MISSING_EXTERNAL_REGISTRATION in missing


# --------------------------------------------- the deposit mode needs a feed


def test_deposit_mode_without_a_feed_is_reported(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "deposit", "deposit_amount": 300},
        headers=organizer,
    )
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert app_setup.MISSING_PAYMENT_FEED in detail["setup_missing"]
    # reported, never rewritten: switching the mode on the organizer's behalf
    # would hand them a mode they did not choose (design D5)
    assert detail["payment_mode"] == "deposit"


def test_configuring_the_feed_clears_it(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "deposit", "deposit_amount": 300},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup", json={"fio_token": "feed"}, headers=organizer
    )
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert app_setup.MISSING_PAYMENT_FEED not in detail["setup_missing"]
    assert detail["fio_token_configured"] is True


@pytest.mark.parametrize("mode", ["immediate", "reservation"])
def test_the_other_two_modes_need_no_feed(client, auth_headers, mode):
    """Both fall due at the single seating deadline, which a batch of uploaded
    statements answers: one pass after a date, not a continuous watch."""
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup", json={"payment_mode": mode}, headers=organizer
    )
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert app_setup.MISSING_PAYMENT_FEED not in detail["setup_missing"]


def test_a_payments_off_deposit_tournament_is_not_reported(client, auth_headers):
    """No mode applies where no money is collected, so there is nothing for a
    feed to answer."""
    organizer = auth_headers()
    make_tournament(client, organizer)
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "deposit", "deposit_amount": 300, "bank_account": IBAN},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup/features",
        json={
            "feature_schedule": False,
            "feature_payments": False,
            "feature_teams": False,
            "feature_extras": False,
        },
        headers=organizer,
    )
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert app_setup.MISSING_PAYMENT_FEED not in detail["setup_missing"]
    assert detail["payment_mode"] == "deposit"


def test_a_published_deposit_tournament_is_not_unpublished(client, auth_headers):
    """Completeness attaching later never un-publishes: the guarantee attached
    at the moment of publication (spec tournament-admin)."""
    organizer = auth_headers()
    make_tournament(client, organizer, bank_account=IBAN, fio_token="feed")
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "deposit", "deposit_amount": 300},
        headers=organizer,
    )
    publish(client, organizer, "cup")

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.fio_token = None
    session.commit()

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert app_setup.MISSING_PAYMENT_FEED in detail["setup_missing"]
    assert detail["published_at"] is not None
    assert detail["payment_mode"] == "deposit"


def test_an_organizer_kept_tournament_is_not_asked_for_a_feed(client, auth_headers):
    organizer = auth_headers()
    make_tournament(client, organizer, external_registration_url=URL, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "deposit", "deposit_amount": 300},
        headers=organizer,
    )
    kept_by_organizer(client, organizer)
    assert tournament_row().registrations_kept_by is RegistrationsKeptBy.ORGANIZER
    assert client.get("/api/tournaments/cup", headers=organizer).json()["setup_missing"] == []
