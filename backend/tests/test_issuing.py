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
from conftest import enable_payments, outcome, publish
from sqlalchemy import select

from app.bank import get_fio_client
from app.dedup import MergeProposal, ThreeBands, default_merge, get_dedup_llm
from app.hr_match import HRMatchResult, get_hr_matcher
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
                    # the roster CSV has no problems column; a name ending in
                    # "?" is how a test asks the parser to doubt a row
                    problems="doubtful" if raw["name"].endswith("?") else None,
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
        json={
            "location": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
            # set here rather than left to the publish helper, because a test
            # that turns payments on afterwards needs a published tournament to
            # stay setup-complete
            "bank_account": "CZ6508000000192000145399",
        },
        headers=organizer,
    )
    if early_until is not None:
        client.patch(
            "/api/tournaments/cup",
            json={"early_bird_until": early_until},
            headers=organizer,
        )
    # issuing waits for publication (spec imported-registrations, Issuing waits
    # for publication): every roster on this file needs a published tournament
    publish(client, organizer, "cup")
    app.dependency_overrides[get_import_parser] = lambda: RosterParser()


def import_roster(client, organizer, rows):
    content = (HEADER + "".join(rows)).encode()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("roster.csv", io.BytesIO(content), "text/csv")},
        headers=organizer,
    )
    return outcome(client, organizer, "cup", "parse")


# a Fio export carrying no movements: enough for the intake path to run, and it
# ingests nothing, so what the outcome reports about issuing is all that changed
EMPTY_STATEMENT = """\
accountId;2000145399
bankId;2010
currency;CZK

ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet
""".encode()


def issue(client, organizer, slug="cup"):
    """Drive the issuing pass the way the console does: through payment intake.

    There is no issuing action any more (design Decision 10). Importing a
    statement issues registrations for the fencer list before it matches
    anything, so an empty statement is how a test asks for the pass alone. A
    tournament Squire collects nothing for has no intake, and issues through the
    endpoint the Payments phase calls on arrival instead.
    """
    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    if not detail.get("feature_payments"):
        response = client.post(f"/api/tournaments/{slug}/import/issue", headers=organizer)
        assert response.status_code == 200, response.json()
        return response.json()

    response = client.post(
        f"/api/tournaments/{slug}/payments/import-statement",
        files={"file": ("statement.csv", io.BytesIO(EMPTY_STATEMENT), "text/csv")},
        headers=organizer,
    )
    assert response.status_code == 202, response.text
    report = outcome(client, organizer, slug, "statement")
    return {
        "issued": report["issued"],
        "already": report["already_issued"],
        "skipped": report["skipped"],
    }


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


def offer(client, organizer, name, category, price):
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": name, "category": category, "price": price, "max_qty": 1},
        headers=organizer,
    )
    assert response.status_code == 201, response.text


def sheet_row(client, organizer, name):
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    return next(row for row in rows if row["name"] == name)


def test_rentals_are_priced_where_the_tournament_prices_by_items(
    client, auth_headers, mailbox
):
    """The bug this covers: a row's rentals were written into the older
    per-registration fields alone, which a tournament that prices by items does
    not bill from. Every borrowed weapon on the pilot was issued free — 32 of
    them across 19 registrations, and 1 600 Kč in no total anywhere."""
    organizer = auth_headers()
    setup(client, organizer)
    offer(client, organizer, "Sabre", "rental", 50)
    offer(client, organizer, "Buckler", "rental", 50)
    import_roster(
        client,
        organizer,
        [row("Jan", "jan@example.com", disciplines="SA", borrow="Sabre|Buckler")],
    )

    issue(client, organizer)

    registration = registrations()[0]
    assert registration.total_amount == 800 + 50 + 50
    # the selections are what carries the price, and the row's own answers stay
    # where the fencer list and the confirmation mail read them
    assert sorted(s.item.name for s in registration.extra_selections) == [
        "Buckler",
        "Sabre",
    ]
    assert registration.weapon_rentals == ["Sabre", "Buckler"]


def test_an_afterparty_is_taken_up_where_one_item_offers_it(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    offer(client, organizer, "Afterparty", "afterparty", 250)
    import_roster(client, organizer, [row("Jan", "jan@example.com", afterparty="y")])

    issue(client, organizer)

    assert registrations()[0].total_amount == 800 + 250


def test_an_afterparty_nobody_can_name_is_not_guessed(client, auth_headers, mailbox):
    """Two evenings on offer and a row that says only yes. Which one it means
    is not in the row, and billing somebody for an evening they did not pick is
    worse than billing them for none."""
    organizer = auth_headers()
    setup(client, organizer)
    offer(client, organizer, "Afterparty", "afterparty", 250)
    offer(client, organizer, "Afterparty with dinner", "afterparty", 500)
    import_roster(client, organizer, [row("Jan", "jan@example.com", afterparty="y")])

    issue(client, organizer)

    assert registrations()[0].total_amount == 800
    assert registrations()[0].afterparty is True


def test_a_rental_the_tournament_does_not_lend_is_named_on_the_row(
    client, auth_headers, mailbox
):
    """It cannot be priced — nothing on the tournament is called that — so the
    row says which item nothing was billed for rather than leaving the total
    quietly short (owner decision, 2026-09-06)."""
    organizer = auth_headers()
    setup(client, organizer)
    offer(client, organizer, "Sabre", "rental", 50)
    import_roster(
        client,
        organizer,
        [row("Jan", "jan@example.com", disciplines="SA", borrow="Sabre|Sword")],
    )

    # named while the row is still a row, so the item list can be put right
    assert sheet_row(client, organizer, "Jan")["unpriced_rentals"] == ["Sword"]

    issue(client, organizer)

    assert registrations()[0].total_amount == 800 + 50
    issued = sheet_row(client, organizer, "Jan")
    assert issued["weapon_rentals"] == ["Sabre", "Sword"]
    assert issued["unpriced_rentals"] == ["Sword"]


def test_a_flat_fee_tournament_names_no_unpriced_rental(client, auth_headers, mailbox):
    """Priced the older way, a rental is billed by the flat fee whatever it is
    called, so there is no name for a row to fail to match."""
    organizer = auth_headers()
    setup(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"weapon_rental_fee": 100},
        headers=organizer,
    )
    import_roster(
        client, organizer, [row("Jan", "jan@example.com", borrow="whatever")]
    )

    assert sheet_row(client, organizer, "Jan")["unpriced_rentals"] == []
    issue(client, organizer)
    assert registrations()[0].total_amount == 800 + 100


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


def test_a_row_with_no_email_is_issued(client, auth_headers, mailbox):
    """An address identifies an account, and a record enrolled by the organizer
    is not one: it holds no credentials and is never written to."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Anon", "")])

    report = issue(client, organizer)

    assert report["issued"] == 1
    assert report["skipped"] == []
    (registration,) = registrations()
    assert registration.fencer.email is None
    assert registration.fencer.password_hash is None


def test_two_rows_sharing_an_address_are_both_issued(client, auth_headers, mailbox):
    """One person entering several others is ordinary on a real roster — the
    pilot has one address covering three fencers, two of them brothers. The
    address is that person's; the second record simply holds none."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [row("Václav Pekárek", "divis@example.com"),
         row("Jindřich Pekárek", "divis@example.com")],
    )

    report = issue(client, organizer)

    assert report["issued"] == 2
    assert report["skipped"] == []
    by_name = {r.fencer.display_name: r.fencer.email for r in registrations()}
    assert by_name == {"Václav Pekárek": "divis@example.com", "Jindřich Pekárek": None}


def test_the_address_goes_to_the_row_that_comes_first(client, auth_headers, mailbox):
    """Arbitrary between siblings and it does not matter — nothing is written to
    either record, and the address stays on both rows of the fencer list."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [row("Jindřich Pekárek", "divis@example.com", when="2026-04-01T09:00:00"),
         row("Václav Pekárek", "divis@example.com", when="2026-04-01T10:00:00")],
    )

    issue(client, organizer)

    by_name = {r.fencer.display_name: r.fencer.email for r in registrations()}
    assert by_name == {"Jindřich Pekárek": "divis@example.com", "Václav Pekárek": None}


def test_a_parents_address_does_not_enrol_the_child_as_the_parent(client, auth_headers, mailbox):
    """Found on the pilot. Two brothers and their father's address, where the
    father is himself on the roster: resolving by address alone bound one
    brother's row to the father's record, found the father already registered,
    and left the brother off the list entirely."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [
            row("Milan Diviš", "divis@example.com"),
            row("Jindřich Pekárek", "divis@example.com"),
            row("Václav Pekárek", "divis@example.com"),
        ],
    )

    report = issue(client, organizer)

    assert report["issued"] == 3
    by_name = {r.fencer.display_name: r.fencer.email for r in registrations()}
    assert by_name == {
        "Milan Diviš": "divis@example.com",
        "Jindřich Pekárek": None,
        "Václav Pekárek": None,
    }
    # three people, three records — not one record wearing three names
    assert len({r.fencer_id for r in registrations()}) == 3


def test_an_address_is_reused_where_it_names_the_same_person(client, auth_headers, mailbox):
    """The other half: a row whose address belongs to the fencer it names is
    that fencer, whatever spelling the roster used."""
    organizer = auth_headers()
    setup(client, organizer)
    account = auth_headers(email="eva@example.com", name="Eva Malá")
    assert account
    before = db_session().scalar(select(Fencer).where(Fencer.email == "eva@example.com"))
    before_id = before.id

    import_roster(client, organizer, [row("Malá Eva", "eva@example.com")])
    issue(client, organizer)

    (registration,) = registrations()
    assert registration.fencer_id == before_id, "word order is not a different person"


def test_a_row_whose_person_already_registered_is_left_alone(client, auth_headers, mailbox):
    """A registration is unique per tournament and fencer, so a row naming
    somebody who registered in the application has nothing to issue. Left alone
    rather than refused: there is nothing wrong with the row."""
    organizer = auth_headers()
    setup(client, organizer)
    enrolled = auth_headers(email="jan@example.com", name="Jan Novák")
    entered = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["SA"]}, headers=enrolled
    )
    assert entered.status_code == 201, entered.text
    before = len(registrations())
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    report = issue(client, organizer)

    assert report["issued"] == 0
    assert report["skipped"] == []
    assert report["already"] >= 1
    assert len(registrations()) == before


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
    from conftest import enable_payments

    patched = client.patch(
        "/api/tournaments/cup/disciplines/SA",
        json={"weapon": "SA", "capacity": 1, "fee": 800},
        headers=organizer,
    )
    assert patched.status_code == 200, patched.text
    enable_payments(client, organizer, "cup")
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
    from conftest import enable_payments

    enable_payments(client, organizer, "cup")
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
    from conftest import enable_payments

    enable_payments(client, organizer, "cup")
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
    from conftest import enable_payments, import_statement

    enable_payments(client, organizer, "cup")
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
    """A merge collapses rows, not registrations: issuing before the verdict
    leaves one person holding two and the merge nothing to collapse. This is the
    boned-out path, where the Payments phase issues on arrival; the tournament
    Squire collects for meets the same rule at intake (see below)."""
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


# ----------------------------- the symbol belongs to the automatic path


def kept_by_organizer():
    from app.models import RegistrationsKeptBy, Tournament

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    session.commit()


def next_sequence():
    from app.models import Tournament

    return db_session().scalar(select(Tournament.vs_next_seq).where(Tournament.slug == "cup"))


def test_a_manual_tournament_issues_no_variable_symbols(client, auth_headers, mailbox):
    """A symbol is what Squire tells a fencer to quote. On a tournament whose
    organizer keeps the registrations it has told them nothing, so a symbol
    minted here would match no payment while consuming a number from a sequence
    that is unique across the deployment and never reused."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    kept_by_organizer()
    before = next_sequence()

    assert issue(client, organizer)["issued"] == 1

    issued = registrations()
    assert issued and all(r.vs is None for r in issued)
    assert next_sequence() == before, "the sequence has not moved"


def test_a_manual_registration_is_still_priced_and_dormant(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    kept_by_organizer()
    issue(client, organizer)

    (registration,) = registrations()
    assert registration.total_amount > 0
    assert registration.clocks_dormant
    assert registration.expires_at is None
    assert [e.is_substitute for e in registration.entries] == [False]


def test_a_squire_kept_tournament_still_issues_one_symbol_per_row(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [row("Jan Novak", "jan@example.com"), row("Eva Dvorak", "eva@example.com")],
    )
    issue(client, organizer)

    symbols = [r.vs for r in registrations()]
    assert all(vs is not None for vs in symbols)
    assert len(set(symbols)) == len(symbols)


def test_an_issued_registration_is_never_told_about_a_credit(client, auth_headers, mailbox):
    """The hazard dormancy does not cover: crediting an issued registration is
    expressly allowed, so an organizer reconciling last season's statement would
    have mailed the whole roster by confirming each payment. The dormant clocks
    stop the scheduler, not the organizer."""
    from app import emails
    from app.models import Tournament

    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    issue(client, organizer)

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.feature_payments = True
    (registration,) = session.scalars(select(Registration)).all()
    session.commit()
    mailbox.sent.clear()

    emails.send_payment_received(mailbox, tournament, registration.fencer, registration)
    assert mailbox.sent == [], "an issued registration is credited silently"

    # and an ordinary registration is still told
    registration.clocks_dormant = False
    session.commit()
    emails.send_payment_received(mailbox, tournament, registration.fencer, registration)
    assert len(mailbox.sent) == 1


# --- Issuing through payment intake -----------------------------------------
#
# There is no issuing action (design Decision 10). On a tournament Squire
# collects for, the roster is made billable by the intake that needs it — the
# statement import and the bank poll, each issuing before it matches — and the
# deduplication gate sits on intake rather than on issuing, so a verdict left
# outstanding stops the money rather than a control the organizer cannot find.


def collecting_setup(client, organizer, *, fio_token=None):
    setup(client, organizer)
    enable_payments(client, organizer, "cup")
    if fio_token:
        client.patch(
            "/api/tournaments/cup", json={"fio_token": fio_token}, headers=organizer
        )


class SilentFio:
    """A bank with nothing to report: a poll of it is the issuing pass alone."""

    def __init__(self):
        self.calls = []

    def fetch(self, token, date_from, date_to):
        self.calls.append(token)
        return []


@pytest.fixture
def stub_fio():
    stub = SilentFio()
    app.dependency_overrides[get_fio_client] = lambda: stub
    yield stub
    app.dependency_overrides.pop(get_fio_client, None)


def import_bank_statement(client, organizer, content=EMPTY_STATEMENT):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("statement.csv", io.BytesIO(content), "text/csv")},
        headers=organizer,
    )


def test_a_statement_import_issues_before_it_matches(client, auth_headers, mailbox):
    """The whole point: the organizer imports a statement and the roster it has
    to match against comes into existence in the same operation."""
    organizer = auth_headers()
    collecting_setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com"),
                                      row("Eva Dvorak", "eva@example.com")])
    assert registrations() == []

    assert import_bank_statement(client, organizer).status_code == 202
    report = outcome(client, organizer, "cup", "statement")

    assert report["issued"] == 2
    assert len(registrations()) == 2
    # a tournament Squire keeps the registrations for gets its shortcut
    assert all(r.vs is not None for r in registrations())
    assert mailbox.sent == [], "issuing mails nobody, whatever ran it"


def test_a_poll_issues_on_the_same_terms(client, auth_headers, mailbox, stub_fio):
    organizer = auth_headers()
    collecting_setup(client, organizer, fio_token="secret-token")
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    polled = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)

    assert polled.status_code == 200, polled.text
    assert polled.json()["issued"] == 1
    assert len(registrations()) == 1


def test_a_second_intake_issues_nothing(client, auth_headers, mailbox):
    organizer = auth_headers()
    collecting_setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    import_bank_statement(client, organizer)
    first = outcome(client, organizer, "cup", "statement")
    symbols = {r.id: r.vs for r in registrations()}

    import_bank_statement(client, organizer)
    second = outcome(client, organizer, "cup", "statement")

    assert first["issued"] == 1
    assert second == {**second, "issued": 0, "already_issued": 1}
    assert {r.id: r.vs for r in registrations()} == symbols


def test_a_row_entered_between_two_statements_is_caught_up(client, auth_headers, mailbox):
    """Nobody has to remember that the second fencer needs anything done."""
    organizer = auth_headers()
    collecting_setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    import_bank_statement(client, organizer)
    outcome(client, organizer, "cup", "statement")

    import_roster(client, organizer, [row("Eva Dvorak", "eva@example.com")])
    import_bank_statement(client, organizer)
    second = outcome(client, organizer, "cup", "statement")

    assert second["issued"] == 1
    assert second["already_issued"] == 1
    assert len(registrations()) == 2


def test_intake_is_refused_while_duplicates_are_pending(client, auth_headers, mailbox):
    organizer = auth_headers()
    collecting_setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: PairingDedup()
    import_roster(
        client,
        organizer,
        [row("Jan Novák", "jan@example.com"), row("Jan Novak", "jan2@example.com")],
    )
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    outcome(client, organizer, "cup", "dedup")

    response = import_bank_statement(client, organizer)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "dedup_pending"
    assert response.json()["detail"]["groups"] == 1
    assert registrations() == [], "a refused intake issues nothing"


def test_a_poll_is_refused_on_the_same_ground(client, auth_headers, mailbox, stub_fio):
    organizer = auth_headers()
    collecting_setup(client, organizer, fio_token="secret-token")
    app.dependency_overrides[get_dedup_llm] = lambda: PairingDedup()
    import_roster(
        client,
        organizer,
        [row("Jan Novák", "jan@example.com"), row("Jan Novak", "jan2@example.com")],
    )
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    outcome(client, organizer, "cup", "dedup")

    response = client.post("/api/tournaments/cup/payments/fio-poll", headers=organizer)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "dedup_pending"
    assert stub_fio.calls == [], "the bank is not even asked"


def test_intake_proceeds_once_the_verdicts_are_in(client, auth_headers, mailbox):
    organizer = auth_headers()
    collecting_setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: PairingDedup()
    import_roster(
        client,
        organizer,
        [row("Jan Novák", "jan@example.com"), row("Jan Novak", "jan2@example.com")],
    )
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    outcome(client, organizer, "cup", "dedup")
    groups = client.get("/api/tournaments/cup/import/dedup/groups", headers=organizer).json()
    for group in groups:
        client.post(
            "/api/tournaments/cup/import/dedup/decide",
            json={"key": group["key"], "accept": False},
            headers=organizer,
        )

    assert import_bank_statement(client, organizer).status_code == 202
    report = outcome(client, organizer, "cup", "statement")

    assert report["issued"] == 2


def test_the_conclusion_names_the_rows_it_skipped(client, auth_headers, mailbox):
    """No confirmation dialog carries this any more, and it has to land
    somewhere: each skipped row is a fencer whose payment cannot reconcile until
    the organizer fixes the row."""
    organizer = auth_headers()
    collecting_setup(client, organizer)
    import_roster(
        client,
        organizer,
        [
            row("Jan Novak", "jan@example.com"),
            row("Bez Disciplin", "bez@example.com", disciplines=""),
        ],
    )

    import_bank_statement(client, organizer)
    report = outcome(client, organizer, "cup", "statement")

    assert report["issued"] == 1
    assert [(s["name"], s["reason"]) for s in report["skipped"]] == [
        ("Bez Disciplin", "no_discipline")
    ]


def test_the_lifecycle_passes_issue_nothing(client, auth_headers, mailbox):
    """They move time, not money."""
    organizer = auth_headers()
    collecting_setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    response = client.post("/api/tournaments/cup/payments/process", headers=organizer)

    assert response.status_code == 200, response.text
    assert registrations() == []


def test_no_surface_issues_outside_intake_where_squire_collects(client, auth_headers, mailbox):
    """One path, so a variable symbol cannot be spent from anywhere else."""
    organizer = auth_headers()
    collecting_setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    response = client.post("/api/tournaments/cup/import/issue", headers=organizer)

    assert response.status_code == 409
    assert response.json()["detail"] == "intake_issues_instead"
    assert registrations() == []


def test_a_tournament_squire_collects_nothing_for_issues_on_arrival(client, auth_headers, mailbox):
    """No intake exists to hang the pass on, so the Payments phase issues when
    the organizer opens it — and mints nothing scarce doing so."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    report = issue(client, organizer)

    assert report["issued"] == 1
    (registration,) = registrations()
    # priced, entered and dormant — everything the export, the outstanding
    # column and the manual paid tick need. Whether it carries a symbol is
    # `registrations_kept_by`'s question, not this one
    assert registration.total_amount is not None
    assert registration.clocks_dormant


# --- what issuing must not take away ----------------------------------------


class MatchesJan:
    """Proposes the stub index's Jan Novák for the row of that name, and finds
    nobody else — the shape a real matching run leaves behind: proposals that
    nobody has ratified yet."""

    def match(self, fencers, candidates):
        # one result per fencer, matched or not: the real matcher answers the
        # whole batch, and `run_matching` zips the two strictly
        return [
            HRMatchResult(
                name=fencer["name"],
                club=fencer["club"],
                hr_id=10234 if fencer["name"] == "Jan Novak" else None,
                matched_name="Jan Novák" if fencer["name"] == "Jan Novak" else None,
                matched_club="Prague HEMA" if fencer["name"] == "Jan Novak" else None,
                nationality="CZ",
            )
            for fencer in fencers
        ]


def sheet_row_named(client, organizer, name):
    body = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return next(r for r in body["rows"] if r["name"] == name)


def test_issuing_keeps_an_unratified_hr_proposal_on_the_row(client, auth_headers, mailbox):
    """The bug this covers: matching proposed 52 profiles, the organizer had not
    ratified them, and the first statement import issued the roster — after
    which every row read `nespárováno` with an empty HR side, and the proposals
    could not be reached at all, because ratifying happens on this table.

    Issuing binds only a confirmed match, and that stays true. What must not
    happen is the proposal disappearing: a registration issued for a row stands
    in that row's place, so it shows what the row showed.
    """
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_hr_matcher] = lambda: MatchesJan()
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    client.post("/api/tournaments/cup/import/match", headers=organizer)
    outcome(client, organizer, "cup", "match")

    before = sheet_row_named(client, organizer, "Jan Novak")
    assert before["hr_id"] == 10234
    assert before["match_verdict"] != "unknown"

    issue(client, organizer)

    after = sheet_row_named(client, organizer, "Jan Novak")
    assert after["hr_id"] == 10234, "the proposal survives the roster becoming billable"
    assert after["match_verdict"] == before["match_verdict"]
    assert after["hr_name"] == before["hr_name"]
    # and it is still only a proposal: nothing claimed the profile
    fencer = db_session().scalar(select(Fencer).where(Fencer.email == "jan@example.com"))
    assert fencer.hr_id is None


def test_a_row_with_no_proposal_still_reads_unmatched_after_issuing(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_hr_matcher] = lambda: MatchesJan()
    import_roster(client, organizer, [row("Nikdo Neznámý", "nikdo@example.com")])
    client.post("/api/tournaments/cup/import/match", headers=organizer)
    outcome(client, organizer, "cup", "match")

    issue(client, organizer)

    after = sheet_row_named(client, organizer, "Nikdo Neznámý")
    assert after["hr_id"] is None
    assert after["match_verdict"] == "none_found"


# --- naming the rows that cannot be issued, before anything runs -------------


def issuable(client, organizer):
    return client.get("/api/tournaments/cup/import/issue", headers=organizer).json()


def test_two_rows_sharing_an_address_are_not_named_at_all(client, auth_headers, mailbox):
    """The pilot's shape, and no longer a problem: one address covering several
    fencers is how a parent or a club representative enters a family."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [
            row("Milan Diviš", "divis@example.com"),
            row("Václav Pekárek", "divis@example.com"),
        ],
    )

    stated = issuable(client, organizer)

    assert stated["pending_rows"] == 2
    assert stated["skipped"] == []
    assert registrations() == [], "stating it writes nothing"


def test_a_row_that_states_nothing_readable_is_named(client, auth_headers, mailbox):
    """The two reasons that survive both describe the row: no fencer to make,
    and a registration that would total zero and quietly absorb a payment."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [
            row("Bez Disciplin", "bez@example.com", disciplines=""),
            row("Jan Novak", "jan@example.com"),
        ],
    )

    stated = issuable(client, organizer)

    assert [(s["name"], s["reason"]) for s in stated["skipped"]] == [
        ("Bez Disciplin", "no_discipline")
    ]


def test_the_dry_run_agrees_with_what_the_pass_then_does(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(
        client,
        organizer,
        [
            row("Milan Diviš", "divis@example.com"),
            row("Václav Pekárek", "divis@example.com"),
            row("Bez Disciplin", "bez@example.com", disciplines=""),
            row("Bez Mailu", ""),
        ],
    )

    stated = issuable(client, organizer)
    report = issue(client, organizer)

    assert [(s["name"], s["reason"]) for s in stated["skipped"]] == [
        (s["name"], s["reason"]) for s in report["skipped"]
    ]


def test_a_row_whose_person_is_already_registered_is_not_named(client, auth_headers, mailbox):
    """Left alone rather than refused, so nothing warns about it: the row is
    fine, the tournament simply already holds that fencer's registration."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Milan Diviš", "divis@example.com")])
    issue(client, organizer)
    import_roster(client, organizer, [row("Václav Pekárek", "divis@example.com")])

    stated = issuable(client, organizer)

    assert stated["skipped"] == []


def test_nothing_is_named_where_every_row_can_be_issued(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])

    assert issuable(client, organizer)["skipped"] == []


# --- correcting a row's disciplines -----------------------------------------
#
# A row that entered no discipline cannot be issued, and until the organizer
# could put one there the console named a remedy it did not offer. The cell is
# the row's to correct only while it is still a row: an issued registration's
# entries decide what it is billed and where it is seated, and a cell edit would
# move the table without moving the money.


def edit(client, organizer, row_id, value):
    return client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": "field_edit",
            "target": row_id,
            "payload": {"field": "disciplines", "value": value},
        },
        headers=organizer,
    )


def test_a_row_given_a_discipline_can_then_be_issued(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Bez Disciplin", "bez@example.com", disciplines="")])
    (before,) = issuable(client, organizer)["skipped"]
    assert before["reason"] == "no_discipline"

    assert edit(client, organizer, before["row_id"], ["SA"]).status_code in (200, 201)

    assert issuable(client, organizer)["skipped"] == []
    report = issue(client, organizer)
    assert report["issued"] == 1
    (registration,) = registrations()
    assert [e.discipline.slug for e in registration.entries] == ["SA"]


def test_a_corrected_row_is_priced_for_what_it_now_enters(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer, fee=800)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com", disciplines="SA")])
    rows = sheet_rows(client, organizer)
    target = next(r["id"] for r in rows if r["name"] == "Jan Novak")

    edit(client, organizer, target, ["SA", "SB"])
    issue(client, organizer)

    (registration,) = registrations()
    assert sorted(e.discipline.slug for e in registration.entries) == ["SA", "SB"]
    assert registration.total_amount == 1300  # 800 + 500


def test_an_unknown_slug_is_refused(client, auth_headers, mailbox):
    """Dropped silently by issuing, it would leave a row that mysteriously will
    not bill."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    target = sheet_rows(client, organizer)[0]["id"]

    refused = edit(client, organizer, target, ["SA", "NEEXISTUJE"])

    assert refused.status_code == 422
    assert refused.json()["detail"]["slugs"] == ["NEEXISTUJE"]


def test_an_empty_list_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan Novak", "jan@example.com")])
    target = sheet_rows(client, organizer)[0]["id"]

    assert edit(client, organizer, target, []).status_code == 422
    assert edit(client, organizer, target, "SA").status_code == 422


def test_issuing_keeps_what_the_parser_doubted(client, auth_headers, mailbox):
    """A registration takes its row's place in the table, and the flag comes
    with it. What was doubtful about the row does not stop being true because
    the row became billable — and the organizer meets the flag on the phase
    where they work, not only in the minutes before an intake runs."""
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan?", "jan@example.com"),
                                      row("Eva", "eva@example.com")])
    before = {r["name"]: r["problems"] for r in sheet_rows(client, organizer)}
    assert before["Jan?"] == "doubtful"

    issue(client, organizer)

    after = {r["name"]: r["problems"] for r in sheet_rows(client, organizer)}
    assert after["Jan?"] == "doubtful"
    assert after["Eva"] is None
