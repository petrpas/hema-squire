"""Reading a bank statement, whatever bank wrote it.

A Fio export has a published, stable column layout and is parsed exactly. Any
other bank's export is read as a table and interpreted by a language model, the
same treatment `importer` already gives a registration table (design
add-payments-intake D1).

The parsed rows are cached per row fingerprint, so re-uploading a corrected
statement interprets only what actually changed.
"""

import re
from collections.abc import Callable

from sqlalchemy.orm import Session

from app import bank, importer
from app.models import Tournament

# what a parsed statement row is stored under, beside "parse" and the rest
DECISION_KIND = "statement_row"


# A statement is a table of dated amounts, whatever else a bank puts around
# them. These say only "this column reads as a date" and "this one reads as a
# number" — never which column means what, which stays the model's job and is
# what keeps the reader bank-agnostic (design D1).
_DATE = re.compile(
    r"\s*(?:"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"  # 02.04.2026, 2/4/26, 02-04-2026
    r"|\d{4}[./-]\d{1,2}[./-]\d{1,2}"  # 2026-04-02
    r")(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\s*$"
)
# an amount: optional sign, digits grouped by space, nbsp or apostrophe, and a
# comma or dot decimal — plus an optional trailing currency word (12,00 EUR)
_AMOUNT = re.compile(r"\s*[-+]?\d{1,3}(?:[  '\u00a0]?\d{3})*(?:[.,]\d+)?\s*[A-Za-z]{0,3}\s*$")

# how much of a column has to read that way for the column to count. Not every
# value: a bank writes the odd summary or fee line, and refusing a statement
# over one of them would be worse than the misreading this guards against.
_SHARE = 0.7


class UnreadableStatementError(ValueError):
    """The table is not a statement, or was not read as one.

    Raised before any model is asked, so a file that trivial parsing already
    shows to be wrong costs nothing to reject. The misreading this exists for
    is a delimiter the reader guessed wrong: the whole line arrives as one
    column, no column reads as a date or an amount, and the model is left to
    invent an answer from mangled text (`importer.sniff_delimiter`)."""

    def __init__(self, missing: str):
        self.missing = missing
        super().__init__(f"no column reads as {missing}")


def _column_reads_as(values: list[str], pattern: re.Pattern) -> bool:
    filled = [v for v in values if v.strip()]
    if not filled:
        return False
    return sum(bool(pattern.match(v)) for v in filled) >= _SHARE * len(filled)


def check_readable(rows: list[dict[str, str]]) -> None:
    """Refuse a table that cannot be a statement, before spending a model call.

    A statement has a column of dates and a column of amounts. Neither has to be
    named anything in particular — banks name them in their own language — but
    both have to be *there*, and a table where neither is has either been read
    wrongly or is not a statement at all.
    """
    if not rows:
        raise UnreadableStatementError("a date")
    columns = {key: [row.get(key, "") for row in rows] for key in rows[0]}
    for missing, pattern in (("a date", _DATE), ("an amount", _AMOUNT)):
        if not any(_column_reads_as(values, pattern) for values in columns.values()):
            raise UnreadableStatementError(missing)


class NoStatementParserError(RuntimeError):
    """An unrecognised statement arrived on a deployment with no model
    configured. Nothing can be read from it, and saying so is better than
    ingesting an empty statement as if it held no payments."""


def read_rows(filename: str, data: bytes) -> list[dict[str, str]]:
    """The statement as header-keyed rows. Raises
    `importer.UnsupportedFormatError` for a file that is neither CSV nor
    XLSX."""
    return importer.read_table(filename, data)


def undecided(
    session: Session, tournament: Tournament, rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    """The rows no stored decision covers yet, each distinct row once.

    A statement can repeat a row exactly: two identical payments on one day
    from a bank that numbers nothing leave two byte-identical lines, and both
    key the same decision. Handing both to `parse` asks the model to interpret
    the same row twice and then stores the answer under one key twice, which
    the (tournament, kind, key) uniqueness refuses mid-batch.

    Collapsing them here decides nothing about the money — the caller still
    walks every row, and the second one's transaction collides with the first
    on `external_id` at ingestion and counts duplicate, which is the same
    answer by design (bank.to_transaction, design D2).
    """
    seen: set[str] = set()
    pending = []
    for raw in rows:
        key = importer.row_fingerprint(raw)
        if key in seen:
            continue
        seen.add(key)
        if importer.get_decision(session, tournament, DECISION_KIND, key) is None:
            pending.append(raw)
    return pending


def parse(
    session: Session,
    tournament: Tournament,
    rows: list[dict[str, str]],
    parser: bank.StatementParser,
    progress: Callable[[Session, int], None] | None = None,
) -> list[bank.IncomingTransaction]:
    """Interpret the rows that need it, then return every row's transaction.

    Each batch's decisions and the progress they represent commit together, so
    a run that stops partway leaves what it interpreted standing and a rerun
    does only the remainder. `progress` is what commits — the caller passes the
    one that also raises the operation's count.
    """
    commit = progress or (lambda session, _units: session.commit())
    pending = undecided(session, tournament, rows)
    for group in importer.batches(pending):
        records = parser.parse_batch(group)
        for raw, record in zip(group, records, strict=True):
            importer.store_decision(
                session,
                tournament,
                DECISION_KIND,
                importer.row_fingerprint(raw),
                record.model_dump(mode="json"),
            )
        commit(session, len(group))

    transactions = []
    for raw in rows:
        decision = importer.get_decision(
            session, tournament, DECISION_KIND, importer.row_fingerprint(raw)
        )
        if decision is None:
            continue
        row = bank.ParsedStatementRow.model_validate(decision.payload)
        # money leaving the account is not somebody's entry fee; the parser is
        # told to report it rather than hide it, and it is dropped here where
        # the reason can be stated once (design D2)
        if row.amount_cents <= 0:
            continue
        transactions.append(bank.to_transaction(row, raw))
    return transactions


def statement_units(filename: str, data: bytes) -> int:
    """How many units of work importing this statement is, for the operation's
    total. A Fio export is one unit: it parses exactly and instantly."""
    if bank.is_fio_export(data):
        return 1
    try:
        return max(len(read_rows(filename, data)), 1)
    except importer.UnsupportedFormatError:
        return 1
