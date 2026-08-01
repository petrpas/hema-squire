"""Bank transaction ingestion: Fio REST API and CSV statement import feed one
idempotent interface keyed by the bank's transaction id."""

import csv
import datetime
import io
import re
from decimal import Decimal
from typing import Protocol

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankTransaction, Tournament

FIO_API_BASE = "https://fioapi.fio.cz/v1/rest"


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
