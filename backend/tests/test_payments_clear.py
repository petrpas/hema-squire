"""Clearing the payments a tournament imported (spec `payments-clearing`).

The console could undo a table import and not a statement import. Undoing the
pilot's misread statement took hand-written SQL against the live database, twice.

Two of these matter more than the rest: that a re-import after a clear genuinely
re-reads the file rather than reusing what was stored, and that a clear refused
for credited money removes *nothing*. Both are asserted on what survived, not on
a status code — a broken implementation gets the status code right.
"""

import io

import pytest
from conftest import import_statement, settle
from sqlalchemy import select

from app.bank import ParsedStatementRow, get_statement_parser
from app.mail import get_mailer
from app.main import app
from app.models import BankTransaction, ImportDecision, Registration, Rule
from tests.test_matching import db_session, enroll, setup


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


class CountingParser:
    """Counts the rows it is asked to interpret, so a test can tell a genuine
    re-read from a reuse of what was stored."""

    def __init__(self):
        self.rows_seen = []

    def parse_batch(self, rows):
        self.rows_seen.extend(rows)
        return [
            ParsedStatementRow(
                external_id=raw.get("Reference") or None,
                date=raw["Date"],
                amount_cents=int(round(float(raw["Amount"]) * 100)),
                currency="CZK",
                vs=int(raw["Payment ref"]) if raw.get("Payment ref") else None,
                message=raw.get("Note") or None,
                payer_name=raw.get("Counterparty") or None,
                payer_account=None,
            )
            for raw in rows
        ]


@pytest.fixture
def parser():
    fake = CountingParser()
    app.dependency_overrides[get_statement_parser] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_statement_parser, None)


def statement(rows: list[str]) -> bytes:
    header = "Date,Counterparty,Amount,Currency,Payment ref,Note"
    return ("\n".join([header, *rows]) + "\n").encode()


def clear(client, headers, slug="cup"):
    return client.delete(f"/api/tournaments/{slug}/payments", headers=headers)


def clearable(client, headers, slug="cup"):
    return client.get(f"/api/tournaments/{slug}/payments/clear", headers=headers).json()


def transactions():
    return db_session().scalars(select(BankTransaction)).all()


def stored_readings():
    return db_session().scalars(
        select(ImportDecision).where(ImportDecision.kind == "statement_row")
    ).all()


# --- what a clear removes --------------------------------------------------


def test_a_misread_statement_is_removed_altogether(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    import_statement(
        client, organizer, statement(["2026-08-12,Jan Novák,1000.00,CZK,,entry fee"])
    )
    assert len(transactions()) == 1

    body = clear(client, organizer).json()

    assert body == {"payments": 1}
    assert transactions() == []
    assert client.get(
        "/api/tournaments/cup/payments/unmatched", headers=organizer
    ).json() == []


def test_the_stored_readings_go_with_them(client, auth_headers, mailbox, parser):
    """The half a person would never guess. Left behind, they defeat the next
    import invisibly."""
    organizer = auth_headers()
    setup(client, organizer)
    import_statement(
        client, organizer, statement(["2026-08-12,Jan Novák,1000.00,CZK,,fee"])
    )
    assert len(stored_readings()) == 1

    clear(client, organizer)

    assert stored_readings() == []


def test_re_import_after_a_clear_reads_the_file_again(
    client, auth_headers, mailbox, parser
):
    """The property this change exists for. A clear of the transactions alone
    would pass every other test here and fail this one."""
    organizer = auth_headers()
    setup(client, organizer)
    rows = ["2026-08-12,Jan Novák,1000.00,CZK,,fee"]
    import_statement(client, organizer, statement(rows))
    assert len(parser.rows_seen) == 1

    clear(client, organizer)
    import_statement(client, organizer, statement(rows))

    # asked again, rather than served from what was stored before the clear
    assert len(parser.rows_seen) == 2
    assert len(transactions()) == 1


def test_a_corrected_file_is_read_as_corrected(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    import_statement(
        client, organizer, statement(["2026-08-12,Jan,1214.00,CZK,,truncated"])
    )
    clear(client, organizer)

    import_statement(
        client, organizer, statement(["2026-08-12,Jan Novák,1214.03,CZK,,full message"])
    )

    remaining = transactions()
    assert len(remaining) == 1
    assert remaining[0].amount_cents == 121403
    assert remaining[0].payer_name == "Jan Novák"


def test_several_statements_go_together(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    for day in ("12", "13", "14"):
        import_statement(
            client, organizer, statement([f"2026-08-{day},Payer,100.00,CZK,,fee"])
        )
    assert len(transactions()) == 3

    assert clear(client, organizer).json() == {"payments": 3}

    assert transactions() == []


def test_a_link_to_a_cleared_transaction_goes_with_it(
    client, auth_headers, mailbox, parser
):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    # an amount that does not settle the registration, so the link stays a link
    import_statement(client, organizer, statement(["2026-08-12,Jan,10.00,CZK,,fee"]))
    transaction = transactions()[0]
    client.post(
        "/api/tournaments/cup/payments/link",
        json={"transaction_id": transaction.id, "vs": [vs]},
        headers=organizer,
    )
    assert db_session().scalars(
        select(Rule).where(Rule.kind == "payment_link")
    ).all()

    # the link credited it, so unlink first — a credited transaction refuses
    for rule in db_session().scalars(select(Rule).where(Rule.kind == "payment_link")):
        client.delete(f"/api/tournaments/cup/rules/{rule.id}", headers=organizer)
    clear(client, organizer)

    assert transactions() == []
    assert db_session().scalars(select(Rule).where(Rule.kind == "payment_link")).all() == []


# --- what it refuses -------------------------------------------------------


def test_credited_money_stops_the_clear(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_statement(
        client, organizer, statement([f"2026-08-12,Jan,1000.00,CZK,{vs},fee"])
    )
    assert transactions()[0].matched_registration_id is not None

    response = clear(client, organizer)

    assert response.status_code == 409
    assert response.json()["detail"] == {"code": "credited_transactions", "count": 1}


def test_a_refusal_removes_nothing_at_all(client, auth_headers, mailbox, parser):
    """The assertion that matters: not the status code, but that everything
    survived it — including the uncredited transactions and the stored
    readings a partial clear would have taken."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_statement(
        client,
        organizer,
        statement(
            [
                f"2026-08-12,Jan,1000.00,CZK,{vs},paid",
                "2026-08-13,Nobody,500.00,CZK,,unresolved",
                "2026-08-14,Nobody Else,250.00,CZK,,unresolved",
            ]
        ),
    )
    before = len(transactions())
    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    credited_before = registration.amount_paid_cents
    readings_before = len(stored_readings())

    assert clear(client, organizer).status_code == 409

    assert len(transactions()) == before
    assert len(stored_readings()) == readings_before
    after = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert after.amount_paid_cents == credited_before
    assert after.state == registration.state


def test_clearing_after_the_payments_are_unlinked(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_statement(
        client, organizer, statement([f"2026-08-12,Jan,1000.00,CZK,{vs},fee"])
    )
    assert clear(client, organizer).status_code == 409

    # unwind the credit the way the console does, then clear
    session = db_session()
    transaction = session.scalars(select(BankTransaction)).one()
    transaction.matched_registration_id = None
    transaction.status = "unmatched"
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    registration.amount_paid_cents = 0
    session.commit()

    assert clear(client, organizer).status_code == 200
    assert transactions() == []


def test_the_count_states_what_stands_in_the_way(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    import_statement(
        client,
        organizer,
        statement(
            [f"2026-08-12,Jan,1000.00,CZK,{vs},paid", "2026-08-13,Nobody,50.00,CZK,,no"]
        ),
    )

    assert clearable(client, organizer) == {"payments": 2, "credited": 1}


# --- what it leaves alone --------------------------------------------------


def test_the_roster_survives(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)
    import_statement(client, organizer, statement(["2026-08-12,Nobody,50.00,CZK,,no"]))

    clear(client, organizer)

    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    assert registration.vs == vs
    assert registration.total_amount > 0
    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "reserved"


def test_payment_settings_survive(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    client.patch(
        "/api/tournaments/cup", json={"fio_token": "secret-token"}, headers=organizer
    )
    import_statement(client, organizer, statement(["2026-08-12,Nobody,50.00,CZK,,no"]))

    clear(client, organizer)

    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert detail["fio_token_configured"] is True


def test_clearing_payments_leaves_the_imported_rows(client, auth_headers, mailbox, parser):
    """Two clears on two subjects; neither implies the other."""
    from app.importer import get_import_parser
    from tests.test_import import CSV, FakeParser

    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: FakeParser()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
        headers=organizer,
    )
    settle(client, organizer, "cup", kind="parse")
    import_statement(client, organizer, statement(["2026-08-12,Nobody,50.00,CZK,,no"]))

    clear(client, organizer)

    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    assert [r for r in rows if r["id"].startswith("imp:")]


# --- guards ----------------------------------------------------------------


def test_console_access_is_required(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    import_statement(client, organizer, statement(["2026-08-12,Nobody,50.00,CZK,,no"]))
    stranger = auth_headers(email="nobody@example.com", name="Nobody")

    assert clear(client, stranger).status_code in (401, 403, 404)
    assert len(transactions()) == 1


def test_refused_where_payments_are_disabled(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "nopay", "display_name": "No Pay", "date": "2026-12-05"},
        headers=organizer,
    )

    assert clear(client, organizer, "nopay").status_code == 409
