"""Removal of everything a tournament ever imported.

The tournament asserts that no file was ever uploaded, so the removal is a
deletion of the data rather than a marking of it: no batch, no source row, no
decision taken about one, no correction to one, and no number one held survives
it (spec table-import, Clearing the tournament's imported content). This is the
one place the console deletes rather than records — the reversible row deletion
the table offers is a rule, and rules are what this removes.

Ordered by dependency, in one transaction: registrations issued for the cleared
rows, then journal entries, then the rules they belong to, then the numbers,
then the rows, then the batches. Decisions are pruned last, once the survivors
are known.

A registration issued for an imported row goes with it. It exists only because
the row did, and it stands in the row's place in the fencer list — left behind
it would keep drawing that fencer into the table under the id of a row that no
longer exists, and the clear could be seen through. Where such a registration
has been credited the clear is refused instead: money already recorded against a
fencer is not the console's to delete on the way past.
"""

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app import dedup, hr_match
from app.models import (
    BankTransaction,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    PaymentEvent,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    Rule,
    RuleJournalEntry,
    SheetRowNumber,
    Team,
    TeamMember,
    Tournament,
)


class CreditedRegistrationsError(RuntimeError):
    """The clear would delete registrations that money has been credited to.

    Raised rather than deleting them: the row can be asserted never to have
    existed, but the payment against it was a real event, and destroying it
    silently would leave a tournament whose books do not add up with nothing to
    say why. The organizer resolves those payments first."""

    def __init__(self, count: int):
        self.count = count
        super().__init__(f"{count} issued registrations hold credit")


def _names_a_cleared_row(value: object, cleared: set[str]) -> bool:
    """Whether a rule's payload mentions a cleared row anywhere inside it.

    A merge names its absorbed rows in `absorb`, a payment link its rows in a
    list; rather than enumerate the payload shapes of every rule kind, the whole
    structure is scanned for a row id. A rule that speaks about a row which no
    longer exists has nothing left to say."""
    if isinstance(value, str):
        return value in cleared
    if isinstance(value, dict):
        return any(_names_a_cleared_row(item, cleared) for item in value.values())
    if isinstance(value, list):
        return any(_names_a_cleared_row(item, cleared) for item in value)
    return False


def _surviving_groups(session: Session, tournament: Tournament) -> set[str]:
    """The dedup group keys still reconstructible after the clear.

    A merge is recorded twice over: as a `dedup_decision` rule naming its
    survivor and its absorbed rows, and as a decision keyed by the hash of that
    group. The hash cannot be reversed, so the surviving rules are what says
    which group keys still name a real group."""
    groups = set()
    for rule in session.scalars(
        select(Rule).where(Rule.tournament_id == tournament.id, Rule.kind == "dedup_decision")
    ):
        members = [rule.target, *rule.payload.get("absorb", [])]
        groups.add(dedup.group_key(members))
    return groups


def _prune_decisions(session: Session, tournament: Tournament) -> None:
    """Drop every decision that is not provably about rows which survive.

    A decision is a cache of an LLM answer, so dropping one costs a rerun and
    nothing else; keeping one that speaks about a cleared row would let the
    clear be seen through. What survives is what the spec promises survives:
    the decisions recorded about rows that did not come from a file.
    """
    from app import sheet  # local: sheet imports this module's siblings

    survivors = sheet.base_rows(session, tournament)
    identities = {
        hr_match.identity_key(row.get("name"), row.get("club")) for row in survivors.values()
    }
    groups = _surviving_groups(session, tournament)

    for decision in session.scalars(
        select(ImportDecision).where(ImportDecision.tournament_id == tournament.id)
    ):
        keep = False
        if decision.kind == "hr_match":
            # keyed by name and club, so a surviving row's proposal is still its own
            keep = decision.key in identities
        elif decision.kind == "dedup_seen":
            keep = decision.key in survivors
        elif decision.kind == "merge":
            keep = bool(decision.payload.get("rows")) and all(
                row_id in survivors for row_id in decision.payload["rows"]
            )
        elif decision.kind == "dedup_resolution":
            keep = decision.key in groups
        # `parse` belongs to an imported row by definition, and `dedup` is a
        # banding of the whole no-id population, which the clear has changed:
        # both go, the banding to be recomputed on the next run
        if not keep:
            session.delete(decision)


def imported_totals(session: Session, tournament: Tournament) -> dict:
    """What a clear would remove: every row of every file ever uploaded."""
    rows = session.scalar(
        select(func.count()).select_from(ImportedRow).where(
            ImportedRow.tournament_id == tournament.id
        )
    )
    files = session.scalar(
        select(func.count()).select_from(ImportBatch).where(
            ImportBatch.tournament_id == tournament.id
        )
    )
    return {"rows": rows or 0, "files": files or 0}


def _issued_registrations(session: Session, tournament: Tournament) -> list[Registration]:
    """Registrations issued for a row of this tournament's fencer list."""
    return list(
        session.scalars(
            select(Registration).where(
                Registration.tournament_id == tournament.id,
                Registration.source_row_id.is_not(None),
            )
        )
    )


def clear_imports(session: Session, tournament: Tournament) -> dict:
    """Remove every trace of every import. Returns what was removed, in the
    terms the confirmation stated it: rows and files.

    Raises `CreditedRegistrationsError` where a registration issued for one of
    those rows has been credited.
    """
    issued = _issued_registrations(session, tournament)
    credited = [r for r in issued if r.amount_paid_cents or r.amount_paid_eur_cents]
    if credited:
        raise CreditedRegistrationsError(len(credited))
    imported = list(
        session.scalars(
            select(ImportedRow).where(ImportedRow.tournament_id == tournament.id)
        )
    )
    batch_ids = list(
        session.scalars(select(ImportBatch.id).where(ImportBatch.tournament_id == tournament.id))
    )
    cleared = {f"imp:{row.key}" for row in imported}
    if not imported and not batch_ids:
        return {"rows": 0, "files": 0}

    # soft-deleted rules included: an undone correction to a cleared row is
    # still a record that the row was there
    doomed = [
        rule.id
        for rule in session.scalars(
            select(Rule).where(Rule.tournament_id == tournament.id)
        )
        if rule.target in cleared or _names_a_cleared_row(rule.payload, cleared)
    ]
    if doomed:
        session.execute(
            delete(RuleJournalEntry).where(RuleJournalEntry.rule_id.in_(doomed))
        )
        session.execute(delete(Rule).where(Rule.id.in_(doomed)))

    if cleared:
        session.execute(
            delete(SheetRowNumber).where(
                SheetRowNumber.tournament_id == tournament.id,
                SheetRowNumber.row_id.in_(cleared),
            )
        )
    if issued:
        # Children first and explicitly: SQLite has no ON DELETE CASCADE here
        # and the relationships do not delete-orphan, so a plain delete would
        # try to null a NOT NULL foreign key. Same order and reason as
        # `routers.tournaments._cascade_delete`.
        ids = [r.id for r in issued]
        team_ids = select(Team.id).where(Team.registration_id.in_(ids))
        session.execute(delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
        session.execute(delete(Team).where(Team.registration_id.in_(ids)))
        session.execute(
            delete(RegistrationDiscipline).where(
                RegistrationDiscipline.registration_id.in_(ids)
            )
        )
        session.execute(
            delete(RegistrationExtra).where(RegistrationExtra.registration_id.in_(ids))
        )
        session.execute(delete(PaymentEvent).where(PaymentEvent.registration_id.in_(ids)))
        # a transaction that had been linked to one of these keeps its money and
        # loses its addressee: it returns to the unresolved queue rather than
        # vanishing with the registration (none of these is credited — a
        # credited one refused the clear above)
        session.execute(
            update(BankTransaction)
            .where(BankTransaction.matched_registration_id.in_(ids))
            .values(matched_registration_id=None, status="unmatched",
                    status_reason="registration_cleared")
        )
        session.execute(delete(Registration).where(Registration.id.in_(ids)))
    session.flush()
    session.execute(delete(ImportedRow).where(ImportedRow.tournament_id == tournament.id))
    if batch_ids:
        session.execute(delete(ImportBatch).where(ImportBatch.id.in_(batch_ids)))
    session.flush()

    _prune_decisions(session, tournament)
    session.commit()
    return {"rows": len(imported), "files": len(batch_ids)}
