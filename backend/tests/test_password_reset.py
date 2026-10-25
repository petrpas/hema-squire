"""A forgotten password is reset through a mailed link, and changing a password
by any path ends every other session (specs password-reset, profile-page)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.config import settings
from app.mail import get_mailer
from app.main import app
from app.models import Fencer, FencerProfileAudit, PasswordReset
from tests.conftest import signup_verified
from tests.test_issuing import db_session, import_roster, issue, row, setup


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


EMAIL = "eva@example.com"
PASSWORD = "correct-horse"


def account(client) -> str:
    return signup_verified(
        client, {"email": EMAIL, "password": PASSWORD, "display_name": "Eva Malá"}
    )


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": EMAIL, "password": password})


def reset_key(message) -> str:
    body = message.get_body(preferencelist=("plain",)).get_content()
    return body.split("/reset#", 1)[1].split()[0]


def request_reset(client, mailbox, email=EMAIL) -> str:
    response = client.post("/api/auth/password-reset", json={"email": email})
    assert response.status_code == 202, response.text
    return reset_key(mailbox.sent[-1])


def confirm(client, key, password="new-horse-battery"):
    return client.post("/api/auth/password-reset/confirm", json={"key": key, "password": password})


def earlier_session() -> dict:
    """A session signed in a minute ago — before the change a test is about to
    make. Tokens are stamped in whole seconds, so one made in the same second
    as the change would read as issued with it."""
    fencer_id = db_session().scalar(select(Fencer.id).where(Fencer.email == EMAIL))
    issued = datetime.now(UTC) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": str(fencer_id), "iat": int(issued.timestamp()), "exp": issued + timedelta(days=1)},
        settings.secret_key,
        algorithm="HS256",
    )
    return bearer(token)


def test_requesting_a_reset_mails_a_link_and_changes_nothing(client, mailbox):
    account(client)
    response = client.post("/api/auth/password-reset", json={"email": EMAIL})
    assert response.status_code == 202
    assert response.json() == {"email": EMAIL}
    assert mailbox.sent[-1]["To"] == EMAIL
    assert "/reset#" in mailbox.sent[-1].get_body(preferencelist=("plain",)).get_content()
    assert login(client).status_code == 200


def test_following_the_link_sets_the_password_and_signs_in(client, mailbox):
    account(client)
    key = request_reset(client, mailbox)
    assert client.post("/api/auth/password-reset/inspect", json={"key": key}).json() == {
        "email": EMAIL
    }
    response = confirm(client, key)
    assert response.status_code == 200
    assert client.get("/api/account", headers=bearer(response.json()["token"])).status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="new-horse-battery").status_code == 200


def test_a_reset_is_audited_without_the_password(client, mailbox):
    account(client)
    confirm(client, request_reset(client, mailbox))
    audit = (
        db_session()
        .scalars(select(FencerProfileAudit).where(FencerProfileAudit.field == "password"))
        .one()
    )
    assert audit.old_value is None
    assert audit.new_value is None


@pytest.mark.parametrize("address", ["nobody@example.com", "eva-pending@example.com"])
def test_an_address_without_an_account_is_told_so(client, mailbox, address):
    # one address nobody holds, one whose signup is still pending
    client.post(
        "/api/auth/signup",
        json={"email": "eva-pending@example.com", "password": PASSWORD, "display_name": "Eva"},
    )
    sent_before = len(mailbox.sent)
    response = client.post("/api/auth/password-reset", json={"email": address})
    assert response.status_code == 404
    assert response.json()["detail"] == "no_account"
    assert len(mailbox.sent) == sent_before


@pytest.mark.usefixtures("before_manual_entry_registers")
def test_a_roster_issued_record_is_not_reset(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novák", "jan@example.com")])
    issue(client, organizer)
    sent_before = len(mailbox.sent)
    response = client.post("/api/auth/password-reset", json={"email": "jan@example.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "no_account"
    assert len(mailbox.sent) == sent_before
    assert db_session().scalars(select(PasswordReset)).all() == []


def test_a_link_works_once(client, mailbox):
    account(client)
    key = request_reset(client, mailbox)
    assert confirm(client, key).status_code == 200
    again = confirm(client, key, password="third-horse-battery")
    assert again.status_code == 410
    assert again.json()["detail"] == "reset_invalid"
    assert login(client, password="new-horse-battery").status_code == 200


def test_a_link_expires_after_an_hour(client, mailbox):
    account(client)
    key = request_reset(client, mailbox)
    session = db_session()
    reset = session.scalars(select(PasswordReset)).one()
    # followed 61 minutes after it was mailed
    reset.created_at = datetime.now(UTC) - timedelta(minutes=61)
    reset.expires_at = reset.created_at + timedelta(hours=1)
    session.commit()
    assert client.post("/api/auth/password-reset/inspect", json={"key": key}).status_code == 410
    assert confirm(client, key).status_code == 410
    assert login(client).status_code == 200


def test_the_latest_request_wins(client, mailbox):
    account(client)
    first = request_reset(client, mailbox)
    second = request_reset(client, mailbox)
    assert confirm(client, first).status_code == 410
    assert confirm(client, second).status_code == 200


def test_too_short_a_password_leaves_the_link_usable(client, mailbox):
    account(client)
    key = request_reset(client, mailbox)
    assert confirm(client, key, password="short").status_code == 422
    assert confirm(client, key).status_code == 200


def test_a_reset_ends_every_other_session(client, mailbox):
    account(client)
    laptop = earlier_session()
    assert client.get("/api/account", headers=laptop).status_code == 200
    phone = bearer(confirm(client, request_reset(client, mailbox)).json()["token"])
    refused = client.get("/api/account", headers=laptop)
    assert refused.status_code == 401
    assert refused.json()["detail"] == "invalid_token"
    assert client.get("/api/account", headers=phone).status_code == 200


def test_sessions_stand_until_the_password_changes(client):
    """Introducing the watermark signs nobody out — not even a token issued
    before tokens carried `iat`."""
    account(client)
    fencer_id = db_session().scalar(select(Fencer.id).where(Fencer.email == EMAIL))
    legacy = jwt.encode(
        {"sub": str(fencer_id), "exp": datetime.now(UTC) + timedelta(days=1)},
        settings.secret_key,
        algorithm="HS256",
    )
    assert client.get("/api/account", headers=bearer(legacy)).status_code == 200
    assert client.get("/api/account", headers=earlier_session()).status_code == 200


def test_a_profile_change_needs_the_current_password(client, mailbox):
    token = account(client)
    sent_before = len(mailbox.sent)
    response = client.post(
        "/api/account/password",
        json={"current_password": "wrong-horse", "new_password": "new-horse-battery"},
        headers=bearer(token),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "wrong_password"
    assert client.get("/api/account", headers=bearer(token)).status_code == 200
    assert login(client).status_code == 200
    assert len(mailbox.sent) == sent_before


def test_a_profile_change_mails_a_notice_and_ends_other_sessions(client, mailbox):
    account(client)
    other = earlier_session()
    here = earlier_session()
    response = client.post(
        "/api/account/password",
        json={"current_password": PASSWORD, "new_password": "new-horse-battery"},
        headers=here,
    )
    assert response.status_code == 200
    assert client.get("/api/account", headers=other).status_code == 401
    assert client.get("/api/account", headers=bearer(response.json()["token"])).status_code == 200
    assert login(client, password="new-horse-battery").status_code == 200
    notice = mailbox.sent[-1]
    assert notice["To"] == EMAIL
    assert "/reset#" not in notice.get_body(preferencelist=("plain",)).get_content()
