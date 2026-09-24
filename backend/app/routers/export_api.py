from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from app import export_json, exportsummary, exporttables, rules, sheet, sheets_export
from app.auth import require_console_access, require_published
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import (
    ExportBandTabOut,
    ExportSheetConfigOut,
    ExportSummaryLineOut,
    ExportSummaryOut,
    ExportTableOut,
)

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


@router.get("/{slug}/export/tables", response_model=list[ExportBandTabOut])
def export_tabs(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> list[ExportBandTabOut]:
    """The band of tables this tournament exports: the fencer list, its
    individual disciplines, and the extra-item categories it offers something
    in. Derived from the tournament, so a category it sells nothing in is
    absent rather than empty.

    Each tab carries how many it lists, counted over the replayed rows by the
    same narrowing its table applies."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    base = sheet.base_rows(session, tournament)
    replayed, _ = rules.replay(
        base, rules.active_rules(session, tournament), sheet.rating_lookup(session, tournament)
    )
    rows = list(replayed.values())
    band: list[ExportBandTabOut] = []
    for tab in exporttables.tabs(tournament):
        count, queued = exporttables.tab_counts(rows, tab)
        band.append(ExportBandTabOut(**tab.__dict__, count=count, queued=queued))
    return band


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
    # the summary is a tab but not a fencer table; its lines are read at
    # `/export/summary`
    if tab is None or tab.kind == exporttables.SUMMARY:
        raise HTTPException(status_code=404, detail="unknown_export_table")
    base = sheet.base_rows(session, tournament)
    replayed, _ = rules.replay(
        base, rules.active_rules(session, tournament), sheet.rating_lookup(session, tournament)
    )
    return ExportTableOut(
        **tab.__dict__,
        rows=exporttables.table_rows(list(replayed.values()), tab),
    )


@router.get("/{slug}/export/summary", response_model=ExportSummaryOut)
def export_summary(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> ExportSummaryOut:
    """The Summary tab: how many of each discipline and item the tournament
    offers, paid and unpaid, counted over the replayed rows."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    base = sheet.base_rows(session, tournament)
    replayed, _ = rules.replay(
        base, rules.active_rules(session, tournament), sheet.rating_lookup(session, tournament)
    )
    lines = exportsummary.summary_lines(tournament, list(replayed.values()))
    return ExportSummaryOut(lines=[ExportSummaryLineOut(**line.__dict__) for line in lines])


@router.get("/{slug}/export/sheet-config", response_model=ExportSheetConfigOut)
def export_sheet_config(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> ExportSheetConfigOut:
    """What the Export rail must know before a first export can succeed:
    whether this server holds Google credentials, the address they act as, and
    where this tournament currently writes.

    Not gated on publication, unlike the export itself. Naming the destination
    is preparation, and an organizer does it while the tournament is still a
    draft; refusing the read until publication would put the procedure out of
    reach exactly when it is being followed.

    The address is operational, not secret — it opens nothing without the
    private key — but it is stated only to an account with console access, as
    every other read of this tournament's console is."""
    require_console_access(session, tournament, fencer)
    email = sheets_export.service_account_email()
    return ExportSheetConfigOut(
        configured=email is not None,
        service_account=email,
        output_sheet_url=tournament.output_sheet_url,
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
    rows, _ = rules.replay(
        base, rules.active_rules(session, tournament), sheet.rating_lookup(session, tournament)
    )
    locale = "en" if english else fencer.language
    return sheets_export.export_to_sheets(tournament, list(rows.values()), client, locale)


@router.post("/restore", status_code=201)
def restore_tournament(session: SessionDep, fencer: FencerDep, data: Annotated[dict, Body()]):
    """Recreate a tournament from a canonical JSON export; the caller becomes
    its organizer."""
    tournament = export_json.restore_tournament(session, data, fencer)
    return {"slug": tournament.slug}
