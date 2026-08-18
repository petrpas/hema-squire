"""Production email is delivered (deployment spec). Selection is by configuration
presence: a set SMTP host means real delivery, an unset one keeps the outbox that
every dev checkout uses.
"""

from email.message import EmailMessage

from app.config import settings
from app.mail import OutboxMailer, SmtpMailer, get_mailer


def test_outbox_is_the_default(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    assert isinstance(get_mailer(), OutboxMailer)


def test_smtp_host_selects_real_delivery(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.net")
    monkeypatch.setattr(settings, "smtp_port", 2525)
    monkeypatch.setattr(settings, "smtp_user", "squire")
    monkeypatch.setattr(settings, "smtp_password", "secret")

    mailer = get_mailer()
    assert isinstance(mailer, SmtpMailer)
    assert (mailer.host, mailer.port, mailer.user) == ("smtp.example.net", 2525, "squire")


class _StubSmtp:
    """Records what SmtpMailer.send does to a connection."""

    instances: list[_StubSmtp] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in_as = None
        self.sent: list[EmailMessage] = []
        _StubSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in_as = (user, password)

    def send_message(self, message):
        self.sent.append(message)


def test_send_goes_over_starttls_after_login(monkeypatch):
    _StubSmtp.instances.clear()
    monkeypatch.setattr("app.mail.smtplib.SMTP", _StubSmtp)

    message = EmailMessage()
    message["To"] = "fencer@example.com"
    message["Subject"] = "Payment reminder"
    message.set_content("body")

    mailer = SmtpMailer(host="smtp.example.net", port=587, user="squire", password="secret")
    mailer.send(message)

    (connection,) = _StubSmtp.instances
    assert (connection.host, connection.port) == ("smtp.example.net", 587)
    assert connection.started_tls
    assert connection.logged_in_as == ("squire", "secret")
    assert [m["Subject"] for m in connection.sent] == ["Payment reminder"]


def test_send_without_credentials_skips_login(monkeypatch):
    _StubSmtp.instances.clear()
    monkeypatch.setattr("app.mail.smtplib.SMTP", _StubSmtp)

    message = EmailMessage()
    message["To"] = "fencer@example.com"
    message["Subject"] = "Reminder"
    message.set_content("body")

    SmtpMailer(host="smtp.example.net").send(message)

    (connection,) = _StubSmtp.instances
    assert connection.logged_in_as is None
    assert connection.sent
