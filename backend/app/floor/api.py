"""The floor's HTTP surface (specs floor-roster, floor-setup, floor-console).

Every endpoint stands behind the console gate. Reads stay open on a draft;
writes are refused there, as every write of a tournament's data is
(`require_published`). A discipline-less event has no floor and answers 404.
"""

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.auth import require_console_access, require_published
from app.errors import FieldValidationError
from app.floor import planning, setup
from app.floor.adapters.office import (
    FencerDep,
    SessionDep,
    TournamentDep,
    has_floor,
    roster,
    setup_facts,
)
from app.floor.engine.model import Result
from app.floor.models import FloorPin
from app.floor.schemas import (
    ChooseIn,
    DayIO,
    FloorPersonRefOut,
    FloorPlanStateOut,
    FloorRosterOut,
    FloorSetupDisciplineOut,
    FloorSetupOut,
    FloorSummaryOut,
    FormatIn,
    OfficialIn,
    ParamsIO,
    PinIn,
    PinOut,
    PisteIn,
    VariantsOut,
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
    published = planning.published(session, tournament.id) is not None
    # a working version waits to be published
    badges["plan"] = planning.working(session, tournament.id) is not None
    return FloorSummaryOut(plan_published=published, badges=badges, setup_missing=missing)


# ------------------------------------------------------------ the plan
# (spec floor-plan)


def _context(session: SessionDep, tournament: TournamentDep) -> planning.Context:
    try:
        return planning.build(session, setup_facts(tournament), roster(session, tournament))
    except planning.SetupIncomplete as missing:
        raise HTTPException(
            status_code=409, detail={"reason": "setup_incomplete", "missing": missing.missing}
        ) from None


def _pin_out(row: FloorPin) -> PinOut:
    return PinOut(id=row.id, kind=row.kind, target=row.target, value=row.value, gate=row.gate)  # pyright: ignore[reportArgumentType]  # kind is one of PinIn's four: only this API writes it


@router.get("/{slug}/floor/plan", response_model=FloorPlanStateOut)
def floor_plan(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> FloorPlanStateOut:
    """The working and published versions, their difference, the pins, what
    stands in the way of publishing, and sensitivity."""
    require_console_access(session, tournament, fencer)
    _floor(tournament)
    facts = setup_facts(tournament)
    pins = [_pin_out(row) for row in planning.pins(session, facts.id)]
    try:
        context = planning.build(session, facts, roster(session, tournament))
    except planning.SetupIncomplete as missing:
        return FloorPlanStateOut(
            working=None,
            published=None,
            history=[],
            diff=[],
            pins=pins,
            obstacles=[],
            sensitivity=None,
            setup_missing=missing.missing,
        )
    work = planning.working(session, facts.id)
    return FloorPlanStateOut.model_validate(
        {
            "working": planning.stored_json(session, context, work),
            "published": planning.stored_json(
                session, context, planning.published(session, facts.id)
            ),
            "history": [p.version for p in planning.history(session, facts.id)],
            "diff": [
                {"activity": c.activity, "kind": c.kind, "before": c.before, "after": c.after}
                for c in planning.diff(session, context, facts.id)
            ],
            "pins": pins,
            "obstacles": planning.obstacles(session, facts, work) if work is not None else [],
            "sensitivity": planning.sensitivity_json(
                context, planning.sensitivity_of(session, context, facts.id)
            ),
            "setup_missing": [],
        }
    )


def _variants_out(context: planning.Context, result: Result) -> VariantsOut:
    return VariantsOut.model_validate(
        {
            "variants": [planning.variant_json(context, v) for v in result.variants],
            "infeasible": planning.infeasible_json(context, result),
            "capped": list(result.capped),
            "empty": list(context.empty),
        }
    )


@router.post("/{slug}/floor/plan/variants", response_model=VariantsOut)
def floor_plan_variants(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> VariantsOut:
    """The planner's variants for the tournament as it stands; nothing stored."""
    require_console_access(session, tournament, fencer)
    _floor(tournament)
    context = _context(session, tournament)
    return _variants_out(context, planning.run(context))


@router.post("/{slug}/floor/plan/choose", status_code=204)
def floor_plan_choose(
    data: ChooseIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """The chosen variant becomes the working version. The planner is run
    again, which gives the same variants for the same state."""
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    context = _context(session, tournament)
    chosen = next((v for v in planning.run(context).variants if v.key == data.key), None)
    if chosen is None:
        raise HTTPException(status_code=409, detail="variant_gone")
    planning.store(session, tournament.id, context, chosen, fencer.id, datetime.now(UTC))
    session.commit()


@router.post("/{slug}/floor/plan/publish", status_code=204)
def floor_plan_publish(tournament: TournamentDep, session: SessionDep, fencer: FencerDep) -> None:
    """The working version becomes the published one, the previous published
    kept as history. Refused while an obstacle stands."""
    require_console_access(session, tournament, fencer)
    facts = _writable(tournament)
    work = planning.working(session, facts.id)
    if work is None:
        raise HTTPException(status_code=409, detail="no_working_plan")
    found = planning.obstacles(session, facts, work)
    if found:
        raise HTTPException(status_code=409, detail={"reason": "obstacles", "obstacles": found})
    planning.publish(session, facts.id)
    session.commit()


@router.post("/{slug}/floor/plan/replan", response_model=VariantsOut)
def floor_plan_replan(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> VariantsOut:
    """A new working version from the state of the day: what has started stays
    where it stands, reserve pistes come in. Never published by itself."""
    require_console_access(session, tournament, fencer)
    facts = _writable(tournament)
    now = datetime.now(UTC)
    try:
        context = planning.build(session, facts, roster(session, tournament), replan_at=now)
    except planning.SetupIncomplete as missing:
        raise HTTPException(
            status_code=409, detail={"reason": "setup_incomplete", "missing": missing.missing}
        ) from None
    result = planning.run(context)
    if result.variants:
        planning.store(session, facts.id, context, result.variants[0], fencer.id, now)
        session.commit()
    return _variants_out(context, result)


@router.post("/{slug}/floor/plan/pins", response_model=PinOut, status_code=201)
def floor_plan_pin(
    data: PinIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> PinOut:
    require_console_access(session, tournament, fencer)
    facts = _writable(tournament)
    errors = planning.pin_errors(session, facts, data.kind, data.target, data.value)
    if errors:
        raise FieldValidationError(errors)
    row = FloorPin(
        tournament_id=facts.id,
        kind=data.kind,
        target=data.target,
        value=data.value,
        gate=None,
        created_at=datetime.now(UTC),
        created_by=fencer.id,
    )
    session.add(row)
    session.commit()
    return _pin_out(row)


@router.delete("/{slug}/floor/plan/pins/{pin_id}", status_code=204)
def floor_plan_unpin(
    pin_id: int, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    """A gate's pin is not removed here: reopening its gate removes it."""
    require_console_access(session, tournament, fencer)
    facts = _writable(tournament)
    row = session.get(FloorPin, pin_id)
    if row is None or row.tournament_id != facts.id:
        raise HTTPException(status_code=404, detail="pin_not_found")
    if row.gate is not None:
        raise HTTPException(status_code=409, detail="pin_from_gate")
    session.delete(row)
    session.commit()
