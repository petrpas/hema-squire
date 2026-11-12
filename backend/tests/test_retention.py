"""Storage limitation (spec data-retention): finished mail and expired tokens
go by age, and a tournament twelve months past its date loses its bank text,
contact addresses and free-text details, while every figure and every roster
reads as before."""

import datetime
from datetime import UTC, timedelta

import pytest
from sqlalchemy import func, select

from app import retention
from app.config import settings
from app.importer import get_import_parser
from app.mail import get_mailer
from app.main import app
from app.models import (
    BankTransaction,
    Fencer,
    ImportDecision,
    ImportedRow,
    ManualRow,
    OutgoingMail,
    PasswordReset,
    PendingSignup,
    Registration,
    Tournament,
)
from tests.conftest import import_statement, outcome, post_restore
from tests.test_export_json import fresh_deployment
from tests.test_import import FakeParser, upload
from tests.test_matching import db_session, enroll, make_csv, setup

pytestmark = pytest.mark.usefixtures("before_manual_entry_registers")

NOW = datetime.datetime(2099, 6, 1, 12, tzinfo=UTC)
# the free-text fields a fencer-list or export row carries
FREE = {"email", "notes", "accommodation", "contact_email"}


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


@pytest.fixture
def writes(monkeypatch):
    monkeypatch.setattr(settings, "retention_writes_enabled", True)


@pytest.fixture
def parser():
    fake = FakeParser()
    app.dependency_overrides[get_import_parser] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_import_parser, None)


def statement(vs) -> bytes:
    return make_csv([f"7001;12.08.2026;1000,00;CZK;{vs};;;startovné Jan;Jan Novák;123/0800"])


def cup(session) -> Tournament:
    return session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()


def without_free_text(rows: list[dict]) -> list[dict]:
    return [{key: value for key, value in row.items() if key not in FREE} for row in rows]


def snapshot(client, organizer) -> dict:
    """Everything a pruned tournament must still say the same way."""
    tables = client.get("/api/tournaments/cup/export/tables", headers=organizer).json()
    return {
        "sheet": without_free_text(
            client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
        ),
        "fencers": without_free_text(
            client.get("/api/tournaments/cup/export/table", headers=organizer).json()["rows"]
        ),
        "tabs": tables,
        "revenue": client.get("/api/tournaments/cup/export/revenue", headers=organizer).json(),
        "summary": client.get("/api/tournaments/cup/export/summary", headers=organizer).json(),
        "entrants": client.get("/api/tournaments/cup/entrants").json(),
    }


@pytest.fixture
def held_cup(client, auth_headers, mailbox, parser):
    """A paid registration with a contact address and notes, a matched bank
    row with payer text, a manual row and an imported table — then the
    tournament is moved thirteen months into the past."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_statement(client, organizer, statement(vs))
    assert upload(client, organizer).status_code == 202
    outcome(client, organizer)

    session = db_session()
    tournament = cup(session)
    registration = session.scalars(select(Registration).where(Registration.vs == vs)).one()
    registration.contact_email = "club@example.com"
    registration.notes = "arrives Saturday"
    registration.accommodation = "gym floor"
    organizer_id = session.scalars(select(Fencer.id).order_by(Fencer.id)).first()
    assert organizer_id is not None
    session.add(
        ManualRow(
            tournament_id=tournament.id,
            name="Eva Ručně",
            email="eva@example.com",
            notes="pays at the venue",
            registered_at=NOW,
            disciplines=["LS"],
            created_by=organizer_id,
        )
    )
    session.commit()
    tournament.date = retention.cutoff(datetime.datetime.now(UTC).date()) - timedelta(days=30)
    session.commit()
    return organizer, vs


def test_pruning_removes_the_text_and_leaves_every_figure_and_roster(
    client, held_cup, writes, mailbox, parser
):
    organizer, vs = held_cup
    before = snapshot(client, organizer)

    session = db_session()
    retention.run_pass(session)

    session = db_session()
    bank_row = session.scalars(select(BankTransaction)).one()
    assert (bank_row.payer_name, bank_row.payer_account, bank_row.message) == (None, None, None)
    # what money is reconciled from stays
    assert (bank_row.vs, bank_row.amount_cents, bank_row.external_id) == (vs, 100_000, "7001")
    assert bank_row.matched_registration_id is not None

    registration = session.scalars(select(Registration).where(Registration.vs == vs)).one()
    assert (registration.contact_email, registration.notes, registration.accommodation) == (
        None,
        None,
        None,
    )
    manual = session.scalars(select(ManualRow)).one()
    assert (manual.name, manual.email, manual.notes) == ("Eva Ručně", None, None)

    for row in session.scalars(select(ImportedRow)):
        assert not any("@" in str(value) for value in row.raw.values())
        assert row.raw["Poznámka / Note"] == ""
        assert row.raw["Jméno / Full Name"].strip()
    for decision in session.scalars(select(ImportDecision).where(ImportDecision.kind == "parse")):
        assert decision.payload["email"] is None
        assert decision.payload["notes"] is None
        assert decision.payload["name"]

    assert cup(session).personal_data_pruned_at is not None
    assert snapshot(client, organizer) == before


def test_a_pruned_tournament_takes_nothing_back_in(client, held_cup, writes, mailbox, parser):
    organizer, vs = held_cup
    retention.run_pass(db_session())
    rows_before = db_session().scalar(select(func.count()).select_from(ImportedRow))

    import_statement(client, organizer, statement(vs))
    upload(client, organizer)
    outcome(client, organizer)

    session = db_session()
    bank_row = session.scalars(select(BankTransaction)).one()
    assert bank_row.payer_name is None and bank_row.message is None
    assert session.scalar(select(func.count()).select_from(ImportedRow)) == rows_before


def test_a_pruned_tournament_exports_and_restores(
    client, held_cup, writes, auth_headers, mailbox, parser
):
    organizer, _ = held_cup
    retention.run_pass(db_session())

    response = client.get("/api/tournaments/cup/export/json", headers=organizer)
    assert response.status_code == 200
    # the pruned values; an account's own address is its login and travels
    # with the document, which restores fencers by it
    for pruned in ("club@example.com", "eva@example.com", "alex@example.com", "startovné"):
        assert pruned not in response.text

    def names(http, headers) -> list[str]:
        rows = http.get("/api/tournaments/cup/sheet", headers=headers).json()["rows"]
        return [row["name"] for row in rows]

    before = names(client, organizer)
    new_organizer, restore_client = fresh_deployment(client, auth_headers)
    restored = post_restore(restore_client, new_organizer, response.json())
    assert restored.status_code == 201, restored.text
    # a restore arrives as a draft, so the fencer list is what can be compared
    assert names(restore_client, new_organizer) == before
    assert "Eva Ručně" in before


def test_a_second_pass_changes_nothing(client, held_cup, writes, mailbox, parser):
    retention.run_pass(db_session())
    session = db_session()
    tournament = cup(session)
    stamped = tournament.personal_data_pruned_at

    assert retention.due_tournaments(session, datetime.datetime.now(UTC).date()) == []
    # even run again by hand, there is nothing left to take
    counts = retention.prune_tournament(session, tournament, NOW)
    assert sum(counts.values()) == 0
    session.rollback()
    assert cup(db_session()).personal_data_pruned_at == stamped


def test_a_tournament_inside_its_year_is_left_alone(client, held_cup, writes, mailbox, parser):
    session = db_session()
    cup(session).date = datetime.datetime.now(UTC).date() - timedelta(days=300)
    session.commit()

    retention.run_pass(db_session())

    session = db_session()
    assert session.scalars(select(BankTransaction)).one().payer_name == "Jan Novák"
    assert cup(session).personal_data_pruned_at is None


def test_with_writes_disabled_nothing_changes(client, held_cup, mailbox, parser, caplog):
    assert settings.retention_writes_enabled is False
    caplog.set_level("INFO", logger="app.retention")

    retention.run_pass(db_session())

    session = db_session()
    assert session.scalars(select(BankTransaction)).one().payer_name == "Jan Novák"
    assert cup(session).personal_data_pruned_at is None
    assert "would change" in caplog.text and "bank_rows 1" in caplog.text


# ------------------------------------------------------------------ by age


def mail(session, created_at=NOW, **stamps) -> OutgoingMail:
    row = OutgoingMail(
        created_at=created_at, recipient="a@example.com", subject="s", raw=b"x", **stamps
    )
    session.add(row)
    return row


def test_finished_mail_ages_out_and_waiting_mail_stays(client, writes):
    session = db_session()
    old_sent = mail(session, sent_at=NOW - timedelta(days=31))
    old_failed = mail(session, failed_at=NOW - timedelta(days=31))
    recent = mail(session, sent_at=NOW - timedelta(days=29))
    # waiting since long ago and still being retried
    waiting = mail(session, created_at=NOW - timedelta(days=90), attempts=7)
    session.commit()
    kept = {recent.id, waiting.id}
    gone = {old_sent.id, old_failed.id}

    retention.run_pass(db_session(), NOW)

    ids = set(db_session().scalars(select(OutgoingMail.id)))
    assert kept <= ids
    assert not gone & ids


def test_expired_signups_and_resets_go(client, writes, auth_headers):
    auth_headers(email="owner@example.com")
    session = db_session()
    fencer_id = session.scalars(select(Fencer.id)).first()
    assert fencer_id is not None
    for key, expires in (
        ("a" * 64, NOW - timedelta(hours=1)),
        ("b" * 64, NOW + timedelta(hours=1)),
    ):
        session.add(
            PendingSignup(
                email=f"{key[0]}@example.com",
                password_hash="x",
                display_name="X",
                key_hash=key,
                created_at=NOW - timedelta(days=1),
                expires_at=expires,
            )
        )
    session.add(
        PasswordReset(
            fencer_id=fencer_id,
            key_hash="c" * 64,
            created_at=NOW - timedelta(days=1),
            expires_at=NOW - timedelta(minutes=1),
        )
    )
    session.commit()

    retention.run_pass(db_session(), NOW)

    session = db_session()
    assert list(session.scalars(select(PendingSignup.email))) == ["b@example.com"]
    assert session.scalar(select(func.count()).select_from(PasswordReset)) == 0


# --------------------------------------------------------------- the scrub


def test_a_rule_that_wrote_an_address_loses_it():
    """An edit rule would write the address back on every replay."""
    payload = {"field": "email", "value": "new@example.com", "base": "old@example.com"}
    scrubbed, changed = retention._scrub(payload, frozenset())
    assert changed
    assert scrubbed == {"field": "email", "value": None, "base": None}

    name_edit = {"field": "name", "value": "Jan", "base": "Jna"}
    assert retention._scrub(name_edit, frozenset()) == (name_edit, False)


def test_an_address_inside_free_text_is_cut_out():
    scrubbed, changed = retention._scrub(
        {"Comment": "write to jan@example.com please"}, frozenset()
    )
    assert changed
    assert scrubbed == {"Comment": "write to  please"}


def test_the_year_ends_on_the_same_date_and_survives_a_leap_day():
    assert retention.cutoff(datetime.date(2099, 6, 1)) == datetime.date(2098, 6, 1)
    assert retention.cutoff(datetime.date(2096, 2, 29)) == datetime.date(2095, 2, 28)
