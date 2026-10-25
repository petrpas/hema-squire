"""An account exists only once its address is verified, and a verified signup
takes over the record without credentials on its address (spec
fencer-accounts)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.mail import get_mailer
from app.main import app
from app.models import Fencer, FencerProfileAudit, PendingSignup, Registration
from tests.conftest import verification_key
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


BODY = {"email": "eva@example.com", "password": "correct-horse", "display_name": "Eva Malá"}


def sign_up(client, **overrides):
    return client.post("/api/auth/signup", json=BODY | overrides)


def login(client, password="correct-horse"):
    return client.post("/api/auth/login", json={"email": BODY["email"], "password": password})


def test_signup_creates_nothing_until_verified(client, mailbox):
    assert sign_up(client).status_code == 202
    assert db_session().scalar(select(Fencer).where(Fencer.email == BODY["email"])) is None
    assert len(mailbox.sent) == 1
    assert mailbox.sent[0]["To"] == BODY["email"]


def test_pending_signup_is_told_so_at_sign_in_and_only_with_its_password(client, mailbox):
    sign_up(client)
    refused = login(client)
    assert refused.status_code == 403
    assert refused.json()["detail"] == "email_not_verified"
    # a stranger guessing at the address learns nothing
    assert login(client, password="wrong-password").status_code == 401


def test_following_the_link_signs_in_and_lands_where_signup_started(client, mailbox):
    sign_up(client, return_to="/t/cup")
    verified = client.post("/api/auth/verify", json={"key": verification_key(mailbox.sent[-1])})
    assert verified.status_code == 200
    assert verified.json()["return_to"] == "/t/cup"
    headers = {"Authorization": f"Bearer {verified.json()['token']}"}
    assert client.get("/api/account", headers=headers).json()["display_name"] == "Eva Malá"
    assert login(client).status_code == 200


def test_return_to_must_be_a_path_of_this_application(client, mailbox):
    assert sign_up(client, return_to="//evil.example").status_code == 422
    assert sign_up(client, return_to="https://evil.example").status_code == 422


def test_a_link_works_once(client, mailbox):
    sign_up(client)
    key = verification_key(mailbox.sent[-1])
    assert client.post("/api/auth/verify", json={"key": key}).status_code == 200
    again = client.post("/api/auth/verify", json={"key": key})
    assert again.status_code == 410
    assert len(db_session().scalars(select(Fencer).where(Fencer.email == BODY["email"])).all()) == 1


def test_a_link_expires_after_48_hours(client, mailbox):
    sign_up(client)
    key = verification_key(mailbox.sent[-1])
    session = db_session()
    pending = session.scalars(select(PendingSignup)).one()
    pending.expires_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()
    assert client.post("/api/auth/verify", json={"key": key}).status_code == 410


def test_resending_replaces_the_link(client, mailbox):
    sign_up(client)
    first = verification_key(mailbox.sent[-1])
    resent = client.post(
        "/api/auth/resend-verification",
        json={"email": BODY["email"], "password": "correct-horse"},
    )
    assert resent.status_code == 204
    second = verification_key(mailbox.sent[-1])
    assert client.post("/api/auth/verify", json={"key": first}).status_code == 410
    assert client.post("/api/auth/verify", json={"key": second}).status_code == 200


def test_the_latest_signup_wins(client, mailbox):
    sign_up(client, password="first-password")
    first = verification_key(mailbox.sent[-1])
    sign_up(client, password="second-password")
    second = verification_key(mailbox.sent[-1])
    assert client.post("/api/auth/verify", json={"key": first}).status_code == 410
    assert client.post("/api/auth/verify", json={"key": second}).status_code == 200
    assert login(client, password="second-password").status_code == 200
    assert login(client, password="first-password").status_code == 401


def test_an_accounts_address_is_still_refused(client, auth_headers, mailbox):
    auth_headers(email=BODY["email"], name="Eva Malá")
    refused = sign_up(client)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "email_already_registered"
    assert mailbox.sent == []


# a roster-issued record, as an automatic tournament could take one before
# `manual-entry-registers`
@pytest.mark.usefixtures("before_manual_entry_registers")
def test_verification_takes_over_a_roster_issued_record(client, auth_headers, mailbox):
    """The 409 a roster-enrolled fencer met at signup, now the takeover."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Eva Malá", BODY["email"])])
    issue(client, organizer)
    session = db_session()
    record = session.scalar(select(Fencer).where(Fencer.email == BODY["email"]))
    record.hr_id = 10234
    session.commit()
    record_id = record.id
    registration_id = session.scalar(
        select(Registration.id).where(Registration.fencer_id == record_id)
    )

    assert sign_up(client, display_name="Eva Malá-Nová", language="cs").status_code == 202
    verified = client.post("/api/auth/verify", json={"key": verification_key(mailbox.sent[-1])})
    assert verified.status_code == 200

    session = db_session()
    fencers = session.scalars(select(Fencer).where(Fencer.email == BODY["email"])).all()
    assert [f.id for f in fencers] == [record_id]
    taken = fencers[0]
    assert taken.password_hash is not None
    assert taken.display_name == "Eva Malá-Nová"
    assert taken.language == "cs"
    assert taken.hr_id == 10234  # a bound record keeps its binding
    assert session.get(Registration, registration_id).fencer_id == record_id
    audited = {e.field for e in session.scalars(select(FencerProfileAudit)).all()}
    assert {"display_name", "language"} <= audited
    assert login(client).status_code == 200


# a roster-issued record, as an automatic tournament could take one before
# `manual-entry-registers`
@pytest.mark.usefixtures("before_manual_entry_registers")
def test_takeover_binds_the_signups_profile_where_the_record_has_none(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novák", "jan@example.com")])
    issue(client, organizer)
    client.post(
        "/api/auth/signup",
        json={"email": "jan@example.com", "password": "correct-horse", "hr_id": 10234},
    )
    client.post("/api/auth/verify", json={"key": verification_key(mailbox.sent[-1])})
    record = db_session().scalar(select(Fencer).where(Fencer.email == "jan@example.com"))
    assert record.hr_id == 10234
    assert record.nationality == "CZE"
