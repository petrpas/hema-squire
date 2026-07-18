from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select

from app import bank
from app.auth import require_organizer
from app.models import BankTransaction
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import TransactionOut

router = APIRouter(prefix="/api/tournaments/{slug}/payments", tags=["payments"])

FioClientDep = Annotated[bank.FioClient, Depends(bank.get_fio_client)]


@router.post("/import-statement", response_model=bank.IngestResult)
async def import_statement(
    file: UploadFile, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_organizer(session, tournament, fencer)
    content = await file.read()
    try:
        transactions = bank.parse_fio_csv(content)
    except (ValueError, ArithmeticError) as error:
        raise HTTPException(status_code=422, detail=f"statement_parse_error: {error}") from None
    return bank.ingest(session, tournament, "csv", transactions)


@router.post("/fio-poll", response_model=bank.IngestResult)
def fio_poll(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    fio: FioClientDep,
    days_back: int = 14,
):
    require_organizer(session, tournament, fencer)
    if not tournament.fio_token:
        raise HTTPException(status_code=409, detail="fio_token_not_configured")
    today = date.today()
    transactions = fio.fetch(tournament.fio_token, today - timedelta(days=days_back), today)
    return bank.ingest(session, tournament, "fio_api", transactions)


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_organizer(session, tournament, fencer)
    return session.scalars(
        select(BankTransaction)
        .where(BankTransaction.tournament_id == tournament.id)
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
