"""Removal of the payments a tournament has taken in.

The tournament asserts that no money ever arrived, so the removal is a deletion
of the data rather than a marking of it: no transaction, no event recorded about
one, no link an organizer drew to one, and no stored reading of the statement row
it came from survives it (spec payments-clearing, Clearing the payments a
tournament imported). The counterpart of `importclear` on the money side, and
written to the same shape.

Two things distinguish it from its sibling.

**The stored readings go too.** A statement's rows are interpreted once and
cached per row fingerprint, so that re-importing a corrected file costs nothing
for the rows that did not change. A clear that removed only the transactions
would leave those standing, and an organizer clearing after a misreading would
re-import and be handed the same wrong answer with nothing on screen to explain
why. Removing them is most of the point of this module.

**Credited money refuses the clear.** A transaction credited to a registration is
a payment the tournament acted on — a balance moved, a state changed, mail may
have gone out — and deleting it would leave that claim standing with nothing
behind it. The refusal is total: not the uncredited transactions, not the stored
readings, nothing. A partial clear is the one outcome nobody can reason about.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    BankTransaction,
    ImportDecision,
    PaymentEvent,
    Rule,
    RuleJournalEntry,
    Tournament,
)
from app.statements import DECISION_KIND as STATEMENT_ROW


class CreditedTransactionsError(RuntimeError):
    """The clear would delete money the tournament has already acted on.

    Raised rather than deleting: the import can be asserted never to have
    happened, but a payment credited against a fencer was a real event, and
    destroying it silently would leave a tournament whose books do not add up
    and nothing to say why (spec payments-clearing)."""

    def __init__(self, count: int):
        self.count = count
        super().__init__(f"{count} transactions hold credit")


def _credited(session: Session, tournament: Tournament) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(BankTransaction)
            .where(
                BankTransaction.tournament_id == tournament.id,
                BankTransaction.matched_registration_id.is_not(None),
            )
        )
        or 0
    )


def payment_totals(session: Session, tournament: Tournament) -> dict:
    """What a clear would remove, and what stands in its way — so the console can
    state a refusal before the organizer commits rather than after."""
    payments = (
        session.scalar(
            select(func.count())
            .select_from(BankTransaction)
            .where(BankTransaction.tournament_id == tournament.id)
        )
        or 0
    )
    return {"payments": payments, "credited": _credited(session, tournament)}


def clear_payments(session: Session, tournament: Tournament) -> dict:
    """Remove every trace of every payment taken in. Returns what was removed, in
    the terms the confirmation stated it: payments.

    Raises `CreditedTransactionsError` where any transaction has been credited,
    having removed nothing.
    """
    credited = _credited(session, tournament)
    if credited:
        raise CreditedTransactionsError(credited)

    transaction_ids = list(
        session.scalars(
            select(BankTransaction.id).where(
                BankTransaction.tournament_id == tournament.id
            )
        )
    )
    external_ids = {
        f"txn:{external}"
        for external in session.scalars(
            select(BankTransaction.external_id).where(
                BankTransaction.tournament_id == tournament.id
            )
        )
    }

    # A payment link speaks about a transaction by its external id. Soft-deleted
    # rules included, as `importclear` does: an undone link is still a record
    # that the money was there.
    doomed = [
        rule.id
        for rule in session.scalars(
            select(Rule).where(
                Rule.tournament_id == tournament.id, Rule.kind == "payment_link"
            )
        )
        if rule.target in external_ids
    ]
    if doomed:
        session.execute(
            delete(RuleJournalEntry).where(RuleJournalEntry.rule_id.in_(doomed))
        )
        session.execute(delete(Rule).where(Rule.id.in_(doomed)))

    # events first: they name the transactions by foreign key
    if transaction_ids:
        session.execute(
            delete(PaymentEvent).where(PaymentEvent.transaction_id.in_(transaction_ids))
        )
    session.execute(
        delete(BankTransaction).where(BankTransaction.tournament_id == tournament.id)
    )

    # the readings behind them. Without this the clear defeats the next import
    # invisibly — the mechanism, not the subject, so it is not counted in the
    # report (spec, A cleared statement is read afresh on re-import)
    session.execute(
        delete(ImportDecision).where(
            ImportDecision.tournament_id == tournament.id,
            ImportDecision.kind == STATEMENT_ROW,
        )
    )
    session.commit()
    return {"payments": len(transaction_ids)}
