"""Recording the bank feed token.

Its own endpoint rather than a field of the tournament PATCH, because a token is
verified against the bank as it is recorded and there is to be exactly one way
one reaches the database (spec tournament-admin, "A feed token is verified
before it is stored").
"""

import pytest

from app.bank import FioTokenRejected, FioUnreachable, get_fio_client
from app.main import app
from tests.conftest import AcceptingFio, enable_payments, publish


class RefusingFio(AcceptingFio):
    """A bank that will not read the account with this token."""

    def verify(self, token):
        raise FioTokenRejected("404")


class SilentBank(AcceptingFio):
    """A bank that does not answer at all. Says nothing about the token."""

    def verify(self, token):
        raise FioUnreachable("connection refused")


def _override(stub):
    app.dependency_overrides[get_fio_client] = lambda: stub


@pytest.fixture
def refusing_fio():
    _override(RefusingFio())
    yield
    _override(AcceptingFio())


@pytest.fixture
def silent_bank():
    _override(SilentBank())
    yield
    _override(AcceptingFio())


def setup_tournament(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )


def put_token(client, headers, token="secret-token"):
    return client.put("/api/tournaments/cup/fio-token", json={"token": token}, headers=headers)


def detail(client, headers):
    return client.get("/api/tournaments/cup", headers=headers).json()


def test_a_working_token_is_stored(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put_token(client, organizer)

    assert response.status_code == 200, response.text
    assert response.json() == {"configured": True, "verified": True}
    assert detail(client, organizer)["fio_token_configured"] is True


def test_a_token_the_bank_refuses_is_refused_and_stored_nowhere(client, auth_headers, refusing_fio):
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put_token(client, organizer, "mistyped")

    assert response.status_code == 422
    assert response.json()["detail"] == "fio_token_rejected"
    assert detail(client, organizer)["fio_token_configured"] is False


def test_an_unreachable_bank_stores_the_token_unverified(client, auth_headers, silent_bank):
    """Fio being down is not evidence about the token: refusing would make
    recording a correct one depend on the bank's availability that minute."""
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = put_token(client, organizer)

    assert response.status_code == 200, response.text
    assert response.json() == {"configured": True, "verified": False}
    assert detail(client, organizer)["fio_token_configured"] is True


def test_the_token_is_never_returned(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    put_token(client, organizer, "secret-token")

    body = client.get("/api/tournaments/cup", headers=organizer).text

    assert "secret-token" not in body


def test_the_tournament_patch_no_longer_accepts_a_token(client, auth_headers):
    """The endpoint that verifies is the only way in, so a token smuggled into
    the ordinary save is refused rather than stored unchecked."""
    organizer = auth_headers()
    setup_tournament(client, organizer)

    response = client.patch(
        "/api/tournaments/cup", json={"fio_token": "unchecked"}, headers=organizer
    )

    assert response.status_code == 422
    assert detail(client, organizer)["fio_token_configured"] is False


def test_recording_a_token_ingests_nothing(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    publish(client, organizer, "cup")

    put_token(client, organizer)

    transactions = client.get("/api/tournaments/cup/payments/transactions", headers=organizer)
    assert transactions.status_code == 200
    assert transactions.json() == []


def test_removing_a_token_leaves_the_tournament_as_one_that_never_had_one(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    publish(client, organizer, "cup")
    put_token(client, organizer)

    removed = client.delete("/api/tournaments/cup/fio-token", headers=organizer)

    assert removed.status_code == 200
    assert removed.json() == {"configured": False, "verified": False}
    assert detail(client, organizer)["fio_token_configured"] is False
    polled = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)
    assert polled.json()["detail"] == "fio_token_not_configured"


def test_recording_requires_console_access(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    outsider = auth_headers(email="x@example.com", name="X")

    assert put_token(client, outsider).status_code == 403
    assert client.delete("/api/tournaments/cup/fio-token", headers=outsider).status_code == 403
