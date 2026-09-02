"""Importing a bank statement, whatever bank wrote it.

A Fio export is parsed exactly and never reaches a model; anything else is read
as a table and interpreted (spec `payments-intake`).
"""

import io

import pytest
from sqlalchemy import select

from app.bank import ParsedStatementRow, get_statement_parser
from app.mail import get_mailer
from app.main import app
from app.models import Operation, OperationKind, OperationStatus, Tournament
from tests.conftest import settle
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


class FakeStatementParser:
    """Deterministic stand-in for the model: reads a plain English-headed
    statement of the kind a non-Czech bank exports."""

    def __init__(self):
        self.calls = 0

    def parse_batch(self, rows):
        self.calls += 1
        parsed = []
        for raw in rows:
            amount = raw["Amount"].replace(" ", "").replace(",", ".")
            parsed.append(
                ParsedStatementRow(
                    external_id=raw.get("Reference") or None,
                    date=raw["Date"],
                    amount_cents=int(round(float(amount) * 100)),
                    currency=raw.get("Currency") or "CZK",
                    vs=int(raw["Payment ref"]) if raw.get("Payment ref") else None,
                    message=raw.get("Note") or None,
                    payer_name=raw.get("Counterparty") or None,
                    payer_account=None,
                )
            )
        return parsed


def foreign_csv(rows: list[str], header_extra: str = "") -> bytes:
    header = "Date,Counterparty,Amount,Currency,Payment ref,Note" + header_extra
    return ("\n".join([header, *rows]) + "\n").encode()


def fio_csv(rows: list[str]) -> bytes:
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;"
        "Název protiúčtu;Protiúčet"
    )
    return ("meta;data\n\n" + header + "\n" + "\n".join(rows) + "\n").encode()


def upload(client, headers, content: bytes, name="statement.csv"):
    return client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": (name, io.BytesIO(content), "text/csv")},
        headers=headers,
    )


@pytest.fixture
def parser():
    fake = FakeStatementParser()
    app.dependency_overrides[get_statement_parser] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_statement_parser, None)


def test_a_statement_from_a_bank_we_have_never_seen(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    rows = [f"2026-08-12,Jan Novák,1000.00,CZK,{vs},entry fee"]
    assert upload(client, organizer, foreign_csv(rows)).status_code == 202

    concluded = settle(client, organizer, kind="statement")
    assert concluded["status"] == "done"
    assert concluded["outcome"]["new"] == 1
    assert concluded["outcome"]["matched"] == 1

    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "paid"


def test_a_fio_export_never_reaches_the_parser(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    upload(client, organizer, fio_csv([f"9001;12.08.2026;1000,00;CZK;{vs};;;;Jan Novák;123/0800"]))
    concluded = settle(client, organizer, kind="statement")

    assert concluded["outcome"]["matched"] == 1
    # a published, stable column layout is not a guessing problem (design D1)
    assert parser.calls == 0


def test_a_spreadsheet_reads_like_its_csv(client, auth_headers, mailbox, parser):
    openpyxl = pytest.importorskip("openpyxl")
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Date", "Counterparty", "Amount", "Currency", "Payment ref", "Note"])
    sheet.append(["2026-08-12", "Jan Novák", "1000.00", "CZK", str(vs), "entry fee"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    response = upload(client, organizer, buffer.getvalue(), name="statement.xlsx")
    assert response.status_code == 202
    assert settle(client, organizer, kind="statement")["outcome"]["matched"] == 1


def test_the_same_file_twice_credits_nothing_again(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)
    # no Reference column: the row carries no id of the bank's own, so
    # idempotence rests on the row's own fingerprint (design D2)
    content = foreign_csv([f"2026-08-12,Jan Novák,1000.00,CZK,{vs},entry fee"])

    upload(client, organizer, content)
    assert settle(client, organizer, kind="statement")["outcome"]["new"] == 1

    upload(client, organizer, content)
    second = settle(client, organizer, kind="statement")
    assert second["outcome"]["new"] == 0
    assert second["outcome"]["duplicate"] == 1
    # and the rows were not interpreted a second time
    assert parser.calls == 1


def test_only_new_rows_are_interpreted_afresh(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, first_vs = enroll(client, auth_headers)
    _, second_vs = enroll(client, auth_headers, email="eva@example.com", name="Eva")

    row_one = f"2026-08-12,Jan Novák,1000.00,CZK,{first_vs},entry fee"
    upload(client, organizer, foreign_csv([row_one]))
    settle(client, organizer, kind="statement")
    assert parser.calls == 1

    row_two = f"2026-08-13,Eva Malá,1000.00,CZK,{second_vs},entry fee"
    upload(client, organizer, foreign_csv([row_one, row_two]))
    concluded = settle(client, organizer, kind="statement")

    assert concluded["outcome"]["new"] == 1
    assert concluded["outcome"]["duplicate"] == 1
    # the second call carried only the row no decision covered
    assert parser.calls == 2


def test_a_statement_that_repeats_a_row_exactly(client, auth_headers, mailbox, parser):
    """Two identical payments on one day from a bank that numbers nothing leave
    two byte-identical lines. Both key the same decision, so interpreting each
    of them stored one key twice and the import died on the uniqueness of
    (tournament, kind, key) partway through the batch."""
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers)

    row = f"2026-08-12,Jan Novák,1000.00,CZK,{vs},entry fee"
    assert upload(client, organizer, foreign_csv([row, row])).status_code == 202

    concluded = settle(client, organizer, kind="statement")
    assert concluded["status"] == "done"
    # asked once, not twice: the identical row is one thing to interpret
    assert parser.calls == 1
    # and the repeat collides with the first on external_id, as a re-read of
    # the same row does — the money is credited once (design D2)
    assert concluded["outcome"]["new"] == 1
    assert concluded["outcome"]["duplicate"] == 1

    state = client.get("/api/tournaments/cup/my-registration", headers=fencer).json()
    assert state["state"] == "paid"


def test_a_table_that_is_not_a_statement_is_refused_before_the_model(
    client, auth_headers, mailbox, parser
):
    """A statement is a table of dated amounts. A table with no column of
    either has been read wrongly or is not a statement, and finding that out
    costs nothing — so it is found out before a model call is spent, and in the
    request rather than as an operation the organizer waits for."""
    organizer = auth_headers()
    setup(client, organizer)

    # a registration export, uploaded to the wrong importer: it has dates, but
    # nothing that reads as money
    registrations = (
        "Timestamp,Name,Club,Disciplines\n"
        "01.04.2026 14:15:27,Jan Novák,Paridon,sabre\n"
    ).encode()
    response = upload(client, organizer, registrations)

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "unreadable_statement",
        "missing": "an amount",
    }
    assert parser.calls == 0
    # and no operation was started for the organizer to watch fail
    assert client.get("/api/tournaments/cup/operations", headers=organizer).json() == {
        "running": None,
        "concluded": [],
    }


def test_a_statement_read_with_the_wrong_delimiter_is_refused(
    client, auth_headers, mailbox, parser
):
    """The misreading this guard exists for. A semicolon-separated export read
    as commas is one column of mangled text; no column reads as a date, and the
    model would be left inventing amounts from it."""
    organizer = auth_headers()
    setup(client, organizer)

    # every line one field, cut short at its first decimal comma
    mangled = (
        'Datum;"Objem";"Zpráva"\n'
        '"07.04.2026";"1214,03";"CHEREAU"\n'
    ).encode()
    # read as the semicolons it is, this is a statement
    assert upload(client, organizer, mangled).status_code == 202
    settle(client, organizer, kind="statement")

    response = upload(client, organizer, b"a,b\n07.04.2026;1214,03\n")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unreadable_statement"


def test_money_leaving_the_account_is_not_a_payment(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)

    upload(
        client,
        organizer,
        foreign_csv([
            f"2026-08-12,Jan Novák,1000.00,CZK,{vs},entry fee",
            "2026-08-13,Bank,-150.00,CZK,,account fee",
        ]),
    )
    concluded = settle(client, organizer, kind="statement")
    assert concluded["outcome"]["new"] == 1


def test_nothing_to_interpret_with(client, auth_headers, mailbox):
    """No model configured: an unrecognised statement is refused, not ingested
    as though it held no payments."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers)
    app.dependency_overrides[get_statement_parser] = lambda: None
    try:
        response = upload(client, organizer, foreign_csv(["2026-08-12,X,10.00,CZK,,x"]))
        assert response.status_code == 409
        assert response.json()["detail"] == "no_statement_parser"
    finally:
        app.dependency_overrides.pop(get_statement_parser, None)

    assert client.get(
        "/api/tournaments/cup/payments/transactions", headers=organizer
    ).json() == []


def test_a_file_that_is_neither_csv_nor_spreadsheet(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    response = upload(client, organizer, b"%PDF-1.4 not a statement", name="statement.pdf")
    assert response.status_code == 422
    assert response.json()["detail"] == "unsupported_statement_format"


def test_progress_is_counted_in_rows(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    rows = []
    for index in range(45):
        _, vs = enroll(
            client, auth_headers, email=f"f{index}@example.com", name=f"Fencer {index}"
        )
        rows.append(f"2026-08-12,Payer {index},1000.00,CZK,{vs},entry fee")

    response = upload(client, organizer, foreign_csv(rows))
    assert response.json()["rows"] == 45

    concluded = settle(client, organizer, kind="statement")
    assert concluded["total"] == 45
    assert concluded["done"] == 45
    # 45 rows in batches of twenty: three calls
    assert parser.calls == 3


def test_a_second_operation_is_refused_by_name(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers)

    # a parse already under way, as if the organizer were importing a table
    session = db_session()
    tournament_id = session.scalar(select(Tournament.id).where(Tournament.slug == "cup"))
    session.add(
        Operation(
            tournament_id=tournament_id,
            kind=OperationKind.PARSE,
            status=OperationStatus.RUNNING,
            total=1,
            done=0,
            started_by=1,
            outcome={},
        )
    )
    session.commit()

    response = upload(client, organizer, foreign_csv([f"2026-08-12,X,10.00,CZK,{vs},x"]))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "operation_running"
    assert response.json()["detail"]["kind"] == "parse"
