"""The floor's HTTP surface (spec floor-roster)."""

from dataclasses import asdict

from fastapi import APIRouter

from app.auth import require_console_access, require_published
from app.floor.adapters.office import FencerDep, SessionDep, TournamentDep, roster
from app.floor.schemas import FloorRosterOut

router = APIRouter(prefix="/api/tournaments", tags=["floor"])


@router.get("/{slug}/floor/roster", response_model=FloorRosterOut)
def floor_roster(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> FloorRosterOut:
    """The tournament's seated entrants as the floor reads them: behind the
    gate `GET /export/tables` stands behind."""
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    return FloorRosterOut.model_validate(asdict(roster(session, tournament)))
