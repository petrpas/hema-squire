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
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rownumbers
from app.llm import get_model, llm_configured
from app.models import (
    ExtraCategory,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    Tournament,
)

if TYPE_CHECKING:
    from pydantic_ai.models import Model

# an offered discipline as handed to the parser: (slug, name) — the name is
# where a tier, a bracket, or a weapon the taxonomy does not know lives, so it
# is what the model actually matches on (design discipline-identity D7)
OfferedDiscipline = tuple[str, str]

# an item the tournament lends, by the name the sheet shows it under. Free of
# the weapon taxonomy on purpose: an organizer lends whatever they own, and a
# buckler or a mask is no weapon (models.ExtraCategory.RENTAL)
OfferedRental = str

PARSE_BATCH_SIZE = 20


class UnsupportedFormatError(ValueError):
    pass


def read_table(filename: str, data: bytes) -> list[dict[str, str]]:
    """Read an uploaded CSV or XLSX into a list of header-keyed row dicts."""
    name = filename.lower()
    if name.endswith(".csv"):
        text = data.decode("utf-8-sig")
        # a blank line is not a fencer. The XLSX reader below already skips
        # them; without the same guard here a trailing empty line becomes a row,
        # reaches the parser, and comes back named whatever the model invents
        # for a record with nothing in it
        return [
            dict(row)
            for row in csv.DictReader(io.StringIO(text))
            if any((value or "").strip() for value in row.values())
        ]
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
    disciplines: list[str] = Field(
        default=[], description="Slugs chosen from the tournament's offered disciplines."
    )
    borrow: list[str] = Field(
        default=[], description="Names chosen from the tournament's offered rentals."
    )
    after_party: Literal["Yes", "No", "Oth"] | None = None
    aftersparring: Literal["Yes", "No", "Oth"] | None = None
    accommodation: str | None = None
    notes: str | None = Field(
        default=None, description="Anything from the form that fits no other field."
    )
    problems: str | None = Field(
        default=None, description="Parsing doubts, listed for organizer review."
    )

    @field_validator("disciplines", "borrow")
    @classmethod
    def _entered_once(cls, values: list[str]) -> list[str]:
        """Both fields are sets: a fencer enters a discipline once and borrows
        one of an item. A source row repeats itself easily — it names the
        weapon it lends per discipline — and the repeat means nothing here."""
        return list(dict.fromkeys(values))


class ImportParser(Protocol):
    """One batch per call. The loop over batches belongs to the caller, which
    is what lets each batch's decisions and the progress they represent commit
    together (design D4) — and what a concurrent parse would replace without
    touching the parser."""

    def parse_batch(
        self,
        rows: list[dict[str, str]],
        disciplines: list[OfferedDiscipline],
        rentals: list[OfferedRental],
    ) -> list[ParsedFencer]: ...


_SYSTEM_PROMPT = """\
You are a data-cleaning assistant for a HEMA (Historical European Martial Arts) tournament.
You receive a batch of records from a registration table and must output a clean,
structured fencer record for each. Return exactly one record per input row, in order.

Disciplines offered by this tournament (slug — name): {disciplines}
Items this tournament lends, by name: {rentals}

Rules:
1. hr_id: a plain integer as-is; empty or any non-numeric text ("N/A", "Don't have") -> null.
2. disciplines: choose the slug of the matching offered discipline. Match on the name,
   which is where a tier, a bracket, or a weapon not in the usual HEMA taxonomy is named.
   Only use slugs from the offered list, nothing else, and each slug at most once.
3. If a row's content could match more than one offered discipline and does not say which
   (for example it names only a weapon that the tournament splits into several brackets),
   do not guess: leave that discipline out of the row and note the ambiguity in problems.
4. Content that fits no field goes to notes. Parsing doubts go to problems.
5. after_party / aftersparring: map local phrasing to Yes/No/Oth; null if the column is absent.
6. accommodation: copy free text; null if absent or empty.
7. borrow: the lent items the row asks for, named exactly as the offered list names
   them. One of each is lent, so name an item once however often the row repeats it —
   a row entered in two disciplines commonly asks for the same weapon in each. An item
   asked for that this tournament does not lend goes to problems, not to borrow.
"""


class _ParsedBatch(BaseModel):
    fencers: list[ParsedFencer]


class LLMImportParser:
    """pydantic-ai parser over Anthropic; the only LLM call site on this path.

    One call, one batch. Batching is the caller's, so a batch's decisions are
    stored the moment they arrive rather than after the whole file (design D4).
    """

    def __init__(self, model: Model):
        self._model = model

    def parse_batch(
        self,
        rows: list[dict[str, str]],
        disciplines: list[OfferedDiscipline],
        rentals: list[OfferedRental],
    ) -> list[ParsedFencer]:
        from pydantic_ai import Agent

        offered = ", ".join(f"{slug} — {name}" for slug, name in disciplines)
        lent = ", ".join(rentals) if rentals else "nothing — leave borrow empty"
        agent = Agent(
            model=self._model,
            output_type=_ParsedBatch,
            system_prompt=_SYSTEM_PROMPT.format(disciplines=offered, rentals=lent),
            retries=3,
        )
        result = agent.run_sync(
            f"Parse the following {len(rows)} registration rows in order:\n\n"
            f"```json\n{json.dumps(rows, ensure_ascii=False)}\n```\n\n"
            f"Return exactly {len(rows)} records in the same order."
        )
        return list(result.output.fencers)


def get_import_parser() -> ImportParser | None:
    if not llm_configured():
        return None
    return LLMImportParser(get_model())


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


def intake(
    session: Session,
    tournament: Tournament,
    filename: str,
    data: bytes,
    uploaded_by: int,
) -> tuple[ImportBatch, list[ImportedRow]]:
    """File intake: persist the batch with its provenance, its source rows and
    their numbers, and commit.

    This half runs inside the request, so a browser that abandons the upload
    response still leaves a complete batch behind (spec table-import, Batch
    survives an abandoned upload response). Only the parsing that follows is
    background work.
    """
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

    # in file order, and only for keys not already numbered: a re-upload of an
    # unchanged row keeps its fingerprint, so it keeps its number
    rownumbers.allocate(session, tournament, [f"imp:{row.key}" for row in imported])
    session.commit()
    return batch, imported


def batch_rows(session: Session, batch: ImportBatch) -> list[ImportedRow]:
    return list(
        session.scalars(
            select(ImportedRow)
            .where(ImportedRow.batch_id == batch.id)
            .order_by(ImportedRow.row_number)
        )
    )


def undecided_rows(
    session: Session, tournament: Tournament, imported: list[ImportedRow]
) -> list[ImportedRow]:
    """The rows this run will actually parse. A row with a stored decision is
    reused, not work, and is not counted towards an operation's total (spec
    console-operations, Reused rows are not work)."""
    return [
        row for row in imported if get_decision(session, tournament, "parse", row.key) is None
    ]


def batches(rows: list[ImportedRow], size: int = PARSE_BATCH_SIZE) -> list[list[ImportedRow]]:
    return [rows[start : start + size] for start in range(0, len(rows), size)]


def import_outcome(
    session: Session,
    tournament: Tournament,
    batch: ImportBatch,
    imported: list[ImportedRow],
    parsed: int,
    reused: int,
    unparsed: int = 0,
    detail: str | None = None,
) -> dict:
    """What the console reports about a run — the shape the endpoint used to
    return synchronously, now stored on the operation."""
    problems = []
    for row in imported:
        decision = get_decision(session, tournament, "parse", row.key)
        if decision and decision.payload.get("problems"):
            problems.append({"row": row.row_number, "problems": decision.payload["problems"]})
    outcome = {
        "batch_id": batch.id,
        "rows": len(imported),
        "parsed": parsed,
        "reused": reused,
        "unparsed": unparsed,
        "problems": problems,
    }
    if detail is not None:
        outcome["detail"] = detail
    return outcome


def parse_undecided(
    session: Session,
    tournament: Tournament,
    parser: ImportParser,
    batch: ImportBatch,
    imported: list[ImportedRow],
    undecided: list[ImportedRow],
    progress: Callable[[Session, int], None] | None = None,
) -> dict:
    """Parse the undecided rows, one batch at a time, storing as it goes.

    Each batch's decisions and the progress they represent are committed
    together, so a run that stops partway leaves what it had parsed standing and
    a rerun does only the remainder (spec table-import, Partial parse survives
    an interruption). `progress` is what commits — the caller passes the one
    that also raises the operation's count.

    The loop lives here rather than inside the parser so that making it
    concurrent later touches this function and nothing else (design D6).
    """
    commit = progress or (lambda session, _units: session.commit())
    offered = [(d.slug, d.name) for d in tournament.disciplines]
    lent = [
        item.name
        for item in tournament.extra_items
        if item.category == ExtraCategory.RENTAL
    ]
    parsed_count = 0
    for group in batches(undecided):
        records = parser.parse_batch([row.raw for row in group], offered, lent)
        for row, record in zip(group, records, strict=True):
            store_decision(session, tournament, "parse", row.key, record.model_dump())
        parsed_count += len(group)
        commit(session, len(group))

    return import_outcome(
        session,
        tournament,
        batch,
        imported,
        parsed=parsed_count,
        reused=len(imported) - len(undecided),
    )
