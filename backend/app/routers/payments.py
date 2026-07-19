from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select

from app import bank, matching, rules, scheduler
from app.auth import require_console_access
from app.mail import Mailer, get_mailer
from app.models import BankTransaction, Registration
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import IngestAndMatchOut, LinkIn, TransactionOut

router = APIRouter(prefix="/api/tournaments/{slug}/payments", tags=["payments"])

FioClientDep = Annotated[bank.FioClient, Depends(bank.get_fio_client)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]


def _ingest_and_match(session, tournament, mailer, source, transactions) -> IngestAndMatchOut:
    ingested = bank.ingest(session, tournament, source, transactions)
    matched = matching.match_new_transactions(session, tournament, mailer)
    matching.apply_payment_links(session, tournament, mailer)
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
    require_console_access(session, tournament, fencer)
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
    require_console_access(session, tournament, fencer)
    if not tournament.fio_token:
        raise HTTPException(status_code=409, detail="fio_token_not_configured")
    today = date.today()
    transactions = fio.fetch(tournament.fio_token, today - timedelta(days=days_back), today)
    return _ingest_and_match(session, tournament, mailer, "fio_api", transactions)


@router.post("/process")
def process_lifecycle(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep, mailer: MailerDep
) -> dict[str, int]:
    """Run reminders and expiries for this tournament now (also runs periodically)."""
    require_console_access(session, tournament, fencer)
    expired = scheduler.process_expiries(session, tournament, mailer)
    return {
        "reminders": scheduler.process_reminders(session, tournament, mailer),
        "expired": expired,
    }


@router.post("/link", status_code=201)
def link_transaction(
    data: LinkIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    """Manually link an unmatched transaction to one or more registrations.
    Persists as a payment_link rule: survives reruns, removable via the rules API."""
    require_console_access(session, tournament, fencer)
    transaction = session.get(BankTransaction, data.transaction_id)
    if transaction is None or transaction.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if transaction.status == "matched":
        raise HTTPException(status_code=409, detail="already_matched")
    known_vs = set(
        session.scalars(
            select(Registration.vs).where(
                Registration.tournament_id == tournament.id, Registration.vs.in_(data.vs)
            )
        )
    )
    unknown = [vs for vs in data.vs if vs not in known_vs]
    if unknown:
        raise HTTPException(status_code=404, detail={"unknown_vs": unknown})

    rule = rules.create_rule(
        session,
        tournament,
        fencer,
        phase="payments",
        kind="payment_link",
        target=f"txn:{transaction.external_id}",
        payload={"vs": data.vs},
    )
    applied = matching.apply_payment_links(session, tournament, mailer)
    return {"rule_id": rule.id, "applied": applied}


@router.get("/unmatched", response_model=list[TransactionOut])
def unmatched_queue(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
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
    require_console_access(session, tournament, fencer)
    return session.scalars(
        select(BankTransaction)
        .where(BankTransaction.tournament_id == tournament.id)
        .order_by(BankTransaction.date, BankTransaction.id)
    ).all()
