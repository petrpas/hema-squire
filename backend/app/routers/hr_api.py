from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import hr_sync, rules, sheet
from app.auth import require_console_access
from app.models import Tournament, TournamentOrganizer
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep

router = APIRouter(prefix="/api/hr", tags=["hr"])

FetcherDep = Annotated[hr_sync.HRFetcher, Depends(hr_sync.get_hr_fetcher)]


def _require_any_organizer(session, fencer) -> None:
    """The index is global; refreshing it is for anyone with console access to
    any tournament — its owner or a team member."""
    owns_any = session.scalar(select(Tournament.id).where(Tournament.owner_id == fencer.id))
    on_a_team = session.scalar(
        select(TournamentOrganizer.id).where(TournamentOrganizer.fencer_id == fencer.id)
    )
    if owns_any is None and on_a_team is None:
        raise HTTPException(status_code=403, detail="not_an_organizer")


@router.get("/status")
def status(session: SessionDep, fencer: FencerDep):
    return hr_sync.index_status(session)


@router.post("/refresh")
def refresh(session: SessionDep, fencer: FencerDep, fetcher: FetcherDep):
    _require_any_organizer(session, fencer)
    outcome = hr_sync.refresh_fighters(session, fetcher)
    if outcome["status"] != "ok":
        # previous index kept; diagnostics for the operator (drift policy)
        raise HTTPException(status_code=502, detail=outcome)
    return outcome


ratings_router = APIRouter(prefix="/api/tournaments/{slug}/ratings", tags=["hr"])


@ratings_router.post("/snapshot")
def take_snapshot(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    fetcher: FetcherDep,
):
    require_console_access(session, tournament, fencer)
    base = sheet.base_rows(session, tournament)
    rows, _ = rules.replay(base, rules.active_rules(session, tournament))
    hr_ids = sorted(
        {
            row["hr_id"]
            for row in rows.values()
            if row.get("hr_id") is not None and not row.get("_deleted")
        }
    )
    outcome = hr_sync.take_snapshot(session, tournament, fetcher, hr_ids)
    if outcome["status"] != "ok":
        raise HTTPException(status_code=502, detail=outcome)
    return outcome


@ratings_router.get("")
def latest(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    taken_at, ratings = hr_sync.latest_ratings(session, tournament)
    return {"taken_at": taken_at, "ratings": len(ratings)}
