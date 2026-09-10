from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from app import export_json, exporttables, rules, sheet, sheets_export
from app.auth import require_console_access, require_published
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import ExportTableOut, ExportTabOut

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


@router.get("/{slug}/export/tables", response_model=list[ExportTabOut])
def export_tabs(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """The band of tables this tournament exports: the fencer list, its
    individual disciplines, and the extra-item categories it offers something
    in. Derived from the tournament, so a category it sells nothing in is
    absent rather than empty."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    return [ExportTabOut(**tab.__dict__) for tab in exporttables.tabs(tournament)]


@router.get("/{slug}/export/table", response_model=ExportTableOut)
def export_table(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    # the fencer table is the band's first tab, and what an address naming no
    # table means
    kind: str = exporttables.FENCERS,
    key: str = "",
):
    """One table of the band: the replayed fencer table narrowed to the tab and
    in the tab's order.

    Each row keeps `disciplines` and `substitute_for`, so a discipline tab
    draws its capacity line — seated above, queued below — without a second
    query."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    tab = exporttables.find_tab(tournament, kind, key)
    if tab is None:
        raise HTTPException(status_code=404, detail="unknown_export_table")
    base = sheet.base_rows(session, tournament)
    replayed, _ = rules.replay(base, rules.active_rules(session, tournament))
    return ExportTableOut(
        **tab.__dict__,
        rows=exporttables.table_rows(list(replayed.values()), tab),
    )


@router.post("/{slug}/export/sheet")
def export_sheet(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    factory: SheetsFactoryDep,
    english: bool = False,
):
    """Write the export tables to the organizer's spreadsheet.

    `english` is the tick the console offers an organizer whose own language is
    not English: it governs what leaves — the headers and the yes/no values —
    and nothing on screen."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    if factory is None:
        raise HTTPException(status_code=503, detail="sheets_not_configured")
    client = factory(tournament)
    if client is None:
        raise HTTPException(status_code=422, detail="output_sheet_url_not_set")
    base = sheet.base_rows(session, tournament)
    rows, _ = rules.replay(base, rules.active_rules(session, tournament))
    locale = "en" if english else fencer.language
    return sheets_export.export_to_sheets(tournament, list(rows.values()), client, locale)


@router.post("/restore", status_code=201)
def restore_tournament(session: SessionDep, fencer: FencerDep, data: Annotated[dict, Body()]):
    """Recreate a tournament from a canonical JSON export; the caller becomes
    its organizer."""
    tournament = export_json.restore_tournament(session, data, fencer)
    return {"slug": tournament.slug}
