"""The floor's HTTP surface (specs floor-roster, floor-setup, floor-console).

Every endpoint stands behind the console gate. Reads stay open on a draft;
writes are refused there, as every write of a tournament's data is
(`require_published`). A discipline-less event has no floor and answers 404.
"""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.auth import require_console_access, require_published
from app.floor import setup
from app.floor.adapters.office import (
    FencerDep,
    SessionDep,
    TournamentDep,
    has_floor,
    roster,
    setup_facts,
)
from app.floor.schemas import (
    DayIO,
    FloorPersonRefOut,
    FloorRosterOut,
    FloorSetupDisciplineOut,
    FloorSetupOut,
    FloorSummaryOut,
    FormatIn,
    OfficialIn,
    ParamsIO,
    PisteIn,
)

router = APIRouter(prefix="/api/tournaments", tags=["floor"])

TABS = ("setup", "data", "plan", "today", "checkin", "pools", "bracket", "results")


def _floor(tournament: TournamentDep) -> None:
    """After the console gate, which every handler calls itself so the tenant
    sweep (`tests/test_tenant_isolation.py`) finds it."""
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")


@router.get("/{slug}/floor/roster", response_model=FloorRosterOut)
def floor_roster(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> FloorRosterOut:
    """The tournament's seated entrants as the floor reads them: behind the
    gate `GET /export/tables` stands behind."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    return FloorRosterOut.model_validate(asdict(roster(session, tournament)))


@router.get("/{slug}/floor/setup", response_model=FloorSetupOut)
def floor_setup(tournament: TournamentDep, session: SessionDep, fencer: FencerDep) -> FloorSetupOut:
    """Every Setup section with its defaults, and who an official may be
    linked to."""
    require_console_access(session, tournament, fencer)
    _floor(tournament)
    facts = setup_facts(tournament)
    persons = roster(session, tournament).persons
    keys = {person.key for person in persons}
    return FloorSetupOut(
        disciplines=[
            FloorSetupDisciplineOut(id=d.id, slug=d.slug, name=d.name, kind=d.kind)
            for d in facts.disciplines
        ],
        persons=[
            FloorPersonRefOut(key=p.key, name=p.name)
            for p in sorted(persons, key=lambda p: p.name.casefold())
        ],
        days=setup.read_days(session, facts),
        pistes=setup.read_pistes(session, facts.id),
        formats=setup.read_formats(session, facts),
        officials=setup.read_officials(session, facts.id, keys),
        params=setup.read_params(session, facts.id),
    )


def _writable(tournament: TournamentDep) -> setup.Tournament:
    _floor(tournament)
    require_published(tournament)
    return setup_facts(tournament)


@router.put("/{slug}/floor/setup/days", status_code=204)
def save_days(
    days: list[DayIO], tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    setup.save_days(session, _writable(tournament), days)
    session.commit()


@router.put("/{slug}/floor/setup/pistes", status_code=204)
def save_pistes(
    pistes: list[PisteIn], tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    setup.save_pistes(session, _writable(tournament), pistes)
    session.commit()


@router.put("/{slug}/floor/setup/formats", status_code=204)
def save_formats(
    formats: list[FormatIn], tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    setup.save_formats(session, _writable(tournament), formats)
    session.commit()


@router.put("/{slug}/floor/setup/officials", status_code=204)
def save_officials(
    officials: list[OfficialIn], tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    facts = _writable(tournament)
    keys = {person.key for person in roster(session, tournament).persons}
    setup.save_officials(session, facts, officials, keys)
    session.commit()


@router.put("/{slug}/floor/setup/params", status_code=204)
def save_params(
    params: ParamsIO, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    setup.save_params(session, _writable(tournament).id, params)
    session.commit()


@router.get("/{slug}/floor/summary", response_model=FloorSummaryOut)
def floor_summary(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> FloorSummaryOut:
    """The band's badges and the default tab's input (design D6). Each later
    floor change adds its tab's waiting conditions here."""
    require_console_access(session, tournament, fencer)
    _floor(tournament)
    missing = setup.setup_missing(session, setup_facts(tournament))
    badges: dict[str, bool] = dict.fromkeys(TABS, False)
    badges["setup"] = bool(missing)
    return FloorSummaryOut(plan_published=False, badges=badges, setup_missing=missing)
