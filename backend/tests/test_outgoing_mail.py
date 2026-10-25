"""Outgoing mail is queued with its cause and delivered after the commit
(spec outgoing-mail)."""

import smtplib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import bank, emails, outgoing, scheduler
from app.db import get_session
from app.mail import build_message, get_mailer
from app.main import app
from app.models import OutgoingMail, Registration
from tests.conftest import enable_payments, publish


class Transport:
    """A transport that refuses while `down` and records what it accepted."""

    def __init__(self):
        self.sent = []
        self.down = False

    def send(self, message):
        if self.down:
            raise smtplib.SMTPServerDisconnected("connection refused")
        self.sent.append(message)


@pytest.fixture
def transport():
    mailer = Transport()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def db_session():
    return next(app.dependency_overrides[get_session]())


def tournament(client, organizer, slug="cup"):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": slug.title(), "date": "2099-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, slug)
    client.patch(
        f"/api/tournaments/{slug}",
        json={"reservation_validity_days": 7, "reminder_day": 5},
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    publish(client, organizer, slug)


def register(client, headers, slug="cup"):
    response = client.post(
        f"/api/tournaments/{slug}/register", json={"disciplines": ["LS"]}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response


def last_id() -> int:
    return db_session().scalar(select(func.max(OutgoingMail.id))) or 0


def rows_after(start: int) -> list[OutgoingMail]:
    """The messages queued after `start`; the signups a test makes queue their
    verification mail beside the ones it is about."""
    return list(
        db_session()
        .scalars(select(OutgoingMail).where(OutgoingMail.id > start).order_by(OutgoingMail.id))
        .all()
    )


def jan_registers(client, auth_headers) -> int:
    """Jan registers on `cup`; returns the id his messages are queued after."""
    jan = auth_headers(email="jan@example.com", name="Jan")
    start = last_id()
    register(client, jan)
    return start


def test_transport_down_registration_still_succeeds_and_mail_follows(
    client, auth_headers, transport
):
    tournament(client, auth_headers())
    transport.down = True

    start = jan_registers(client, auth_headers)

    assert transport.sent == []
    [row] = rows_after(start)
    assert row.sent_at is None
    assert row.attempts == 1
    assert "SMTPServerDisconnected" in (row.last_error or "")
    assert row.raw is not None

    transport.down = False
    assert outgoing.deliver_pending(db_session(), transport) == 1
    assert [m["To"] for m in transport.sent] == ["jan@example.com"]
    [row] = rows_after(start)
    assert row.sent_at is not None
    assert row.raw is None


def test_a_delivered_message_is_not_resent(client, auth_headers, transport):
    tournament(client, auth_headers())
    start = jan_registers(client, auth_headers)
    assert len(transport.sent) == 1

    assert outgoing.deliver_pending(db_session(), transport) == 0
    assert len(transport.sent) == 1
    assert all(row.raw is None for row in rows_after(start))


def test_a_rolled_back_action_queues_nothing(client, transport):
    start = last_id()
    session = db_session()
    dependency = outgoing.queued_mailer(session, transport)
    mailer = next(dependency)
    # the handler composes a message and then fails; FastAPI throws the
    # exception into the dependency and closes the session uncommitted
    mailer.send(build_message("jan@example.com", "squire@example.com", "s", "b"))
    with pytest.raises(HTTPException):
        dependency.throw(HTTPException(status_code=409))
    session.rollback()

    assert rows_after(start) == []
    assert transport.sent == []


def test_a_claimed_row_is_delivered_once(client, auth_headers, transport):
    tournament(client, auth_headers())
    transport.down = True
    start = jan_registers(client, auth_headers)
    transport.down = False
    [row] = rows_after(start)

    # one delivery holds the claim; a second arriving meanwhile backs off
    assert outgoing._claim(db_session(), row.id, datetime.now(UTC))
    assert outgoing.deliver_pending(db_session(), transport) == 0
    assert transport.sent == []


def test_a_message_past_the_budget_is_given_up_and_scrubbed(client, auth_headers, transport):
    tournament(client, auth_headers())
    transport.down = True
    start = jan_registers(client, auth_headers)
    session = db_session()
    [row] = session.scalars(select(OutgoingMail).where(OutgoingMail.id > start)).all()
    row.created_at = datetime.now(UTC) - timedelta(hours=49)
    session.commit()

    assert outgoing.deliver_pending(session, transport) == 0
    [row] = rows_after(start)
    assert row.failed_at is not None
    assert row.raw is None
    assert row.sent_at is None


@pytest.fixture
def ticking(engine, monkeypatch, transport):
    """`run_tick` with its real session factory pointed at the test engine."""
    monkeypatch.setattr(
        scheduler,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )
    monkeypatch.setattr(scheduler, "get_mailer", lambda: transport)
    monkeypatch.setattr(bank, "get_fio_client", lambda: None)


def test_a_pass_failing_mid_batch_leaves_no_partial_state(
    client, auth_headers, transport, ticking, monkeypatch
):
    organizer = auth_headers()
    tournament(client, organizer, "cup")
    tournament(client, organizer, "open")
    fencers = [auth_headers(email=f"f{i}@example.com", name=f"F{i}") for i in range(3)]
    for fencer in fencers:
        register(client, fencer, "cup")
    register(client, fencers[0], "open")
    session = db_session()
    for registration in session.scalars(select(Registration)).all():
        registration.registered_at = datetime.now(UTC) - timedelta(days=6)
        registration.expires_at = registration.registered_at + timedelta(days=7)
    session.commit()
    transport.sent.clear()

    real = emails.send_payment_reminder
    calls = {"cup": 0}

    def third_on_cup_raises(mailer, tournament, fencer, registration):
        if tournament.slug == "cup":
            calls["cup"] += 1
            if calls["cup"] == 3:
                raise RuntimeError("composition failed")
        real(mailer, tournament, fencer, registration)

    monkeypatch.setattr(emails, "send_payment_reminder", third_on_cup_raises)
    scheduler.run_tick()

    registrations = db_session().scalars(select(Registration)).all()
    on_cup = [r for r in registrations if r.tournament.slug == "cup"]
    on_open = [r for r in registrations if r.tournament.slug == "open"]
    assert all(r.reminded_at is None for r in on_cup)
    assert all(r.reminded_at is not None for r in on_open)
    assert [m["To"] for m in transport.sent] == ["f0@example.com"]

    monkeypatch.setattr(emails, "send_payment_reminder", real)
    scheduler.run_tick()
    assert sorted(m["To"] for m in transport.sent) == [
        "f0@example.com",
        "f0@example.com",
        "f1@example.com",
        "f2@example.com",
    ]
