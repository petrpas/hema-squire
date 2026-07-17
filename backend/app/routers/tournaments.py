from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import taxonomy
from app.auth import current_fencer, require_organizer
from app.db import get_session
from app.models import Discipline, Fencer, Tournament, TournamentOrganizer
from app.schemas import (
    DisciplineIn,
    DisciplineOut,
    OrganizerAdd,
    TournamentCreate,
    TournamentOut,
    TournamentUpdate,
)

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])

SessionDep = Annotated[Session, Depends(get_session)]
FencerDep = Annotated[Fencer, Depends(current_fencer)]


def get_tournament(session: SessionDep, slug: str) -> Tournament:
    tournament = session.scalar(
        select(Tournament)
        .where(Tournament.slug == slug)
        .options(selectinload(Tournament.disciplines))
    )
    if tournament is None:
        raise HTTPException(status_code=404, detail="tournament_not_found")
    return tournament


TournamentDep = Annotated[Tournament, Depends(get_tournament)]


@router.post("", response_model=TournamentOut, status_code=201)
def create_tournament(data: TournamentCreate, session: SessionDep, fencer: FencerDep):
    if session.scalar(select(Tournament.id).where(Tournament.slug == data.slug)):
        raise HTTPException(status_code=409, detail="slug_taken")
    tournament = Tournament(**data.model_dump())
    session.add(tournament)
    session.add(TournamentOrganizer(tournament=tournament, fencer=fencer))
    session.commit()
    session.refresh(tournament)
    return tournament


@router.get("", response_model=list[TournamentOut])
def list_tournaments(session: SessionDep):
    return session.scalars(
        select(Tournament)
        .options(selectinload(Tournament.disciplines))
        .order_by(Tournament.date)
    ).all()


@router.get("/{slug}", response_model=TournamentOut)
def tournament_detail(tournament: TournamentDep):
    return tournament


@router.patch("/{slug}", response_model=TournamentOut)
def update_tournament(
    data: TournamentUpdate, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_organizer(session, tournament, fencer)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tournament, field, value)
    session.commit()
    session.refresh(tournament)
    return tournament


@router.post("/{slug}/disciplines", response_model=DisciplineOut, status_code=201)
def add_discipline(
    data: DisciplineIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_organizer(session, tournament, fencer)
    if not taxonomy.is_valid_code(data.code):
        raise HTTPException(status_code=422, detail="unknown_discipline_code")
    if any(d.code == data.code for d in tournament.disciplines):
        raise HTTPException(status_code=409, detail="discipline_exists")
    discipline = Discipline(
        tournament=tournament,
        code=data.code,
        name=data.name or taxonomy.default_name(data.code),
        capacity=data.capacity,
        fee=data.fee,
        fee_early=data.fee_early,
    )
    session.add(discipline)
    session.commit()
    session.refresh(discipline)
    return discipline


@router.patch("/{slug}/disciplines/{code}", response_model=DisciplineOut)
def update_discipline(
    code: str,
    data: DisciplineIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_organizer(session, tournament, fencer)
    discipline = next((d for d in tournament.disciplines if d.code == code), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    if data.code != code:
        raise HTTPException(status_code=422, detail="code_is_immutable")
    discipline.name = data.name or discipline.name
    discipline.capacity = data.capacity
    discipline.fee = data.fee
    discipline.fee_early = data.fee_early
    session.commit()
    session.refresh(discipline)
    return discipline


@router.delete("/{slug}/disciplines/{code}", status_code=204)
def delete_discipline(
    code: str, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_organizer(session, tournament, fencer)
    discipline = next((d for d in tournament.disciplines if d.code == code), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    session.delete(discipline)
    session.commit()


@router.post("/{slug}/organizers", status_code=201)
def add_organizer(
    data: OrganizerAdd, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_organizer(session, tournament, fencer)
    new_organizer = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if new_organizer is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    already = session.scalar(
        select(TournamentOrganizer.id).where(
            TournamentOrganizer.tournament_id == tournament.id,
            TournamentOrganizer.fencer_id == new_organizer.id,
        )
    )
    if already:
        raise HTTPException(status_code=409, detail="already_organizer")
    session.add(TournamentOrganizer(tournament=tournament, fencer=new_organizer))
    session.commit()
    return {"status": "added"}
