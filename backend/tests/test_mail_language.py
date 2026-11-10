"""Mail follows its recipient's language (spec `localization`, Communication
language vs UI language).

Enumerates every tournament `send_*` rather than listing them, so a send added
later joins by existing: one that still reads the tournament's language fails
here, and one taking an argument nobody has supplied fails here too, which is
the prompt to add it to `ARGUMENTS`."""

import datetime
import inspect
from types import SimpleNamespace

import pytest

from app import emails
from app.i18n import t
from app.mail import get_mailer
from app.main import app
from app.models import Fencer, Registration
from app.substitution import Identity, Prepared
from tests.test_mail_content import (
    CollectingMailer,
    body,
    register,
    the_registration,
    tournament,
)


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


ACCOUNT_MAIL = {"send_signup_verification", "send_password_reset", "send_password_changed"}

TOURNAMENT_SENDS = sorted(
    name
    for name, function in inspect.getmembers(emails, inspect.isfunction)
    if name.startswith("send_") and name not in ACCOUNT_MAIL
)


def _arguments(mailer: CollectingMailer, registration: Registration) -> dict:
    """What each parameter a send may require is given, by name."""
    fencer = registration.fencer
    return {
        "mailer": mailer,
        "tournament": registration.tournament,
        "fencer": fencer,
        "registration": registration,
        "which": "local",
        "received_cents": 50000,
        "discipline_name": "LS",
        "disciplines": "LS",
        "moved": [("LS", 1)],
        "moved_teams": [],
        "team": SimpleNamespace(name="Tým A", discipline=SimpleNamespace(name="LS")),
        # a cancelled team is named by what it was, read off the row before it
        # goes (`emails.send_team_cancelled`)
        "team_name": "Tým A",
        "teams": [],
        "deadline": datetime.date(2099, 12, 1),
        "note": None,
        "prepared": Prepared(
            substitute=fencer,
            contact=None,
            previous=Identity(name="Old", hr_id=None, nationality=None, club=None, email=None),
            registration=registration,
        ),
    }


def _send(name: str, registration: Registration, language: str) -> list:
    registration.fencer.language = language
    mailer = CollectingMailer()
    supplied = _arguments(mailer, registration)
    function = getattr(emails, name)
    required = {
        parameter: supplied[parameter]
        for parameter, spec in inspect.signature(function).parameters.items()
        if spec.default is inspect.Parameter.empty
    }
    function(**required)
    assert mailer.sent, f"{name} sent nothing; the setup no longer reaches it"
    return mailer.sent


def _footer(language: str) -> str:
    return t("email.tournamentLink", language, link="")


@pytest.mark.parametrize("name", TOURNAMENT_SENDS)
def test_an_english_reader_of_a_czech_tournament_is_written_to_in_english(
    client, auth_headers, mailbox, name
):
    tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))
    registration = the_registration()
    assert registration.tournament.language == "cs"

    czech = _send(name, registration, "cs")
    english = _send(name, registration, "en")

    for in_czech, in_english in zip(czech, english, strict=True):
        assert in_english["Subject"] != in_czech["Subject"]
        text = body(in_english)
        assert _footer("en") in text
        assert _footer("cs") not in text


@pytest.mark.parametrize("name", TOURNAMENT_SENDS)
def test_an_unbundled_language_reads_the_tournaments(client, auth_headers, mailbox, name):
    tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))
    registration = the_registration()

    czech = _send(name, registration, "cs")
    unbundled = _send(name, registration, "xx")

    for in_czech, fallen_back in zip(czech, unbundled, strict=True):
        assert fallen_back["Subject"] == in_czech["Subject"]
        assert body(fallen_back) == body(in_czech)


def test_a_composed_team_line_follows_the_message(client, auth_headers, mailbox):
    """The team label is built before the send; it is in the reader's language
    like the rest (spec `localization`, A composed line follows the message)."""
    tournament(client, auth_headers())
    register(client, auth_headers(email="jan@example.com", name="Jan"))
    registration = the_registration()

    [message] = _send("send_team_promoted", registration, "en")
    expected = t("email.promoted.team", "en", team="Tým A", discipline="LS")
    assert expected != t("email.promoted.team", "cs", team="Tým A", discipline="LS")
    assert expected in body(message)


def test_mail_language_falls_back_only_for_an_unbundled_locale():
    from app.models import Tournament

    czech = Tournament(language="cs")
    assert emails.mail_language(czech, Fencer(language="en")) == "en"
    assert emails.mail_language(czech, Fencer(language="xx")) == "cs"
