from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app import dedup, hr_match, importclear, importer, rules, sheet
from app.auth import require_console_access
from app.hr_index import HRIndex, get_hr_index
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep

router = APIRouter(prefix="/api/tournaments/{slug}/import", tags=["import"])

ParserDep = Annotated[importer.ImportParser | None, Depends(importer.get_import_parser)]
MatcherDep = Annotated[hr_match.HRMatcher | None, Depends(hr_match.get_hr_matcher)]
DedupDep = Annotated[dedup.DedupLLM | None, Depends(dedup.get_dedup_llm)]
HRIndexDep = Annotated[HRIndex, Depends(get_hr_index)]


def _replayed_import_rows(session, tournament) -> list[dict]:
    """The rows matching and deduplication work on: the ones that entered
    unmatched. An in-app registration is HR-bound at birth and stays out of it;
    an imported row and a hand-entered one both traverse the two operations
    (spec etl-console, Per-row phase status)."""
    base = sheet.base_rows(session, tournament)
    rows, _ = rules.replay(base, rules.active_rules(session, tournament))
    return [
        row for row in rows.values() if row["id"].startswith(("imp:", "man:"))
    ]


@router.post("")
async def import_table(
    file: UploadFile,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    parser: ParserDep,
):
    require_console_access(session, tournament, fencer)
    data = await file.read()
    try:
        # the parser's LLM call is sync; off the loop thread so it can drive its own
        return await run_in_threadpool(
            importer.import_table,
            session,
            tournament,
            parser,
            file.filename or "upload.csv",
            data,
            fencer.id,
        )
    except importer.UnsupportedFormatError:
        raise HTTPException(status_code=422, detail="unsupported_format") from None


@router.delete("")
def clear_import(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Remove everything the tournament ever imported. Hard, total and final —
    the console confirms it before calling (spec table-import, Clearing is
    warned about and irreversible)."""
    require_console_access(session, tournament, fencer)
    return importclear.clear_imports(session, tournament)


@router.post("/match")
def run_matching(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    matcher: MatcherDep,
    index: HRIndexDep,
):
    require_console_access(session, tournament, fencer)
    if matcher is None:
        raise HTTPException(status_code=503, detail="llm_not_configured")
    rows = _replayed_import_rows(session, tournament)
    return hr_match.run_matching(session, tournament, matcher, index, rows)


@router.post("/dedup")
def run_dedup(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    llm: DedupDep,
):
    require_console_access(session, tournament, fencer)
    if llm is None:
        raise HTTPException(status_code=503, detail="llm_not_configured")
    rows = _replayed_import_rows(session, tournament)
    return dedup.run_dedup(session, tournament, llm, rows, fencer)


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
