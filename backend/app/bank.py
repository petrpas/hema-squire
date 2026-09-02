"""Bank transaction ingestion: Fio REST API and CSV statement import feed one
idempotent interface keyed by the bank's transaction id."""

import csv
import datetime
import io
import json
import re
from decimal import Decimal
from typing import Protocol

import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankTransaction, Tournament

FIO_API_BASE = "https://fioapi.fio.cz/v1/rest"


def require_payments_enabled(tournament: Tournament) -> None:
    """Refuse a reconciliation request against a tournament whose payments
    feature is off (design tournament-modes D5). Such a tournament has no
    money in flight for Squire to reconcile, and an organizer uploading a
    statement against the wrong tournament must learn that rather than watch
    it disappear — so this refuses rather than accepting with no effect.

    Lives beside ingestion because ingestion is the first thing every
    reconciliation path does; matching and the payments endpoints call it
    directly for the paths that skip it."""
    if not tournament.feature_payments:
        raise HTTPException(status_code=409, detail="payments_disabled")


class IncomingTransaction(BaseModel):
    external_id: str
    date: datetime.date
    amount_cents: int
    currency: str
    vs: int | None = None
    message: str | None = None
    payer_name: str | None = None
    payer_account: str | None = None
    # additional text-bearing Fio fields that carry SEPA references on some
    # routings (design harden-payment-matching Decision 4); deliberately not
    # payer_name/payer_account, which are structured identifiers, not text
    user_identification: str | None = None
    comment: str | None = None
    specification: str | None = None
    specific_symbol: str | None = None


class IngestResult(BaseModel):
    new: int
    duplicate: int


def ingest(
    session: Session,
    tournament: Tournament,
    source: str,
    transactions: list[IncomingTransaction],
) -> IngestResult:
    """Store transactions at most once per (tournament, external_id)."""
    require_payments_enabled(tournament)
    seen = set(
        session.scalars(
            select(BankTransaction.external_id).where(
                BankTransaction.tournament_id == tournament.id,
                BankTransaction.external_id.in_([t.external_id for t in transactions]),
            )
        )
    )
    new = 0
    for transaction in transactions:
        if transaction.external_id in seen:
            continue
        seen.add(transaction.external_id)
        session.add(
            BankTransaction(
                tournament_id=tournament.id,
                source=source,
                **transaction.model_dump(),
            )
        )
        new += 1
    session.commit()
    return IngestResult(new=new, duplicate=len(transactions) - new)


# --- Fio JSON (REST API) ---

_FIO_COLUMNS = {
    "external_id": "column22",  # ID pohybu
    "date": "column0",
    "amount": "column1",
    "currency": "column14",
    "vs": "column5",
    "message": "column16",  # zpráva pro příjemce
    "payer_name": "column10",
    "payer_account": "column2",
    "user_identification": "column7",
    "comment": "column25",
    "specification": "column18",
    "specific_symbol": "column6",
}


def _fio_value(row: dict, key: str):
    cell = row.get(_FIO_COLUMNS[key])
    return None if cell is None else cell.get("value")


def parse_fio_json(payload: dict) -> list[IncomingTransaction]:
    rows = (
        payload.get("accountStatement", {}).get("transactionList", {}).get("transaction", [])
    )
    result = []
    for row in rows:
        vs_raw = _fio_value(row, "vs")
        result.append(
            IncomingTransaction(
                external_id=str(_fio_value(row, "external_id")),
                date=datetime.date.fromisoformat(str(_fio_value(row, "date"))[:10]),
                amount_cents=int(round(Decimal(str(_fio_value(row, "amount"))) * 100)),
                # Fio omits the currency on domestic statements, which are
                # always CZK by definition of the format — not an app-level
                # assumption about what a tournament prices in
                currency=str(_fio_value(row, "currency") or "CZK"),
                vs=int(vs_raw) if vs_raw not in (None, "") else None,
                message=_fio_value(row, "message"),
                payer_name=_fio_value(row, "payer_name"),
                payer_account=_fio_value(row, "payer_account"),
                user_identification=_fio_value(row, "user_identification"),
                comment=_fio_value(row, "comment"),
                specification=_fio_value(row, "specification"),
                specific_symbol=_fio_value(row, "specific_symbol"),
            )
        )
    return result


# --- Fio CSV statement export ---

_CSV_FIELDS = {
    "ID pohybu": "external_id",
    "Datum": "date",
    "Objem": "amount",
    "Měna": "currency",
    "VS": "vs",
    "Zpráva pro příjemce": "message",
    "Název protiúčtu": "payer_name",
    "Protiúčet": "payer_account",
    "Uživatelská identifikace": "user_identification",
    "Komentář": "comment",
    "Upřesnění": "specification",
    "SS": "specific_symbol",
}


def _parse_amount_cents(raw: str) -> int:
    normalized = raw.replace("\xa0", "").replace(" ", "").replace(",", ".")
    return int(round(Decimal(normalized) * 100))


def _parse_date(raw: str) -> datetime.date:
    raw = raw.strip()
    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", raw):
        return datetime.datetime.strptime(raw, "%d.%m.%Y").date()
    return datetime.date.fromisoformat(raw[:10])


def parse_fio_csv(content: bytes) -> list[IncomingTransaction]:
    text = content.decode("utf-8-sig")
    lines = text.splitlines()
    header_index = next(
        (i for i, line in enumerate(lines) if "ID pohybu" in line), None
    )
    if header_index is None:
        raise ValueError("no 'ID pohybu' header found — not a Fio statement export")

    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])), delimiter=";")
    result = []
    for row in reader:
        record = {
            field: (row.get(column) or "").strip() for column, field in _CSV_FIELDS.items()
        }
        if not record["external_id"]:
            continue
        result.append(
            IncomingTransaction(
                external_id=record["external_id"],
                date=_parse_date(record["date"]),
                amount_cents=_parse_amount_cents(record["amount"]),
                currency=record["currency"] or "CZK",  # see parse_fio_json
                vs=int(record["vs"]) if record["vs"] else None,
                message=record["message"] or None,
                payer_name=record["payer_name"] or None,
                payer_account=record["payer_account"] or None,
                user_identification=record["user_identification"] or None,
                comment=record["comment"] or None,
                specification=record["specification"] or None,
                specific_symbol=record["specific_symbol"] or None,
            )
        )
    return result


# --- Statement import: any bank's table ---


class ParsedStatementRow(BaseModel):
    """One row of an arbitrary bank's export, as the parser reads it.

    Deliberately looser than `IncomingTransaction`: `external_id` is optional,
    because a bank that supplies no movement id of its own is exactly the case
    this path exists for, and the caller fills it from the row's fingerprint.
    """

    external_id: str | None = None
    date: datetime.date
    amount_cents: int
    currency: str = "CZK"
    vs: int | None = None
    message: str | None = None
    payer_name: str | None = None
    payer_account: str | None = None


class StatementParser(Protocol):
    """One batch per call. The loop over batches belongs to the caller, which
    is what lets each batch's decisions commit with the progress they
    represent — the same contract as `importer.ImportParser`."""

    def parse_batch(self, rows: list[dict[str, str]]) -> list[ParsedStatementRow]: ...


_STATEMENT_SYSTEM_PROMPT = """\
You read rows from a bank account statement and turn each into a structured
payment record. The account belongs to a HEMA tournament, and the rows are
incoming transfers from people paying their entry fee. Return exactly one
record per input row, in order.

Rules:
1. amount_cents: an integer number of cents, signed. Banks write amounts in
   many ways — "1 200,00", "1.200,00", "1200.00", or a positive number in a
   separate credit column with debits in another. Read the row's own
   convention and convert. Never round to whole units.
2. Set amount_cents negative for money leaving the account. The caller drops
   those; do not omit the row yourself, and do not turn a debit into a credit.
3. date: the date the money moved. Prefer a settlement/posting date over a
   value date where the row carries both.
4. vs: the Czech variable symbol (variabilní symbol), the number identifying
   which registration is being paid. It is often its own column, but may sit
   inside the payment message. A number that is plainly something else — an
   account number, a constant or specific symbol — is not a VS. Null if absent.
5. message: whatever free text the payer sent with the payment, verbatim.
6. payer_name / payer_account: the counterparty's name and account, null if
   the row does not carry them.
7. external_id: the bank's own identifier for the movement, if the row has
   one. Null if it does not — do not invent one, and never use the row number.
8. currency: the ISO code (CZK, EUR). Default to CZK only if nothing states it.
"""


class _ParsedStatement(BaseModel):
    rows: list[ParsedStatementRow]


class LLMStatementParser:
    """pydantic-ai parser over Anthropic, mirroring `importer.LLMImportParser`.

    Reached only for a statement that is not a Fio export: a published, stable
    column layout is not a guessing problem (design D1).
    """

    def __init__(self, model):
        self._model = model

    def parse_batch(self, rows: list[dict[str, str]]) -> list[ParsedStatementRow]:
        from pydantic_ai import Agent

        agent = Agent(
            model=self._model,
            output_type=_ParsedStatement,
            system_prompt=_STATEMENT_SYSTEM_PROMPT,
            retries=3,
        )
        result = agent.run_sync(
            f"Parse the following {len(rows)} statement rows in order:\n\n"
            f"```json\n{json.dumps(rows, ensure_ascii=False)}\n```\n\n"
            f"Return exactly {len(rows)} records in the same order."
        )
        return list(result.output.rows)


def get_statement_parser() -> StatementParser | None:
    """None where no model is configured — the injection point tests override,
    exactly as `importer.get_import_parser` is."""
    from app.llm import get_model, llm_configured

    if not llm_configured():
        return None
    return LLMStatementParser(get_model())


def is_fio_export(data: bytes) -> bool:
    """The same test `parse_fio_csv` uses to find its header, so the sniff and
    the parser can never disagree about what a Fio file is."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return any("ID pohybu" in line for line in text.splitlines())


def to_transaction(row: ParsedStatementRow, raw: dict[str, str]) -> IncomingTransaction:
    """A parsed row as the ingest interface takes it.

    Where the bank supplied no id, the row's own fingerprint becomes one.
    Ingestion dedupes on `external_id`, so the same row read twice collides
    with itself and is counted duplicate — which is what keeps import
    idempotent on a bank that numbers nothing (design D2)."""
    from app.importer import row_fingerprint

    return IncomingTransaction(
        external_id=row.external_id or f"row:{row_fingerprint(raw)}",
        date=row.date,
        amount_cents=row.amount_cents,
        currency=row.currency or "CZK",
        vs=row.vs,
        message=row.message,
        payer_name=row.payer_name,
        payer_account=row.payer_account,
    )


# --- Fio REST client (swappable for tests via get_fio_client) ---


class FioClient(Protocol):
    def fetch(self, token: str, date_from: datetime.date, date_to: datetime.date) -> list[
        IncomingTransaction
    ]: ...


class HttpFioClient:
    def fetch(
        self, token: str, date_from: datetime.date, date_to: datetime.date
    ) -> list[IncomingTransaction]:
        url = f"{FIO_API_BASE}/periods/{token}/{date_from}/{date_to}/transactions.json"
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        return parse_fio_json(response.json())


_client = HttpFioClient()


def get_fio_client() -> FioClient:
    return _client
