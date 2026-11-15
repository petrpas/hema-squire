"""The bank feed token is kept encrypted (spec tournament-admin, A feed token is
kept encrypted; change encrypt-fio-token).

Even a read-only token opens the whole history of the account it reads, and
every copy of the database (the server's disk, the replica, its snapshots, a
restore drill) would otherwise hold it readable.
"""

import logging

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app import secretbox
from app.bank import get_fio_client
from app.config import settings
from app.main import app
from app.models import Tournament
from app.scheduler import run_tournament_tick
from tests.conftest import AcceptingFio, enable_payments, publish
from tests.test_fio_token import detail, put_token, setup_tournament
from tests.test_matching import db_session

TOKEN = "fio-read-only-token-0123456789abcdef"


class RecordingFio(AcceptingFio):
    """A bank that answers nothing and remembers which token it was handed."""

    def __init__(self):
        self.tokens: list[str] = []

    def verify(self, token):
        self.tokens.append(token)

    def fetch(self, token, date_from, date_to):
        self.tokens.append(token)
        return []


class NoMailer:
    def send(self, message):
        raise AssertionError("nothing here mails")


@pytest.fixture
def bank():
    recording = RecordingFio()
    app.dependency_overrides[get_fio_client] = lambda: recording
    yield recording
    app.dependency_overrides[get_fio_client] = lambda: AcceptingFio()


def published_with_token(client, organizer, slug="cup"):
    if slug == "cup":
        setup_tournament(client, organizer)
    else:
        client.post(
            "/api/tournaments",
            json={"slug": slug, "display_name": slug, "date": "2099-12-05"},
            headers=organizer,
        )
        enable_payments(client, organizer, slug)
        client.post(
            f"/api/tournaments/{slug}/disciplines",
            json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
            headers=organizer,
        )
    publish(client, organizer, slug)
    response = client.put(
        f"/api/tournaments/{slug}/fio-token", json={"token": TOKEN}, headers=organizer
    )
    assert response.status_code == 200, response.text


def stored(slug="cup") -> str | None:
    return db_session().scalar(select(Tournament.fio_token).where(Tournament.slug == slug))


def tournament_row(session, slug="cup") -> Tournament:
    return session.scalars(select(Tournament).where(Tournament.slug == slug)).one()


def poll(client, organizer, slug="cup"):
    return client.post(f"/api/tournaments/{slug}/payments/fio-poll", headers=organizer)


def replace_key(monkeypatch):
    """The deployment's key is lost or replaced: what is stored was sealed
    under one it no longer has."""
    monkeypatch.setattr(settings, "fio_token_key", Fernet.generate_key().decode())


def test_the_database_alone_does_not_yield_the_token(client, auth_headers, bank):
    published_with_token(client, auth_headers())

    value = stored()
    assert value
    assert value != TOKEN
    assert TOKEN not in value


def test_the_poll_and_the_sweep_hand_the_bank_the_token_as_given(client, auth_headers, bank):
    organizer = auth_headers()
    published_with_token(client, organizer)
    bank.tokens.clear()

    assert poll(client, organizer).status_code == 200
    session = db_session()
    run_tournament_tick(session, tournament_row(session), NoMailer(), bank)

    assert bank.tokens == [TOKEN, TOKEN]


def test_without_a_key_no_token_is_recorded(client, auth_headers, bank, monkeypatch):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    monkeypatch.setattr(settings, "fio_token_key", "")

    response = put_token(client, organizer, TOKEN)

    assert response.status_code == 409
    assert response.json()["detail"] == "fio_token_key_missing"
    assert stored() is None
    assert bank.tokens == [], "refused before the bank is asked"
    assert detail(client, organizer)["fio_token_configured"] is False


def test_a_token_the_key_no_longer_opens(client, auth_headers, bank, monkeypatch, caplog):
    organizer = auth_headers()
    published_with_token(client, organizer, "cup")
    published_with_token(client, organizer, "spring")
    session = db_session()
    lost = tournament_row(session, "cup")
    kept = tournament_row(session, "spring")
    # the other tournament's token re-sealed under the key the deployment
    # will have, as an organizer re-entering it would leave it
    replace_key(monkeypatch)
    kept.fio_token = secretbox.seal(TOKEN)
    session.commit()
    bank.tokens.clear()

    # still recorded, so the poll action and deposit mode stay offered; but
    # Setup says it cannot be read
    shown = detail(client, organizer)
    assert (shown["fio_token_configured"], shown["fio_token_readable"]) == (True, False)

    refused = poll(client, organizer)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "fio_token_unreadable"

    with caplog.at_level(logging.WARNING, logger="app.scheduler"):
        skipped = run_tournament_tick(session, lost, NoMailer(), bank)
        polled = run_tournament_tick(session, kept, NoMailer(), bank)

    assert "polled_new" not in skipped, "the feed was skipped"
    assert "seating_demoted" in skipped, "every other pass still ran"
    assert "polled_new" in polled
    assert bank.tokens == [TOKEN], "only the readable feed reached the bank"
    assert "fio token unreadable for cup" in caplog.text


def test_entering_it_again_recovers_the_feed(client, auth_headers, bank, monkeypatch):
    organizer = auth_headers()
    published_with_token(client, organizer)
    replace_key(monkeypatch)
    assert detail(client, organizer)["fio_token_readable"] is False

    assert put_token(client, organizer, TOKEN).status_code == 200

    assert detail(client, organizer)["fio_token_readable"] is True
    bank.tokens.clear()
    assert poll(client, organizer).status_code == 200
    assert bank.tokens == [TOKEN]
