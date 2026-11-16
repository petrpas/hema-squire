from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import hr_sync, rules, sheet
from app.auth import require_console_access, require_published
from app.models import HRIndexRefresh, Tournament, TournamentOrganizer
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


# The index is one for the deployment and every refresh downloads HEMA
# Ratings' whole fighters page, so the brake is global rather than per caller:
# however many organizers press the button, the source sees at most one
# successful refresh per window (spec hr-integration, Fighters index).
REFRESH_COOLDOWN = timedelta(minutes=15)


def _refuse_within_cooldown(session: Session) -> None:
    last_ok = session.scalar(
        select(HRIndexRefresh.fetched_at)
        .where(HRIndexRefresh.status == "ok")
        .order_by(HRIndexRefresh.id.desc())
        .limit(1)
    )
    if last_ok is None:
        return
    # SQLite hands the server default back naive; it was written in UTC
    at = last_ok if last_ok.tzinfo is not None else last_ok.replace(tzinfo=UTC)
    if datetime.now(UTC) - at < REFRESH_COOLDOWN:
        raise HTTPException(
            status_code=429,
            detail={"code": "hr_refresh_cooldown", "last_refresh": at.isoformat()},
        )


@router.post("/refresh")
def refresh(session: SessionDep, fencer: FencerDep, fetcher: FetcherDep):
    _require_any_organizer(session, fencer)
    _refuse_within_cooldown(session)
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
    require_published(tournament)
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
