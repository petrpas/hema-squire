from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select

from app import bank, matching
from app.auth import require_organizer
from app.mail import Mailer, get_mailer
from app.models import BankTransaction
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import IngestAndMatchOut, TransactionOut

router = APIRouter(prefix="/api/tournaments/{slug}/payments", tags=["payments"])

FioClientDep = Annotated[bank.FioClient, Depends(bank.get_fio_client)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]


def _ingest_and_match(session, tournament, mailer, source, transactions) -> IngestAndMatchOut:
    ingested = bank.ingest(session, tournament, source, transactions)
    matched = matching.match_new_transactions(session, tournament, mailer)
    return IngestAndMatchOut(
        new=ingested.new,
        duplicate=ingested.duplicate,
        matched=matched.matched,
        flagged=matched.flagged,
        unmatched=matched.unmatched,
    )


@router.post("/import-statement", response_model=IngestAndMatchOut)
async def import_statement(
    file: UploadFile,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    require_organizer(session, tournament, fencer)
    content = await file.read()
    try:
        transactions = bank.parse_fio_csv(content)
    except (ValueError, ArithmeticError) as error:
        raise HTTPException(status_code=422, detail=f"statement_parse_error: {error}") from None
    return _ingest_and_match(session, tournament, mailer, "csv", transactions)


@router.post("/fio-poll", response_model=IngestAndMatchOut)
def fio_poll(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    fio: FioClientDep,
    mailer: MailerDep,
    days_back: int = 14,
):
    require_organizer(session, tournament, fencer)
    if not tournament.fio_token:
        raise HTTPException(status_code=409, detail="fio_token_not_configured")
    today = date.today()
    transactions = fio.fetch(tournament.fio_token, today - timedelta(days=days_back), today)
    return _ingest_and_match(session, tournament, mailer, "fio_api", transactions)


@router.get("/unmatched", response_model=list[TransactionOut])
def unmatched_queue(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_organizer(session, tournament, fencer)
    return session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.tournament_id == tournament.id,
            BankTransaction.status.in_(["unmatched", "flagged"]),
        )
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_organizer(session, tournament, fencer)
    return session.scalars(
        select(BankTransaction)
        .where(BankTransaction.tournament_id == tournament.id)
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
