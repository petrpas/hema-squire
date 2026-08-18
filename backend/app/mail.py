"""Outgoing email. The Mailer protocol is the swap point: OutboxMailer (dev)
serializes each message into an outbox directory and logs it; SmtpMailer
delivers for real, and get_mailer picks between them on configuration."""

import logging
import smtplib
import ssl
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


class SmtpMailer:
    """Delivery over STARTTLS. The app knows nothing about the provider beyond
    host, port and credentials, so any transactional endpoint fits."""

    def __init__(self, host: str, port: int = 587, user: str = "", password: str = ""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def send(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)
        logger.info("email to %s (%s) sent via %s", message["To"], message["Subject"], self.host)


def build_message(
    to: str,
    sender: str,
    subject: str,
    body: str,
    qr: bytes | None = None,
    qr_eur: bytes | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if qr is not None:
        message.add_attachment(qr, maintype="image", subtype="png", filename="platba-qr.png")
    # a tournament that also takes EUR sends two QRs; the filenames distinguish
    # them so a payer picks the currency deliberately
    if qr_eur is not None:
        message.add_attachment(
            qr_eur, maintype="image", subtype="png", filename="platba-qr-eur.png"
        )
    return message


_outbox = OutboxMailer(settings.email_outbox_dir)


def get_mailer() -> Mailer:
    """Configuration presence decides, not a mode flag: if an SMTP host is set,
    mail is real. Read per call so a test can set the host and see the switch."""
    if settings.smtp_host:
        return SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
        )
    return _outbox
