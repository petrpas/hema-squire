"""External table import: file intake and LLM parsing into canonical records.

Raw rows are source records; the LLM parse of a row is a cached decision keyed
by the row's content fingerprint (spec: reruns reuse stored decisions, only
undecided rows invoke the LLM). The newest batch is the active source — a
re-upload replaces the projection, and unchanged rows keep their fingerprint,
so decisions and rules targeting them survive.

The FastAPI dependency `get_import_parser` is the swap point between the real
pydantic-ai parser and test fakes.
"""

import csv
import hashlib
import io
import json
from typing import Literal, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ImportBatch, ImportDecision, ImportedRow, Tournament

PARSE_BATCH_SIZE = 20


class UnsupportedFormatError(ValueError):
    pass


def read_table(filename: str, data: bytes) -> list[dict[str, str]]:
    """Read an uploaded CSV or XLSX into a list of header-keyed row dicts."""
    name = filename.lower()
    if name.endswith(".csv"):
        text = data.decode("utf-8-sig")
        return [dict(row) for row in csv.DictReader(io.StringIO(text))]
    if name.endswith(".xlsx"):
        import openpyxl

        workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        rows_iter = workbook.active.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            return []
        keys = [str(cell) if cell is not None else "" for cell in header]
        return [
            {
                key: "" if cell is None else str(cell)
                for key, cell in zip(keys, row, strict=False)
            }
            for row in rows_iter
            if any(cell is not None and str(cell).strip() for cell in row)
        ]
    raise UnsupportedFormatError(filename)


def row_fingerprint(raw: dict[str, str]) -> str:
    canonical = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class ParsedDiscipline(BaseModel):
    weapon: Literal["LS", "SA", "RA", "RD", "SB"]
    gender: Literal["", "W", "M", "O"] = Field(
        default="", description="Open when not explicitly stated; O normalizes to ''."
    )
    material: Literal["", "Steel", "Plastic"] = Field(
        default="", description="Steel when not explicitly stated."
    )

    @property
    def code(self) -> str:
        material = "" if self.material in ("", "Steel") else self.material
        gender = self.gender if self.gender in ("W", "M") else ""
        return f"{material} {self.weapon}{gender}".strip()


class ParsedFencer(BaseModel):
    """The canonical fencer record an imported row parses into (v1-proven shape)."""

    registration_time: str = Field(description="ISO format, e.g. 2026-03-14T15:32:52")
    name: str = Field(description="Full name, first name first.")
    reg_name: str | None = Field(
        default=None,
        description="Original name from the form when a canonical name was applied.",
    )
    nationality: str = Field(default="", description="Abbreviation, e.g. CZ, DE.")
    email: str | None = None
    club: str | None = None
    hr_id: int | None = Field(
        default=None, description="Plain integer, or null for any non-numeric content."
    )
    disciplines: list[ParsedDiscipline] = []
    borrow: list[Literal["LS", "SA", "RA", "RD", "SB"]] = []
    after_party: Literal["Yes", "No", "Oth"] | None = None
    aftersparring: Literal["Yes", "No", "Oth"] | None = None
    accommodation: str | None = None
    notes: str | None = Field(
        default=None, description="Anything from the form that fits no other field."
    )
    problems: str | None = Field(
        default=None, description="Parsing doubts, listed for organizer review."
    )


class ImportParser(Protocol):
    def parse(self, rows: list[dict[str, str]], disciplines: list[str]) -> list[ParsedFencer]: ...


_SYSTEM_PROMPT = """\
You are a data-cleaning assistant for a HEMA (Historical European Martial Arts) tournament.
You receive a batch of records from a registration table and must output a clean,
structured fencer record for each. Return exactly one record per input row, in order.

HEMA weapons: LS Longsword, SA Sabre, RA Rapier, RD Rapier and Dagger, SB Sword and Buckler.
A discipline is weapon + gender (M men, W women, open when unstated) + material
(steel when unstated; "Plastic SA" means plastic sabre open).

Disciplines offered by this tournament: {disciplines}

Rules:
1. hr_id: a plain integer as-is; empty or any non-numeric text ("N/A", "Don't have") -> null.
2. Only use disciplines offered by this tournament, nothing else.
3. Content that fits no field goes to notes. Parsing doubts go to problems.
4. after_party / aftersparring: map local phrasing to Yes/No/Oth; null if the column is absent.
5. accommodation: copy free text; null if absent or empty.
"""


class _ParsedBatch(BaseModel):
    fencers: list[ParsedFencer]


class LLMImportParser:
    """pydantic-ai parser over Anthropic; the only LLM call site on this path."""

    def __init__(self, model: str, batch_size: int = PARSE_BATCH_SIZE):
        self._model = model
        self._batch_size = batch_size

    def parse(self, rows: list[dict[str, str]], disciplines: list[str]) -> list[ParsedFencer]:
        from pydantic_ai import Agent
        from pydantic_ai.settings import ModelSettings

        agent = Agent(
            model=self._model,
            model_settings=ModelSettings(temperature=0.0),
            output_type=_ParsedBatch,
            system_prompt=_SYSTEM_PROMPT.format(disciplines=", ".join(disciplines)),
            retries=3,
        )
        parsed: list[ParsedFencer] = []
        for start in range(0, len(rows), self._batch_size):
            batch = rows[start : start + self._batch_size]
            result = agent.run_sync(
                f"Parse the following {len(batch)} registration rows in order:\n\n"
                f"```json\n{json.dumps(batch, ensure_ascii=False)}\n```\n\n"
                f"Return exactly {len(batch)} records in the same order."
            )
            parsed.extend(result.output.fencers)
        return parsed


def get_import_parser() -> ImportParser | None:
    if not settings.anthropic_api_key:
        return None
    import os

    os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    return LLMImportParser(settings.llm_model)


def latest_batch(session: Session, tournament: Tournament) -> ImportBatch | None:
    return session.scalars(
        select(ImportBatch)
        .where(ImportBatch.tournament_id == tournament.id)
        .order_by(ImportBatch.id.desc())
        .limit(1)
    ).first()


def get_decision(
    session: Session, tournament: Tournament, kind: str, key: str
) -> ImportDecision | None:
    return session.scalars(
        select(ImportDecision).where(
            ImportDecision.tournament_id == tournament.id,
            ImportDecision.kind == kind,
            ImportDecision.key == key,
        )
    ).first()


def store_decision(
    session: Session,
    tournament: Tournament,
    kind: str,
    key: str,
    payload: dict,
    source: str = "llm",
) -> ImportDecision:
    decision = get_decision(session, tournament, kind, key)
    if decision is None:
        decision = ImportDecision(
            tournament_id=tournament.id, kind=kind, key=key, source=source
        )
        session.add(decision)
    decision.payload = payload
    decision.source = source
    return decision


def import_table(
    session: Session,
    tournament: Tournament,
    parser: ImportParser | None,
    filename: str,
    data: bytes,
    uploaded_by: int,
) -> dict:
    """File intake: persist the batch with provenance, then LLM-parse only the
    rows without a stored parse decision."""
    raw_rows = read_table(filename, data)
    batch = ImportBatch(
        tournament_id=tournament.id,
        filename=filename,
        uploaded_by=uploaded_by,
        row_count=len(raw_rows),
    )
    session.add(batch)
    session.flush()

    seen: dict[str, int] = {}
    imported: list[ImportedRow] = []
    for number, raw in enumerate(raw_rows, start=1):
        fingerprint = row_fingerprint(raw)
        # identical duplicate rows get distinct keys; dedup decides their fate
        occurrence = seen.get(fingerprint, 0)
        seen[fingerprint] = occurrence + 1
        key = fingerprint if occurrence == 0 else f"{fingerprint}-{occurrence + 1}"
        row = ImportedRow(
            batch_id=batch.id,
            tournament_id=tournament.id,
            row_number=number,
            key=key,
            raw=raw,
        )
        session.add(row)
        imported.append(row)

    undecided = [
        row for row in imported if get_decision(session, tournament, "parse", row.key) is None
    ]
    parsed_count = 0
    if undecided:
        if parser is None:
            session.commit()
            return {
                "batch_id": batch.id,
                "rows": len(imported),
                "parsed": 0,
                "reused": len(imported) - len(undecided),
                "unparsed": len(undecided),
                "problems": [],
                "detail": "llm_not_configured",
            }
        discipline_codes = [d.code for d in tournament.disciplines]
        parsed = parser.parse([row.raw for row in undecided], discipline_codes)
        for row, record in zip(undecided, parsed, strict=True):
            store_decision(session, tournament, "parse", row.key, record.model_dump())
        parsed_count = len(parsed)

    session.commit()

    problems = []
    for row in imported:
        decision = get_decision(session, tournament, "parse", row.key)
        if decision and decision.payload.get("problems"):
            problems.append({"row": row.row_number, "problems": decision.payload["problems"]})
    return {
        "batch_id": batch.id,
        "rows": len(imported),
        "parsed": parsed_count,
        "reused": len(imported) - len(undecided),
        "unparsed": 0,
        "problems": problems,
    }
