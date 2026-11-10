"""Hard deletion of a tournament and everything recorded under it.

Two callers, one cascade. The Tournament Owner deletes only an empty tournament;
a global Admin deletes one in any state, registrations and payment history
included, once confirmed (spec tournament-admin, Tournament deletion and
cancellation). Who may call it, and whether registrations stop it, is the
caller's to decide; this module only removes.

SQLite has no ON DELETE CASCADE here and the relationships do not
delete-orphan, so every child table is named and deleted explicitly, children
before parents, in the caller's transaction. A table added later that refers to
a tournament or to one of its registrations has to be added here too; the
metadata-driven test in `tests/test_tournament_delete.py` fails until it is.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    BankTransaction,
    Discipline,
    DiscountCode,
    ExtraItem,
    HRRatingSnapshot,
    HRSnapshotRating,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    ManualPayment,
    ManualRow,
    Operation,
    PaymentCredit,
    PaymentEvent,
    PaymentWaiver,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RosterChange,
    Rule,
    RuleJournalEntry,
    SheetRowNumber,
    Team,
    TeamMember,
    Tournament,
    TournamentOrganizer,
)


def _delete_registrations(session: Session, tid: int) -> None:
    """Everything hanging off the tournament's registrations, then the
    registrations. Payment events and bank transactions point at a
    registration, so they go before it."""
    registration_ids = select(Registration.id).where(Registration.tournament_id == tid)
    team_ids = select(Team.id).where(Team.tournament_id == tid)
    # the roster log names a member, so it goes before the members
    session.execute(delete(RosterChange).where(RosterChange.team_id.in_(team_ids)))
    session.execute(delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
    session.execute(delete(Team).where(Team.tournament_id == tid))
    session.execute(
        delete(RegistrationDiscipline).where(
            RegistrationDiscipline.registration_id.in_(registration_ids)
        )
    )
    session.execute(
        delete(RegistrationExtra).where(RegistrationExtra.registration_id.in_(registration_ids))
    )
    session.execute(delete(PaymentCredit).where(PaymentCredit.tournament_id == tid))
    session.execute(delete(PaymentWaiver).where(PaymentWaiver.tournament_id == tid))
    session.execute(delete(ManualPayment).where(ManualPayment.tournament_id == tid))
    session.execute(delete(PaymentEvent).where(PaymentEvent.tournament_id == tid))
    session.execute(delete(BankTransaction).where(BankTransaction.tournament_id == tid))
    session.execute(delete(Registration).where(Registration.tournament_id == tid))
    # after the registrations, whose rows name them
    session.execute(delete(DiscountCode).where(DiscountCode.tournament_id == tid))


def delete_tournament(session: Session, tournament: Tournament) -> None:
    """Remove the tournament and every row recorded under it. Accounts are
    untouched: a fencer registered for it, or an organizer of it, keeps theirs.
    Does not commit."""
    tid = tournament.id
    _delete_registrations(session, tid)
    snapshot_ids = select(HRRatingSnapshot.id).where(HRRatingSnapshot.tournament_id == tid)
    session.execute(delete(HRSnapshotRating).where(HRSnapshotRating.snapshot_id.in_(snapshot_ids)))
    session.execute(delete(HRRatingSnapshot).where(HRRatingSnapshot.tournament_id == tid))
    batch_ids = select(ImportBatch.id).where(ImportBatch.tournament_id == tid)
    session.execute(delete(ImportedRow).where(ImportedRow.batch_id.in_(batch_ids)))
    session.execute(delete(ImportDecision).where(ImportDecision.tournament_id == tid))
    session.execute(delete(ImportBatch).where(ImportBatch.tournament_id == tid))
    session.execute(delete(RuleJournalEntry).where(RuleJournalEntry.tournament_id == tid))
    session.execute(delete(Rule).where(Rule.tournament_id == tid))
    session.execute(delete(ManualRow).where(ManualRow.tournament_id == tid))
    # the numbers those rows held; a tournament being deleted keeps none of them
    session.execute(delete(SheetRowNumber).where(SheetRowNumber.tournament_id == tid))
    session.execute(delete(Operation).where(Operation.tournament_id == tid))
    session.execute(delete(TournamentOrganizer).where(TournamentOrganizer.tournament_id == tid))
    session.execute(delete(ExtraItem).where(ExtraItem.tournament_id == tid))
    session.execute(delete(Discipline).where(Discipline.tournament_id == tid))
    session.delete(tournament)
