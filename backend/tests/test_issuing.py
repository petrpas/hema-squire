"""Issuing registrations for a fencer list (spec `imported-registrations`).

A tournament whose fencers were imported cannot take a payment: matching
resolves through `Registration.vs` and there is none. These cover the action
that makes such a roster billable, and — at greater length than anything else
here — that doing so mails nobody. The rows describe people who registered
elsewhere, often a season ago and often already paid; a lifecycle clock started
on their behalf would tell them their reservation is about to expire.
"""

import io
from datetime import UTC, datetime, timedelta

import pytest
from conftest import outcome
from sqlalchemy import select

from app.dedup import MergeProposal, ThreeBands, default_merge, get_dedup_llm
from app.importer import ParsedFencer, get_import_parser
from app.mail import get_mailer
from app.main import app
from app.models import Fencer, Registration, RegistrationState
from tests.test_matching import db_session


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


class RosterParser:
    """Turns the CSV below into records, one per row, with no LLM."""

    def parse_batch(self, rows, disciplines, rentals):
        parsed = []
        for raw in rows:
            disciplines_in = [d for d in (raw["disciplines"] or "").split("|") if d]
            parsed.append(
                ParsedFencer(
                    registration_time=raw["when"],
                    name=raw["name"],
                    email=raw["email"] or None,
                    club=raw["club"] or None,
                    nationality="CZ",
                    hr_id=None,
                    disciplines=disciplines_in,
                    borrow=[r for r in (raw["borrow"] or "").split("|") if r],
                    after_party="Yes" if raw["afterparty"] == "y" else "No",
                    notes=None,
                    problems=None,
                )
            )
        return parsed


HEADER = "when,name,email,club,disciplines,borrow,afterparty\n"


def row(
    name, email, *, when="2026-04-01T10:00:00", disciplines="SA", borrow="", afterparty=""
):
    return f"{when},{name},{email},Klub,{disciplines},{borrow},{afterparty}\n"


def setup(client, organizer, *, fee=800, early_fee=None, early_until=None):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    body = {"slug": "SA", "weapon": "SA", "capacity": 20, "fee": fee}
    if early_fee is not None:
        body["fee_early"] = early_fee
    client.post("/api/tournaments/cup/disciplines", json=body, headers=organizer)
    client.post("/api/tournaments/cup/disciplines",
                json={"slug": "SB", "weapon": "SB", "capacity": 20, "fee": 500},
                headers=organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    if early_until is not None:
        client.patch(
            "/api/tournaments/cup",
            json={"early_bird_until": early_until},
            headers=organizer,
        )
    app.dependency_overrides[get_import_parser] = lambda: RosterParser()


def import_roster(client, organizer, rows):
    content = (HEADER + "".join(rows)).encode()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("roster.csv", io.BytesIO(content), "text/csv")},
        headers=organizer,
    )
    return outcome(client, organizer, "cup", "parse")


def issue(client, organizer):
    response = client.post("/api/tournaments/cup/import/issue", headers=organizer)
    assert response.status_code == 200, response.json()
    return response.json()


def sheet_rows(client, organizer):
    body = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return [r for r in body["rows"] if not r["_deleted"]]


def registrations():
    return db_session().scalars(select(Registration)).all()


# --- what issuing produces -------------------------------------------------


def test_a_roster_becomes_billable(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com"),
                                      row("Eva", "eva@example.com")])

    report = issue(client, organizer)

    assert report["issued"] == 2
    issued = registrations()
    assert len(issued) == 2
    assert all(r.vs is not None for r in issued)
    assert len({r.vs for r in issued}) == 2
    # what each owes now appears in the fencer list, which is the whole point
    rows = sheet_rows(client, organizer)
    assert {r["outstanding_amount"] for r in rows} == {"800.00"}


def test_issuing_shows_one_row_per_fencer_not_two(client, auth_headers, mailbox):
    """The registration stands in the row's place, under the row's own id — so
    the fencer keeps their fixed number and is listed once (spec etl-console,
    Fixed fencer number)."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    before = sheet_rows(client, organizer)
    assert len(before) == 1
    number, row_id = before[0]["number"], before[0]["id"]

    issue(client, organizer)

    after = sheet_rows(client, organizer)
    assert len(after) == 1
    assert after[0]["id"] == row_id
    assert after[0]["number"] == number
    assert after[0]["vs"] is not None


def test_a_fencer_record_is_created_without_an_account(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novák", "jan@example.com")])

    issue(client, organizer)

    fencer = db_session().scalar(
        select(Fencer).where(Fencer.email == "jan@example.com")
    )
    assert fencer is not None
    assert fencer.password_hash is None  # a record, not a login
    assert mailbox.sent == []  # and no invitation


def test_an_existing_fencer_is_reused_not_overwritten(client, auth_headers, mailbox):
    """The record may belong to someone with an account; their own name and club
    are theirs, not the roster's."""
    organizer = auth_headers()
    setup(client, organizer)
    account = auth_headers(email="eva@example.com", name="Eva Malá")
    assert account  # created through the ordinary signup
    before = db_session().scalar(select(Fencer).where(Fencer.email == "eva@example.com"))
    before_id, before_name = before.id, before.display_name

    import_roster(client, organizer, [row("EVA MALA TYPO", "eva@example.com")])
    issue(client, organizer)

    fencers = db_session().scalars(
        select(Fencer).where(Fencer.email == "eva@example.com")
    ).all()
    assert len(fencers) == 1
    assert fencers[0].id == before_id
    assert fencers[0].display_name == before_name


def test_an_unconfirmed_hr_match_is_not_claimed(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    # no organizer verdict has been reached on any match
    issue(client, organizer)

    fencer = db_session().scalar(select(Fencer).where(Fencer.email == "jan@example.com"))
    assert fencer.hr_id is None


# --- what it is worth ------------------------------------------------------


def test_priced_at_the_rows_own_moment(client, auth_headers, mailbox):
    """Early bird applies as it did when the fencer registered, not as it does
    on the day the organizer gets round to issuing."""
    organizer = auth_headers()
    setup(client, organizer, fee=800, early_fee=500, early_until="2026-05-01")
    import_roster(
        client,
        organizer,
        [
            row("Early", "early@example.com", when="2026-04-01T10:00:00"),
            row("Late", "late@example.com", when="2026-06-01T10:00:00"),
        ],
    )

    issue(client, organizer)

    totals = {r.fencer.email: r.total_amount for r in registrations()}
    assert totals["early@example.com"] == 500
    assert totals["late@example.com"] == 800


def test_extras_are_priced_with_the_disciplines(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"weapon_rental_fee": 100, "afterparty_fee": 250},
        headers=organizer,
    )
    import_roster(
        client,
        organizer,
        [row("Jan", "jan@example.com", disciplines="SA|SB", borrow="meč", afterparty="y")],
    )

    issue(client, organizer)

    assert registrations()[0].total_amount == 800 + 500 + 100 + 250


def test_a_later_fee_change_does_not_move_an_issued_total(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)
    assert registrations()[0].total_amount == 800

    client.patch(
        "/api/tournaments/cup/disciplines/SA", json={"fee": 2000}, headers=organizer
    )

    assert registrations()[0].total_amount == 800


def test_a_row_with_no_discipline_is_skipped_and_named(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [row("Jan", "jan@example.com"), row("Nada", "nada@example.com", disciplines="")],
    )

    report = issue(client, organizer)

    assert report["issued"] == 1
    assert [s["reason"] for s in report["skipped"]] == ["no_discipline"]
    assert report["skipped"][0]["name"] == "Nada"


def test_a_row_with_no_email_is_skipped(client, auth_headers, mailbox):
    """`Fencer.email` is the account identity and cannot be null, so such a row
    cannot become a registration until the organizer supplies one."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Anon", "")])

    report = issue(client, organizer)

    assert report["issued"] == 0
    assert [s["reason"] for s in report["skipped"]] == ["no_email"]


def test_two_rows_sharing_an_email_issue_once_and_say_so(client, auth_headers, mailbox):
    """One person entering several others is ordinary on a real roster — the
    pilot has one address covering three different fencers. `Fencer.email` is
    unique across the deployment and a fencer registers once per tournament, so
    only the first row can be issued, and the rest are named rather than
    silently dropped."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [row("Václav Pekárek", "divis@example.com"),
         row("Jindřich Pekárek", "divis@example.com")],
    )

    report = issue(client, organizer)

    assert report["issued"] == 1
    assert [s["reason"] for s in report["skipped"]] == ["email_taken"]
    assert report["skipped"][0]["name"] == "Jindřich Pekárek"


def test_capacity_does_not_apply_to_an_issued_roster(client, auth_headers, mailbox):
    """A roster records who competed, not who applied. Placing the overflow
    below the line would queue people who already fenced — and because a
    substitute placement is not billed, would leave them owing nothing."""
    organizer = auth_headers()
    setup(client, organizer)
    patched = client.patch(
        "/api/tournaments/cup/disciplines/SA",
        json={"weapon": "SA", "capacity": 1, "fee": 800},
        headers=organizer,
    )
    assert patched.status_code == 200, patched.text
    import_roster(
        client,
        organizer,
        [row("First", "first@example.com", when="2026-04-01T10:00:00"),
         row("Second", "second@example.com", when="2026-04-02T10:00:00"),
         row("Third", "third@example.com", when="2026-04-03T10:00:00")],
    )

    issue(client, organizer)

    issued = registrations()
    assert len(issued) == 3
    # every entry seated, three into a discipline that holds one
    assert all(not e.is_substitute for r in issued for e in r.entries)
    # and so every one of them is billed
    assert {r.total_amount for r in issued} == {800}


def test_an_issued_roster_fills_the_discipline_for_later_registrations(
    client, auth_headers, mailbox
):
    """Capacity not applying to the roster does not mean it stops existing: a
    fencer registering afterwards meets a discipline the roster has filled."""
    organizer = auth_headers()
    setup(client, organizer)
    from conftest import enable_payments, publish

    patched = client.patch(
        "/api/tournaments/cup/disciplines/SA",
        json={"weapon": "SA", "capacity": 1, "fee": 800},
        headers=organizer,
    )
    assert patched.status_code == 200, patched.text
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    import_roster(client, organizer, [row("First", "first@example.com"),
                                      row("Second", "second@example.com")])
    issue(client, organizer)

    latecomer = auth_headers(email="late@example.com", name="Late")
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["SA"]}, headers=latecomer
    )

    assert response.status_code == 201
    registration = db_session().scalar(
        select(Registration).where(Registration.vs == response.json()["vs"])
    )
    assert [e.is_substitute for e in registration.entries] == [True]


# --- the clocks never start ------------------------------------------------


def test_an_issued_registration_carries_no_due_date(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])

    issue(client, organizer)

    registration = registrations()[0]
    assert registration.clocks_dormant is True
    assert registration.expires_at is None


def test_the_lifecycle_passes_leave_issued_registrations_alone(
    client, auth_headers, mailbox
):
    """The test this change exists to pass. Run the lifecycle long after any
    window would have closed and assert against the mailer — a broken
    implementation sets the flag correctly and mails anyway."""
    organizer = auth_headers()
    setup(client, organizer)
    from conftest import enable_payments, publish

    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    import_roster(client, organizer, [row("Jan", "jan@example.com"),
                                      row("Eva", "eva@example.com")])
    issue(client, organizer)

    # push every clock far into the past
    session = db_session()
    for registration in session.scalars(select(Registration)).all():
        registration.registered_at = datetime.now(UTC) - timedelta(days=400)
    session.commit()

    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    assert mailbox.sent == []
    after = session.scalars(select(Registration)).all()
    assert all(r.state == RegistrationState.RESERVED for r in after)
    assert all(r.reminded_at is None for r in after)
    # and still seated: not demoted to the substitute queue
    assert all(not e.is_substitute for r in after for e in r.entries)


def test_configuration_changes_do_not_wake_the_clocks(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    from conftest import enable_payments, publish

    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)

    client.patch(
        "/api/tournaments/cup",
        json={"payment_mode": "immediate", "seating_deadline": "2026-01-01"},
        headers=organizer,
    )
    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    assert mailbox.sent == []
    registration = registrations()[0]
    assert registration.state == RegistrationState.RESERVED
    assert registration.expires_at is None


def test_dormant_clocks_do_not_stop_money(client, auth_headers, mailbox):
    """What is dormant is the passage of time, not the money."""
    organizer = auth_headers()
    setup(client, organizer)
    from conftest import enable_payments, import_statement, publish

    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)
    vs = registrations()[0].vs

    # a Fio export: read by the exact parser, so this needs no model
    statement = (
        "meta;data\n\n"
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;"
        "Název protiúčtu;Protiúčet\n"
        f"9001;01.05.2026;800,00;CZK;{vs};;;platba;Jan;123/0800\n"
    ).encode()
    result = import_statement(client, organizer, statement, "cup")

    assert result["matched"] == 1
    assert registrations()[0].state == RegistrationState.PAID


# --- running it again ------------------------------------------------------


def test_a_rerun_changes_nothing_it_already_did(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com"),
                                      row("Eva", "eva@example.com")])
    issue(client, organizer)
    before = {r.id: (r.vs, r.total_amount, r.state) for r in registrations()}

    report = issue(client, organizer)

    assert report["issued"] == 0
    assert {r.id: (r.vs, r.total_amount, r.state) for r in registrations()} == before
    assert mailbox.sent == []


def test_a_later_import_is_caught_up(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)
    first_vs = registrations()[0].vs

    import_roster(
        client,
        organizer,
        [row("Jan", "jan@example.com"), row("Eva", "eva@example.com")],
    )
    report = issue(client, organizer)

    assert report["issued"] == 1
    assert first_vs in {r.vs for r in registrations()}
    assert len(registrations()) == 2


def test_a_paid_issued_registration_is_not_disturbed(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)
    session = db_session()
    registration = session.scalars(select(Registration)).one()
    registration.amount_paid_cents = 80000
    registration.state = RegistrationState.PAID
    session.commit()

    issue(client, organizer)

    after = db_session().scalars(select(Registration)).one()
    assert after.state == RegistrationState.PAID
    assert after.amount_paid_cents == 80000


# --- when it may run -------------------------------------------------------


class PairingDedup:
    """Stands in for the classifier: calls every row a likely duplicate of the
    rest, so a group is raised and left pending the organizer's verdict."""

    def propose_merge(self, records, language):
        return MergeProposal(fields=default_merge(records), note="duplicate")

    def classify(self, records):
        ids = [r["id"] for r in records]
        return ThreeBands(likely=[ids] if len(ids) > 1 else [])


def test_refused_while_deduplication_is_pending(client, auth_headers, mailbox):
    """A row a merge may collapse must not spend a variable symbol first."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: PairingDedup()
    import_roster(
        client,
        organizer,
        [row("Jan Novák", "jan@example.com"), row("Jan Novak", "jan2@example.com")],
    )
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    outcome(client, organizer, "cup", "dedup")

    response = client.post("/api/tournaments/cup/import/issue", headers=organizer)

    assert response.status_code == 409
    assert response.json()["detail"] == "dedup_pending"
    assert registrations() == []


def test_the_count_agrees_with_what_the_pass_issues(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com"),
                                      row("Eva", "eva@example.com")])

    stated = client.get("/api/tournaments/cup/import/issue", headers=organizer).json()
    report = issue(client, organizer)

    assert stated["pending_rows"] == 2
    assert stated["pending_dedup"] == 0
    assert report["issued"] == 2
    # and afterwards there is nothing left to issue
    again = client.get("/api/tournaments/cup/import/issue", headers=organizer).json()
    assert again["pending_rows"] == 0


def test_console_access_is_required(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    stranger = auth_headers(email="nobody@example.com", name="Nobody")

    assert client.post(
        "/api/tournaments/cup/import/issue", headers=stranger
    ).status_code in (401, 403, 404)
    assert registrations() == []


def test_clearing_the_import_leaves_no_issued_registration_behind(
    client, auth_headers, mailbox
):
    """`clear_imports` asserts no file was ever uploaded — "no batch, no source
    row, no decision taken about one … survives it". A registration issued for
    such a row is a thing the import produced, so it cannot outlive it: left
    standing it would keep drawing the fencer into the list under the id of a
    row that no longer exists."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)
    assert len(registrations()) == 1

    client.delete("/api/tournaments/cup/import", headers=organizer)

    assert registrations() == []
    assert sheet_rows(client, organizer) == []


def test_clearing_is_refused_while_an_issued_registration_holds_credit(
    client, auth_headers, mailbox
):
    """A row can be asserted never to have existed; a payment against it was a
    real event. Deleting it on the way past would leave books that do not add
    up and nothing to say why — the same reason a tournament with registrations
    cannot be hard-deleted."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    issue(client, organizer)
    session = db_session()
    session.scalars(select(Registration)).one().amount_paid_cents = 80000
    session.commit()

    response = client.delete("/api/tournaments/cup/import", headers=organizer)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "credited_registrations"
    assert len(registrations()) == 1
