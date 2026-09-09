from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from app import export_json, hr_sync, rules, sheet, sheets_export
from app.auth import require_console_access, require_published
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep

router = APIRouter(prefix="/api/tournaments", tags=["export"])

SheetsFactoryDep = Annotated[
    sheets_export.SheetsClientFactory | None,
    Depends(sheets_export.get_sheets_client_factory),
]


@router.get("/{slug}/export/json")
def export_tournament(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    return export_json.export_tournament(session, tournament)


@router.post("/{slug}/export/sheet")
def export_sheet(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    factory: SheetsFactoryDep,
):
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    if factory is None:
        raise HTTPException(status_code=503, detail="sheets_not_configured")
    client = factory(tournament)
    if client is None:
        raise HTTPException(status_code=422, detail="output_sheet_url_not_set")
    base = sheet.base_rows(session, tournament)
    rows, _ = rules.replay(base, rules.active_rules(session, tournament))
    _, ratings = hr_sync.latest_ratings(session, tournament)
    return sheets_export.export_to_sheets(tournament, list(rows.values()), client, ratings)


@router.post("/restore", status_code=201)
def restore_tournament(session: SessionDep, fencer: FencerDep, data: Annotated[dict, Body()]):
    """Recreate a tournament from a canonical JSON export; the caller becomes
    its organizer."""
    tournament = export_json.restore_tournament(session, data, fencer)
    return {"slug": tournament.slug}
