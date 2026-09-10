"""The credit journal and the waiver journal: the only ways money is credited
to a registration, and the only way one is waived.

Every route money takes ends here — an automatic match on the variable symbol,
a payment link, a payment an organizer recorded, a reinstatement, a refund
hold. Six call sites used to move two counters with `+=` and `-=` and record
nothing about what they were the sum of; this module replaces all six, and what
a registration has been credited is read back off the rows it wrote
(`Registration.credited_in`).

**Appending is idempotent on the credit's source.** A source row credits a
registration at most once while that credit is live, guarded by a partial
unique index and by the check below rather than by the workflow state of the
source. `BankTransaction.status` says where a transaction sits in the
organizer's queues; it is not, and must not be, what decides whether the money
has already been counted (design `derive-balances-from-credits` D2).

**Reversal returns exactly what was credited.** Never an amount recomputed
against today's balance, which is the mistake both the payment-link rules and
`ManualPayment` were built to avoid, and which this module now makes
structurally impossible: a reversal names a row, and the row holds its own
amount.
"""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import setup
from app.models import (
    CreditOrigin,
    CreditSource,
    Currency,
    Fencer,
    PaymentCredit,
    PaymentWaiver,
    Registration,
    Tournament,
)


def actor_label(fencer: Fencer) -> str:
    """How a person is named in the journals: the label the audit trail uses,
    not a foreign key, so the record still reads correctly once the account
    that made it is gone. The same shape `ManualPayment.recorded_by` holds."""
    return f"{fencer.display_name} <{fencer.email}>"


def live_credit_for(
    session: Session,
    registration: Registration,
    source_kind: CreditSource,
    source_id: int,
) -> PaymentCredit | None:
    """The live credit this source already made against this registration, if
    it made one. The question every crediting path asks before it writes, and
    the question that replaces "has this transaction been matched yet"."""
    return session.scalar(
        select(PaymentCredit).where(
            PaymentCredit.registration_id == registration.id,
            PaymentCredit.source_kind == source_kind,
            PaymentCredit.source_id == source_id,
            PaymentCredit.reversed_at.is_(None),
        )
    )


def credit(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    *,
    amount_cents: int,
    currency: Currency,
    value_date: date,
    source_kind: CreditSource,
    source_id: int,
    origin: CreditOrigin,
    rule_id: int | None = None,
) -> PaymentCredit:
    """Append one credit, or return the live one that already covers this
    source without writing a second.

    Returning the existing row rather than raising is deliberate: every caller
    is a pass that may legitimately run again — a re-ingested statement, a
    second application of the payment links, a scheduler tick — and each of
    them wants "this money is credited" to be true afterwards, not to have to
    tell a repeat from a first run.
    """
    existing = live_credit_for(session, registration, source_kind, source_id)
    if existing is not None:
        return existing
    entry = PaymentCredit(
        # stamped by the application clock, not the database's. The order these
        # were appended in is what `paid_at` replays, and a waiver's moment is
        # the day such a registration became paid — both need more than the
        # whole-second resolution a server default gives on SQLite, and both
        # halves of the journal must read the same clock as their reversals do
        created_at=datetime.now(UTC),
        tournament_id=tournament.id,
        registration_id=registration.id,
        amount_cents=amount_cents,
        currency=currency,
        value_date=value_date,
        source_kind=source_kind,
        source_id=source_id,
        origin=origin,
        rule_id=rule_id,
    )
    session.add(entry)
    session.flush()
    # the relationship is what every derived figure reads, and a caller that
    # credits and then asks the balance in the same request must not be handed
    # a list loaded before this row existed
    if entry not in registration.credits:
        registration.credits.append(entry)
    return entry


def reverse(
    session: Session,
    entry: PaymentCredit,
    *,
    by: str,
    reason: str,
) -> PaymentCredit:
    """Stop a credit counting, recording when, by whom and why.

    Once. A credit already reversed is returned untouched rather than reversed
    again, so that two callers racing to undo one thing do not each claim to
    have done it. Crediting the same source afresh afterwards is a new row.
    """
    if entry.reversed_at is None:
        entry.reversed_at = datetime.now(UTC)
        entry.reversed_by = by
        entry.reversed_reason = reason
        session.flush()
    return entry


def reverse_for_rule(
    session: Session, rule_id: int, *, by: str, reason: str
) -> list[PaymentCredit]:
    """Every live credit a rule decided, reversed together.

    Unconditional, deliberately. The version this replaces declined to reverse
    a credit when the registration was no longer paid, which left the amount
    standing in a counter while deleting the rule that was its only record.
    What becomes of the registration afterwards is a derivation and re-answers
    itself; there is nothing here to decide.
    """
    entries = list(
        session.scalars(
            select(PaymentCredit).where(
                PaymentCredit.rule_id == rule_id,
                PaymentCredit.reversed_at.is_(None),
            )
        )
    )
    return [reverse(session, entry, by=by, reason=reason) for entry in entries]


def reverse_for_source(
    session: Session,
    tournament: Tournament,
    source_kind: CreditSource,
    source_id: int,
    *,
    by: str,
    reason: str,
) -> list[PaymentCredit]:
    """Every live credit one source row made, reversed together — one
    transaction across all the registrations it covered, or one recorded
    payment."""
    entries = list(
        session.scalars(
            select(PaymentCredit).where(
                PaymentCredit.tournament_id == tournament.id,
                PaymentCredit.source_kind == source_kind,
                PaymentCredit.source_id == source_id,
                PaymentCredit.reversed_at.is_(None),
            )
        )
    )
    return [reverse(session, entry, by=by, reason=reason) for entry in entries]


def credits_of_source(
    session: Session,
    tournament: Tournament,
    source_kind: CreditSource,
    source_id: int,
) -> list[PaymentCredit]:
    """What one source row credited and to whom, live rows only — what a
    reversal is about to undo, so a console can state it before it happens."""
    return list(
        session.scalars(
            select(PaymentCredit).where(
                PaymentCredit.tournament_id == tournament.id,
                PaymentCredit.source_kind == source_kind,
                PaymentCredit.source_id == source_id,
                PaymentCredit.reversed_at.is_(None),
            )
        )
    )


def grant_waiver(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    *,
    reason: str | None,
    granted_by: str,
) -> PaymentWaiver:
    """Record that this registration is settled with no money passing.

    Appends rather than overwrites: a registration waived, unwaived and waived
    again for a different reason keeps every reason it was ever given, where
    the two fields this replaces kept only the last.
    """
    entry = PaymentWaiver(
        created_at=datetime.now(UTC),
        tournament_id=tournament.id,
        registration_id=registration.id,
        reason=reason,
        granted_by=granted_by,
    )
    session.add(entry)
    session.flush()
    if entry not in registration.waivers:
        registration.waivers.append(entry)
    return entry


def revoke_waiver(
    session: Session,
    registration: Registration,
    *,
    revoked_by: str,
) -> PaymentWaiver | None:
    """Withdraw the waiver standing over this registration, leaving it and its
    reason readable. Returns None where none stood."""
    entry = registration.active_waiver
    if entry is None:
        return None
    entry.revoked_at = datetime.now(UTC)
    entry.revoked_by = revoked_by
    session.flush()
    return entry


def paid_at(registration: Registration, tournament: Tournament) -> datetime | None:
    """The day this registration became paid, as an instant.

    The value date of the credit that first brought the balance within
    tolerance, found by accumulating the live credits of the paying lane in the
    order they were appended. A bare day carries no clock, so it is returned as
    the instant that day begins in the tournament's own zone, exactly as the
    stored field this replaces held it.

    Where a waiver alone settles the registration there is no credit to date it
    by, and the day the waiver was granted is the answer — the mark stamping
    its own moment, as it always did.

    Where credits were appended out of the order the money actually arrived in,
    the answer may precede a credit already counted. That is accepted rather
    than corrected: the question is which credit completed the balance, not
    which day is latest (spec `payment-ledger`).

    Takes the tournament rather than reading `registration.tournament` because
    the zone and the tolerance are both its to supply, and a zero-argument
    property would hide two dependencies it cannot honestly do without.
    """
    if not registration.settled:
        return None
    which = registration.settling_lane
    if which is None:
        waiver = registration.active_waiver
        return waiver.created_at if waiver is not None else None
    total_cents = (
        registration.total_amount if which == "local" else (registration.total_eur or 0)
    ) * 100
    tolerance = registration.tolerance_cents(tournament, which)
    running = 0
    for entry in registration.live_credits:
        if registration.lane_of(entry.currency) != which:
            continue
        running += entry.amount_cents
        if total_cents - running <= tolerance:
            return setup.start_of_local_day(entry.value_date, tournament.timezone)
    return None
