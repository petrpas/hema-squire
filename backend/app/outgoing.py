"""Outgoing mail queued with the action that causes it (spec `outgoing-mail`,
design fix-email-findings D8).

Every `emails.send_*` takes "a mailer". Handed a `QueuedMailer`, it writes the
message into the caller's session instead of talking to a transport, so the
message commits or rolls back with its cause. `deliver_pending` hands committed
rows to the real transport (`mail.get_mailer`) afterwards and records what
happened; a failure stays on the row and the next scheduler pass retries it.

The request path gets this through `queued_mailer`, a dependency whose
teardown commits and delivers. The scheduler wraps its own session
(`scheduler.run_tick`)."""

from __future__ import annotations

import email
import email.policy
import logging
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Annotated

from fastapi import Depends
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.db import get_session
from app.mail import Mailer, get_mailer
from app.models import OutgoingMail

logger = logging.getLogger(__name__)

# a message older than this describes a state the fencer has most likely moved
# past; it matches the expiry grace (design D8, Retry budget)
RETRY_BUDGET = timedelta(hours=48)
# a claim not finished within this is taken to have died with its process
CLAIM_LEASE = timedelta(minutes=10)


def _now() -> datetime:
    return datetime.now(UTC)


class QueuedMailer:
    """A `Mailer` that queues into `session` rather than sending. The rows are
    the caller's to commit; `queued` names them so the caller can deliver
    exactly what it queued."""

    def __init__(self, session: Session):
        self.session = session
        self.queued: list[OutgoingMail] = []

    def send(self, message: EmailMessage) -> None:
        row = OutgoingMail(
            created_at=_now(),
            recipient=str(message["To"]),
            subject=str(message["Subject"])[:500],
            raw=bytes(message),
            attempts=0,
        )
        self.session.add(row)
        self.queued.append(row)


def _claim(session: Session, row_id: int, now: datetime) -> bool:
    """Take the row for delivery, atomically: a request's teardown and a
    scheduler pass must never both send it."""
    result = session.execute(
        update(OutgoingMail)
        .where(
            OutgoingMail.id == row_id,
            OutgoingMail.sent_at.is_(None),
            OutgoingMail.failed_at.is_(None),
            or_(OutgoingMail.claimed_at.is_(None), OutgoingMail.claimed_at < now - CLAIM_LEASE),
        )
        .values(claimed_at=now)
        # the claimed row is refreshed by the caller; evaluating the criteria in
        # Python would compare SQLite's naive datetimes against an aware `now`
        .execution_options(synchronize_session=False)
    )
    session.commit()
    return getattr(result, "rowcount", 0) == 1


def _deliver_one(session: Session, transport: Mailer, row: OutgoingMail) -> bool:
    now = _now()
    if not _claim(session, row.id, now):
        return False
    session.refresh(row)
    raw = row.raw
    if raw is None:  # scrubbed by a delivery that finished between select and claim
        return False
    message = email.message_from_bytes(raw, policy=email.policy.default)
    row.attempts += 1
    try:
        if not isinstance(message, EmailMessage):  # the default policy always builds one
            raise TypeError("a queued message did not parse back into an EmailMessage")
        transport.send(message)
    except Exception as exc:
        row.last_error = f"{type(exc).__name__}: {exc}"[:1000]
        row.claimed_at = None
        created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=UTC)
        if now - created > RETRY_BUDGET:
            row.failed_at = now
            row.raw = None
            logger.error(
                "giving up on email to %s (%s) after %d attempts: %s",
                row.recipient,
                row.subject,
                row.attempts,
                row.last_error,
            )
        else:
            logger.warning(
                "email to %s (%s) not delivered, will retry: %s",
                row.recipient,
                row.subject,
                row.last_error,
            )
        session.commit()
        return False
    row.sent_at = _now()
    row.raw = None
    session.commit()
    return True


def deliver_pending(
    session: Session, transport: Mailer, rows: list[OutgoingMail] | None = None
) -> int:
    """Hand committed messages to the transport; `rows` limits it to those, and
    `None` means every message still waiting. Never raises for a failed send:
    the failure is recorded on the row and a later pass retries it. Returns how
    many were sent."""
    if rows is None:
        rows = list(
            session.scalars(
                select(OutgoingMail)
                .where(OutgoingMail.sent_at.is_(None), OutgoingMail.failed_at.is_(None))
                .order_by(OutgoingMail.id)
            ).all()
        )
    return sum(_deliver_one(session, transport, row) for row in rows)


def queued_mailer(
    session: Annotated[Session, Depends(get_session)],
    transport: Annotated[Mailer, Depends(get_mailer)],
) -> Generator[QueuedMailer]:
    """The request's mailer. The teardown runs only when the handler returned:
    an exception propagates through the `yield`, and the session's rollback
    then discards whatever was queued. Otherwise it commits — which also
    persists a message composed after the handler's own commit, the order most
    handlers send in — and delivers what this request queued.

    Declared with `scope="function"` at the use site, so the teardown runs
    before the response is sent and a test reading its mailbox right after the
    call sees the message."""
    mailer = QueuedMailer(session)
    yield mailer
    if mailer.queued:
        session.commit()
        deliver_pending(session, transport, mailer.queued)


QueuedMailerDep = Annotated[Mailer, Depends(queued_mailer, scope="function")]
