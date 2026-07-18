from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app import importer
from app.auth import require_organizer
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep

router = APIRouter(prefix="/api/tournaments/{slug}/import", tags=["import"])

ParserDep = Annotated[importer.ImportParser | None, Depends(importer.get_import_parser)]


@router.post("")
async def import_table(
    file: UploadFile,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    parser: ParserDep,
):
    require_organizer(session, tournament, fencer)
    data = await file.read()
    try:
        return importer.import_table(
            session, tournament, parser, file.filename or "upload.csv", data, fencer.id
        )
    except importer.UnsupportedFormatError:
        raise HTTPException(status_code=422, detail="unsupported_format") from None


@router.get("/status")
def import_status(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_organizer(session, tournament, fencer)
    batch = importer.latest_batch(session, tournament)
    if batch is None:
        return {"batch": None}
    return {
        "batch": {
            "id": batch.id,
            "filename": batch.filename,
            "uploaded_at": batch.uploaded_at,
            "rows": batch.row_count,
        }
    }
