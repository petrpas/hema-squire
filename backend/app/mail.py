"""Outgoing email. The Mailer protocol is the swap point: OutboxMailer (dev)
serializes each message into an outbox directory and logs it; a real SMTP or
provider-backed mailer replaces it via the get_mailer dependency later."""

import logging
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


class Mailer(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class OutboxMailer:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def send(self, message: EmailMessage) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path = self.directory / f"{stamp}.eml"
        path.write_bytes(bytes(message))
        logger.info("email to %s (%s) -> %s", message["To"], message["Subject"], path)


def build_message(
    to: str, sender: str, subject: str, body: str, qr: bytes | None = None
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if qr is not None:
        message.add_attachment(qr, maintype="image", subtype="png", filename="platba-qr.png")
    return message


_outbox = OutboxMailer(settings.email_outbox_dir)


def get_mailer() -> Mailer:
    return _outbox
