from typing import Annotated

from fastapi import APIRouter, Body

from app import export_json
from app.auth import require_organizer
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep

router = APIRouter(prefix="/api/tournaments", tags=["export"])


@router.get("/{slug}/export/json")
def export_tournament(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_organizer(session, tournament, fencer)
    return export_json.export_tournament(session, tournament)


@router.post("/restore", status_code=201)
def restore_tournament(
    session: SessionDep, fencer: FencerDep, data: Annotated[dict, Body()]
):
    """Recreate a tournament from a canonical JSON export; the caller becomes
    its organizer."""
    tournament = export_json.restore_tournament(session, data, fencer)
    return {"slug": tournament.slug}
