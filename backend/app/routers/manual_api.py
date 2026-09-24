"""Fencers the organizer enters by hand at the console.

One endpoint, and the validation that stands between the dialog and the table.
The entry is accepted whole or refused whole: nothing is repaired, guessed at,
or silently dropped (spec etl-console, Strict validation of a manual entry).
"""

import datetime

from fastapi import APIRouter, HTTPException

from app import handentry, manualrows, setup
from app.auth import require_console_access, require_published
from app.models import DisciplineKind, ExtraCategory, RegistrationsKeptBy, Tournament
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import ManualEntryIn, ManualEntryOut

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["manual"])


def _resolve_manual_entry(tournament: Tournament, data: ManualEntryIn) -> None:
    """The entry's fit with the tournament's own structure — the sibling of
    `registrations._resolve_selection`, refusing the same way.

    A team discipline is entered through the tournament's team handling, never
    by naming it on a fencer's row, so it is refused here as it is there.
    """
    by_slug = {d.slug: d for d in tournament.disciplines}
    unknown = [slug for slug in data.disciplines if slug not in by_slug]
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_disciplines": unknown})
    wrong_kind = [
        slug for slug in data.disciplines if by_slug[slug].kind != DisciplineKind.INDIVIDUAL
    ]
    if wrong_kind:
        raise HTTPException(status_code=422, detail={"team_discipline_not_individual": wrong_kind})
    if not data.disciplines:
        # a row that enters nobody into anything states nothing; the organizer
        # typed it to record a competitor
        raise HTTPException(status_code=422, detail="no_disciplines")

    lent = {item.name for item in tournament.extra_items if item.category == ExtraCategory.RENTAL}
    unknown_rentals = [name for name in data.weapon_rentals if name not in lent]
    if unknown_rentals:
        raise HTTPException(status_code=422, detail={"unknown_rentals": unknown_rentals})


def enters_registration(tournament: Tournament) -> bool:
    """Whether a hand entry here becomes a registration at once rather than a
    source row: on an automatic tournament, where Squire keeps the list and a
    fencer at the door is placed like any other (design manual-entry-registers
    D1)."""
    return tournament.registrations_kept_by is RegistrationsKeptBy.SQUIRE


@router.post("/manual-rows", response_model=ManualEntryOut, status_code=201)
def create_manual_row(
    data: ManualEntryIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """A fencer entered by hand. What the entry becomes follows the mode: on an
    automatic tournament a registration at once, placed against capacity and
    sent nothing (`handentry`); on a manual one a source row, issued at the
    next payment intake (design manual-entry-registers D1)."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    _resolve_manual_entry(tournament, data)
    # the moment the organizer states, or now read in the tournament's own zone
    # — the frame every moment in the table is read in (design D5)
    zone = setup.zone_for(tournament)
    registered_at = data.registered_at or datetime.datetime.now(zone)
    disciplines = list(dict.fromkeys(data.disciplines))
    rentals = list(dict.fromkeys(data.weapon_rentals))
    if enters_registration(tournament):
        by_slug = {d.slug: d for d in tournament.disciplines}
        registration = handentry.register(
            session,
            tournament,
            name=data.name,
            nationality=data.nationality,
            club=data.club,
            hr_id=data.hr_id,
            email=data.email,
            # a registration holds an instant; a stated moment with no zone is
            # the tournament's own wall clock, as the dialog presents it
            registered_at=(
                registered_at
                if registered_at.tzinfo is not None
                else registered_at.replace(tzinfo=zone)
            ).astimezone(datetime.UTC),
            disciplines=[by_slug[slug] for slug in disciplines],
            weapon_rentals=rentals,
            afterparty=data.afterparty,
            notes=data.notes,
        )
        return ManualEntryOut(registration_id=registration.id)
    row = manualrows.create(
        session,
        tournament,
        fencer.id,
        name=data.name,
        nationality=data.nationality,
        club=data.club,
        hr_id=data.hr_id,
        email=data.email,
        registered_at=registered_at,
        # deduplicated, keeping the organizer's order: one enters a discipline
        # once and borrows one of an item, as a parsed row does
        disciplines=disciplines,
        weapon_rentals=rentals,
        afterparty=data.afterparty,
        notes=data.notes,
    )
    return ManualEntryOut(row_id=row.id)
