"""An account's address moves only through a link its new mailbox follows
(spec profile-page, Address change; design confirm-email-change).

Squire grants by address — a console team, an ownership transfer, the
deployment Owner, a reset link — so an address that reached an account
unconfirmed would carry those grants to a mailbox nobody has shown is the
account holder's.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.mail import get_mailer
from app.main import app
from app.models import Fencer, FencerProfileAudit, PendingEmailChange, Role
from tests.conftest import change_email

PASSWORD = "correct-horse"


class Mailbox:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


@pytest.fixture
def mailbox():
    box = Mailbox()
    app.dependency_overrides[get_mailer] = lambda: box
    yield box
    app.dependency_overrides.pop(get_mailer, None)


def text(message) -> str:
    return message.get_body(preferencelist=("plain",)).get_content()


def ask(client, headers, new_email, password=PASSWORD):
    return client.post(
        "/api/account/email",
        json={"current_password": password, "new_email": new_email},
        headers=headers,
    )


def key_of(message) -> str:
    return text(message).split("/confirm-email#", 1)[1].split()[0]


def address_of(engine, name: str) -> str | None:
    with Session(engine) as session:
        return session.scalars(select(Fencer.email).where(Fencer.display_name == name)).one()


def earlier_session(engine, name: str) -> dict:
    """A session signed in a minute ago. Tokens are stamped in whole seconds,
    so one made in the same second as the change would read as issued with it."""
    with Session(engine) as session:
        fencer_id = session.scalars(select(Fencer.id).where(Fencer.display_name == name)).one()
    issued = datetime.now(UTC) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": str(fencer_id), "iat": int(issued.timestamp()), "exp": issued + timedelta(days=1)},
        settings.secret_key,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_the_update_contract_refuses_an_address(client, auth_headers, engine):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    refused = client.patch(
        "/api/account", json={"email": "new@example.com", "club": "Klub"}, headers=me
    )
    assert refused.status_code == 422
    assert refused.json()["detail"] == "email_change_needs_confirmation"
    account = client.get("/api/account", headers=me).json()
    assert (account["email"], account["club"]) == ("me@example.com", None)


def test_asking_mails_the_new_address_and_changes_nothing_yet(
    client, auth_headers, engine, mailbox
):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    asked = ask(client, me, "new@example.com")
    assert asked.status_code == 202, asked.text
    assert asked.json() == {"email": "new@example.com"}

    (link,) = mailbox.sent
    assert link["To"] == "new@example.com"
    assert "/confirm-email#" in text(link)
    # until the link is followed the old address is the account's
    assert address_of(engine, "Me") == "me@example.com"
    login = client.post("/api/auth/login", json={"email": "me@example.com", "password": PASSWORD})
    assert login.status_code == 200


def test_a_wrong_password_is_refused_and_mails_nothing(client, auth_headers, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    refused = ask(client, me, "new@example.com", password="not-the-password")
    assert refused.status_code == 403
    assert refused.json()["detail"] == "wrong_password"
    assert mailbox.sent == []
    # the session is fine; only the proof was wrong
    assert client.get("/api/account", headers=me).status_code == 200


@pytest.mark.parametrize("credentials", [True, False])
def test_an_address_another_record_holds_is_refused(
    client, auth_headers, engine, mailbox, credentials
):
    """Any record counts, a guest's or a roster record too: the address is
    one record's, and an address change merges nothing (design D2)."""
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    if credentials:
        auth_headers(email="taken@example.com", name="Other", role=Role.FENCER)
    else:
        with Session(engine) as session:
            session.add(Fencer(email="taken@example.com", display_name="Roster Record"))
            session.commit()
    refused = ask(client, me, "taken@example.com")
    assert refused.status_code == 409
    assert mailbox.sent == []


def test_following_the_link_moves_the_address_and_ends_other_sessions(
    client, auth_headers, engine, mailbox
):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    ask(client, me, "new@example.com")
    key = key_of(mailbox.sent[-1])
    laptop = earlier_session(engine, "Me")
    assert client.get("/api/account", headers=laptop).status_code == 200

    confirmed = client.post("/api/account/email/confirm", json={"key": key})
    assert confirmed.status_code == 200, confirmed.text
    fresh = {"Authorization": f"Bearer {confirmed.json()['token']}"}

    assert address_of(engine, "Me") == "new@example.com"
    assert client.get("/api/account", headers=fresh).json()["email"] == "new@example.com"
    assert client.get("/api/account", headers=laptop).status_code == 401
    with Session(engine) as session:
        trail = session.scalars(
            select(FencerProfileAudit).where(FencerProfileAudit.field == "email")
        ).one()
        assert (trail.old_value, trail.new_value) == ("me@example.com", "new@example.com")
        assert session.scalars(select(PendingEmailChange)).all() == []

    notice = mailbox.sent[-1]
    assert notice["To"] == "me@example.com"
    assert "new@example.com" in text(notice)
    assert "privacy@" in text(notice)


def test_a_link_works_once(client, auth_headers, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    ask(client, me, "new@example.com")
    key = key_of(mailbox.sent[-1])
    assert client.post("/api/account/email/confirm", json={"key": key}).status_code == 200
    again = client.post("/api/account/email/confirm", json={"key": key})
    assert again.status_code == 410
    assert again.json()["detail"] == "email_change_invalid"


def test_the_latest_request_wins(client, auth_headers, engine, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    ask(client, me, "first@example.com")
    first = key_of(mailbox.sent[-1])
    ask(client, me, "second@example.com")
    second = key_of(mailbox.sent[-1])

    assert client.post("/api/account/email/inspect", json={"key": first}).status_code == 410
    assert client.post("/api/account/email/inspect", json={"key": second}).json() == {
        "email": "second@example.com"
    }
    assert client.post("/api/account/email/confirm", json={"key": second}).status_code == 200
    assert address_of(engine, "Me") == "second@example.com"


def test_an_expired_link_changes_nothing(client, auth_headers, engine, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    ask(client, me, "new@example.com")
    key = key_of(mailbox.sent[-1])
    with Session(engine) as session:
        change = session.scalars(select(PendingEmailChange)).one()
        change.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    assert client.post("/api/account/email/confirm", json={"key": key}).status_code == 410
    assert address_of(engine, "Me") == "me@example.com"


def test_an_address_taken_meanwhile_stays_with_its_taker(client, auth_headers, engine, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    ask(client, me, "new@example.com")
    key = key_of(mailbox.sent[-1])
    auth_headers(email="new@example.com", name="Quicker", role=Role.FENCER)

    taken = client.post("/api/account/email/confirm", json={"key": key})
    assert taken.status_code == 409
    assert taken.json()["detail"] == "email_taken"
    assert address_of(engine, "Me") == "me@example.com"
    assert address_of(engine, "Quicker") == "new@example.com"


def test_the_helper_signs_in_on_the_new_address(client, auth_headers):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    change_email(client, me, "new@example.com")
    login = client.post("/api/auth/login", json={"email": "new@example.com", "password": PASSWORD})
    assert login.status_code == 200
    old = client.post("/api/auth/login", json={"email": "me@example.com", "password": PASSWORD})
    assert old.status_code == 401
