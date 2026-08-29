from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import dedup, hr_match, importclear, importer, operations, rules, sheet
from app.auth import require_console_access
from app.hr_index import HRIndex, get_hr_index
from app.models import Fencer, Operation, OperationKind, Tournament
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep

router = APIRouter(prefix="/api/tournaments/{slug}/import", tags=["import"])

ParserDep = Annotated[importer.ImportParser | None, Depends(importer.get_import_parser)]
MatcherDep = Annotated[hr_match.HRMatcher | None, Depends(hr_match.get_hr_matcher)]
DedupDep = Annotated[dedup.DedupLLM | None, Depends(dedup.get_dedup_llm)]
HRIndexDep = Annotated[HRIndex, Depends(get_hr_index)]


def _replayed_import_rows(session, tournament, index=None) -> list[dict]:
    """The rows matching and deduplication work on: the ones that entered
    unmatched. An in-app registration is HR-bound at birth and stays out of it;
    an imported row and a hand-entered one both traverse the two operations
    (spec etl-console, Per-row phase status)."""
    base = sheet.base_rows(session, tournament, index)
    rows, _ = rules.replay(base, rules.active_rules(session, tournament))
    return [
        row for row in rows.values() if row["id"].startswith(("imp:", "man:"))
    ]


def _refuse_while_busy(session: Session, tournament: Tournament) -> None:
    """One operation at a time for a tournament, whatever its kind. The record
    is what refuses, so this holds for a second tab and a second organizer, not
    only for the page offering the action (spec console-operations, One
    operation at a time for a tournament)."""
    in_flight = operations.running(session, tournament)
    if in_flight is not None:
        raise HTTPException(
            status_code=409, detail={"code": "operation_running", "kind": in_flight.kind.value}
        )


def _start(
    session: Session,
    tournament: Tournament,
    fencer: FencerDep,
    kind: OperationKind,
    total: int,
) -> Operation:
    try:
        return operations.start(session, tournament, kind, total, fencer.id)
    except operations.OperationInFlightError as busy:
        raise HTTPException(
            status_code=409, detail={"code": "operation_running", "kind": busy.kind.value}
        ) from None


@router.post("", status_code=202)
async def import_table(
    file: UploadFile,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    parser: ParserDep,
):
    """Read the file and record its batch here; parse it behind the request.

    The batch and its rows land before this returns, so an abandoned response
    still leaves the upload whole — only the LLM parse, which is what takes the
    minutes, runs as an operation (design D2).
    """
    require_console_access(session, tournament, fencer)
    _refuse_while_busy(session, tournament)
    data = await file.read()
    try:
        batch, imported = importer.intake(
            session, tournament, file.filename or "upload.csv", data, fencer.id
        )
    except importer.UnsupportedFormatError:
        raise HTTPException(status_code=422, detail="unsupported_format") from None

    undecided = importer.undecided_rows(session, tournament, imported)
    if not undecided or parser is None:
        # nothing to run: an all-reused re-upload, or a deployment with no LLM.
        # Starting an operation with nothing to do would report a long parse
        # that never happened (spec, Reused rows are not work).
        return importer.import_outcome(
            session,
            tournament,
            batch,
            imported,
            parsed=0,
            reused=len(imported) - len(undecided),
            unparsed=len(undecided),
            detail="llm_not_configured" if undecided else None,
        )

    operation = _start(session, tournament, fencer, OperationKind.PARSE, len(undecided))
    batch_id = batch.id

    def body(work_session: Session, work_operation: Operation) -> dict:
        work_tournament = work_session.get(Tournament, work_operation.tournament_id)
        work_batch = work_session.get(importer.ImportBatch, batch_id)
        rows = importer.batch_rows(work_session, work_batch)
        return importer.parse_undecided(
            work_session,
            work_tournament,
            parser,
            work_batch,
            rows,
            importer.undecided_rows(work_session, work_tournament, rows),
            progress=lambda session, units: operations.advance(session, work_operation, units),
        )

    operations.run_in_background(operation.id, body)
    return {"operation_id": operation.id, "batch_id": batch_id, "rows": len(imported)}


@router.delete("")
def clear_import(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Remove everything the tournament ever imported. Hard, total and final —
    the console confirms it before calling (spec table-import, Clearing is
    warned about and irreversible)."""
    require_console_access(session, tournament, fencer)
    return importclear.clear_imports(session, tournament)


@router.post("/match", status_code=202)
async def run_matching(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    matcher: MatcherDep,
    index: HRIndexDep,
):
    require_console_access(session, tournament, fencer)
    if matcher is None:
        raise HTTPException(status_code=503, detail="llm_not_configured")
    rows = _replayed_import_rows(session, tournament, index)
    total = hr_match.pending_count(session, tournament, rows)
    operation = _start(session, tournament, fencer, OperationKind.MATCH, total)

    def body(work_session: Session, work_operation: Operation) -> dict:
        work_tournament = work_session.get(Tournament, work_operation.tournament_id)
        return hr_match.run_matching(
            work_session,
            work_tournament,
            matcher,
            index,
            _replayed_import_rows(work_session, work_tournament, index),
            progress=lambda session, units: operations.advance(session, work_operation, units),
        )

    operations.run_in_background(operation.id, body)
    return {"operation_id": operation.id}


@router.post("/dedup", status_code=202)
async def run_dedup(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    llm: DedupDep,
):
    require_console_access(session, tournament, fencer)
    if llm is None:
        raise HTTPException(status_code=503, detail="llm_not_configured")
    rows = _replayed_import_rows(session, tournament)
    total = dedup.pending_count(session, tournament, rows)
    operation = _start(session, tournament, fencer, OperationKind.DEDUP, total)
    actor_id = fencer.id

    def body(work_session: Session, work_operation: Operation) -> dict:
        work_tournament = work_session.get(Tournament, work_operation.tournament_id)
        actor = work_session.get(Fencer, actor_id)
        return dedup.run_dedup(
            work_session,
            work_tournament,
            llm,
            _replayed_import_rows(work_session, work_tournament),
            actor,
            progress=lambda session, units: operations.advance(session, work_operation, units),
        )

    operations.run_in_background(operation.id, body)
    return {"operation_id": operation.id}


@router.get("/dedup/queue")
def dedup_queue(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    rows = _replayed_import_rows(session, tournament)
    return dedup.pending_queue(session, tournament, rows)


class DedupDecisionIn(BaseModel):
    key: str
    accept: bool
    fields: dict | None = None
    note: str | None = None


@router.post("/dedup/decide")
def dedup_decide(
    data: DedupDecisionIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    rows = _replayed_import_rows(session, tournament)
    outcome = dedup.decide(
        session, tournament, fencer, rows, data.key, data.accept, data.fields, data.note
    )
    if outcome["status"] == "not_pending":
        raise HTTPException(status_code=404, detail="not_pending")
    return outcome


@router.get("/status")
def import_status(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    batch = importer.latest_batch(session, tournament)
    # what a clear would remove, which is everything ever imported and not the
    # latest batch alone — the console states these counts before it clears
    # (spec table-import, Confirmation states the cost)
    total = importclear.imported_totals(session, tournament)
    if batch is None:
        return {"batch": None, "total": total}
    return {
        "batch": {
            "id": batch.id,
            "filename": batch.filename,
            "uploaded_at": batch.uploaded_at,
            "rows": batch.row_count,
        },
        "total": total,
    }


operations_router = APIRouter(
    prefix="/api/tournaments/{slug}/operations", tags=["operations"]
)


def _utc(moment: datetime | None) -> datetime | None:
    """Stamp UTC on an instant SQLite handed back naive.

    Every stored instant is UTC, but SQLite drops tzinfo on round-trip even for
    a `DateTime(timezone=True)` column (the same quirk `matching` works around).
    Serialized without a zone, the console would read the instant as its own
    local time and show an operation as having started hours ago."""
    if moment is None:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _operation_view(operation: Operation) -> dict:
    return {
        "id": operation.id,
        "kind": operation.kind.value,
        "status": operation.status.value,
        "total": operation.total,
        "done": operation.done,
        "started_at": _utc(operation.started_at),
        "finished_at": _utc(operation.finished_at),
        "outcome": operation.outcome,
    }


@operations_router.get("")
def list_operations(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """What the console polls: the tournament's running operation, and the most
    recent concluded one of each kind. One request serves both the phase panels
    and the standing indicator (design D7)."""
    require_console_access(session, tournament, fencer)
    in_flight = operations.running(session, tournament)
    return {
        "running": _operation_view(in_flight) if in_flight else None,
        "concluded": [
            _operation_view(operation)
            for operation in operations.latest_concluded(session, tournament)
        ],
    }
