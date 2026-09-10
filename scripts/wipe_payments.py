#!/usr/bin/env python
"""Remove every trace of the payments side, so a test environment can take the
whole flow again from an empty statement.

    ./scripts/wipe_payments.py                              # report, touch nothing
    ./scripts/wipe_payments.py --yes                        # every tournament
    ./scripts/wipe_payments.py --yes --tournament my-slug   # just this one
    ./scripts/wipe_payments.py --yes --with-symbols         # give the VS back too

It deletes in place and keeps nothing, so reporting is the default and `--yes`
is the flag. Which database it reaches is `HEMA_SQUIRE_DATABASE_URL` (the
settings prefix is not optional — a bare `DATABASE_URL` is ignored, and the
default is the dev database under `backend/`). The first line of output is the
resolved path; read it before passing `--yes`.

**Not the same thing as the console's own "Smazat platby"**, and deliberately
outside it. `app/paymentsclear.py` refuses the moment any transaction holds a
live credit, because for a real tournament the import can be asserted never to
have happened while a fencer who was told they are paid cannot be un-told. That
refusal is right and stays. This script exists for the one case it makes
impossible: a test environment whose credited state is the thing being thrown
away. It sends no mail, records no operation and writes nothing to the rule
journal — it is not an act of the application.

What goes: bank transactions, the credit journal, payment events, hand-recorded
payments, waivers, every `payment_link` rule with its journal entries, the
cached readings of statement rows, and the statement-interpretation operations.
Each registration's `refund_state` and `reminded_at` go back to their defaults;
what a registration was credited is not stored anywhere, so nothing else has to
be unwound.

What stays, and why the script says so on the way out: the roster, each
registration's state and payment window, and the variable symbols. An expired
reservation stays expired, so a re-imported payment for it will land flagged
rather than paid — the script counts those so the number is not a surprise.
Symbols are kept because they are issued once and never reused; `--with-symbols`
overrides that for a test environment, where re-testing the issuing step is the
point.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# set on the child when this script re-runs itself, so a missing module there is
# reported rather than causing another re-exec
_REEXEC = "HEMA_SQUIRE_WIPE_PAYMENTS_REEXEC"


def reexec_under_uv() -> None:
    """Re-run this script through `uv run` when the app's imports are missing.

    The dependencies are `backend/.venv`, managed by uv, not whatever
    environment happens to be active. Cheaper to relaunch correctly than to
    make the caller remember `cd backend && uv run`.
    """
    if os.environ.get(_REEXEC) == "1":
        return
    try:
        import sqlalchemy  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return
    try:
        result = subprocess.run(
            ["uv", "run", "python", str(Path(__file__).resolve()), *sys.argv[1:]],
            cwd=BACKEND,
            env={**os.environ, _REEXEC: "1"},
        )
    except FileNotFoundError:
        print(
            "this needs the backend environment, and uv is not installed.\n"
            "Install uv (https://docs.astral.sh/uv/) or run it yourself:\n"
            "  cd backend && uv run python ../scripts/wipe_payments.py",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    raise SystemExit(result.returncode)


reexec_under_uv()

from sqlalchemy import delete, func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import (  # noqa: E402
    BankTransaction,
    ImportDecision,
    ManualPayment,
    Operation,
    OperationKind,
    PaymentCredit,
    PaymentEvent,
    PaymentWaiver,
    RefundState,
    Registration,
    RegistrationState,
    Rule,
    RuleJournalEntry,
    Tournament,
)
from app.statements import DECISION_KIND as STATEMENT_ROW  # noqa: E402


def tournament_ids(session: Session, slug: str | None) -> list[int]:
    """The tournaments in scope, or an empty list where a named slug is absent —
    the caller reports that rather than silently wiping everything."""
    query = select(Tournament.id)
    if slug is not None:
        query = query.where(Tournament.slug == slug)
    return list(session.scalars(query))


def survey(session: Session, ids: list[int]) -> dict[str, int]:
    """What is there to remove, counted before anything is. Also what the wipe
    leaves behind that a reader of the result would want to know about."""

    def count(model, *where) -> int:
        return session.scalar(select(func.count()).select_from(model).where(*where)) or 0

    transactions = list(
        session.scalars(select(BankTransaction.id).where(BankTransaction.tournament_id.in_(ids)))
    )
    registrations = list(
        session.scalars(select(Registration.id).where(Registration.tournament_id.in_(ids)))
    )
    return {
        "transactions": len(transactions),
        "credits": count(PaymentCredit, PaymentCredit.tournament_id.in_(ids)),
        "live_credits": count(
            PaymentCredit,
            PaymentCredit.tournament_id.in_(ids),
            PaymentCredit.reversed_at.is_(None),
        ),
        "events": count(PaymentEvent, PaymentEvent.tournament_id.in_(ids)),
        "recorded": count(ManualPayment, ManualPayment.tournament_id.in_(ids)),
        "waivers": count(PaymentWaiver, PaymentWaiver.tournament_id.in_(ids)),
        "links": count(Rule, Rule.tournament_id.in_(ids), Rule.kind == "payment_link"),
        "readings": count(
            ImportDecision,
            ImportDecision.tournament_id.in_(ids),
            ImportDecision.kind == STATEMENT_ROW,
        ),
        "operations": count(
            Operation, Operation.tournament_id.in_(ids), Operation.kind == OperationKind.STATEMENT
        ),
        "symbols": count(
            Registration, Registration.tournament_id.in_(ids), Registration.vs.is_not(None)
        ),
        "registrations": len(registrations),
    }


def wipe(session: Session, ids: list[int], *, with_symbols: bool) -> None:
    """Delete the payment rows, in the order the foreign keys allow.

    The order is `paymentsclear`'s own and for its reasons: credits before the
    rules, because a credit a payment link decided names that rule; events after
    the credits and before the transactions they both point at; the cached
    statement readings last, being the mechanism rather than the subject.
    """
    session.execute(delete(PaymentCredit).where(PaymentCredit.tournament_id.in_(ids)))

    doomed = list(
        session.scalars(
            select(Rule.id).where(Rule.tournament_id.in_(ids), Rule.kind == "payment_link")
        )
    )
    if doomed:
        session.execute(delete(RuleJournalEntry).where(RuleJournalEntry.rule_id.in_(doomed)))
        session.execute(delete(Rule).where(Rule.id.in_(doomed)))

    session.execute(delete(PaymentEvent).where(PaymentEvent.tournament_id.in_(ids)))
    session.execute(delete(ManualPayment).where(ManualPayment.tournament_id.in_(ids)))
    session.execute(delete(PaymentWaiver).where(PaymentWaiver.tournament_id.in_(ids)))
    session.execute(delete(BankTransaction).where(BankTransaction.tournament_id.in_(ids)))
    session.execute(
        delete(ImportDecision).where(
            ImportDecision.tournament_id.in_(ids), ImportDecision.kind == STATEMENT_ROW
        )
    )
    session.execute(
        delete(Operation).where(
            Operation.tournament_id.in_(ids), Operation.kind == OperationKind.STATEMENT
        )
    )

    # the two fields on a registration that a payment moved. What it was
    # credited is not among them: that is a sum over the journal, and the
    # journal is gone
    for registration in session.scalars(
        select(Registration).where(Registration.tournament_id.in_(ids))
    ):
        registration.refund_state = RefundState.NOT_APPLICABLE
        registration.reminded_at = None
        if with_symbols:
            registration.vs = None

    session.commit()


def expired_count(session: Session, ids: list[int]) -> int:
    """Reservations the clock has already taken. A payment re-imported for one
    of these lands flagged rather than paid, which is worth stating before the
    organizer wonders why."""
    return (
        session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.tournament_id.in_(ids),
                Registration.state == RegistrationState.EXPIRED,
            )
        )
        or 0
    )


def target() -> str:
    """The database this will actually delete from, as a path a reader can
    recognise.

    `settings.database_url` is relative — `sqlite:///./hema_squire.sqlite` — and
    this script re-runs itself with `backend/` as its working directory, so the
    URL as configured names a different file depending on where it is read.
    Printing the resolved path is the difference between "some sqlite file" and
    "the one the dev server is using", and this script deletes what it finds.
    """
    url = settings.database_url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    return f"{prefix}{Path(url[len(prefix) :]).resolve()}"


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--yes",
        action="store_true",
        help="actually delete; without it the run reports what it found and stops",
    )
    parser.add_argument(
        "--tournament", metavar="SLUG", help="scope to one tournament (default: all of them)"
    )
    parser.add_argument(
        "--with-symbols",
        action="store_true",
        help="clear the variable symbols too, so issuing can be tested again",
    )
    args = parser.parse_args()

    print(f"database: {target()}")

    with Session(engine) as session:
        ids = tournament_ids(session, args.tournament)
        if not ids:
            where = (
                f"no tournament with slug {args.tournament!r}"
                if args.tournament
                else "no tournaments"
            )
            print(where, file=sys.stderr)
            return 1
        scope = args.tournament or f"{len(ids)} tournaments"
        counts = survey(session, ids)
        expired = expired_count(session, ids)

    print(f"scope: {scope}")
    print(
        "  {transactions} transactions, {credits} credits ({live_credits} live),\n"
        "  {events} events, {recorded} recorded payments, {waivers} waivers,\n"
        "  {links} payment links, {readings} statement readings, "
        "{operations} statement operations".format(**counts)
    )
    if args.with_symbols:
        print(f"  {counts['symbols']} variable symbols will be given back")

    # reporting is the default and deleting is the flag, the opposite way round
    # from `reset_local_db`. That script moves the database aside and writes a
    # dump first, so its worst outcome is a restore; this one deletes in place
    # with nothing kept, and the database it reaches depends on a relative URL
    if not args.yes:
        print("\nnothing was touched. Pass --yes to delete the rows above.")
        return 0

    with Session(engine) as session:
        wipe(session, ids, with_symbols=args.with_symbols)

    print("\ndone. the payments side is empty.")
    if not args.with_symbols:
        print(f"kept: {counts['symbols']} variable symbols (--with-symbols clears them)")
    if expired:
        print(
            f"note: {expired} of {counts['registrations']} registrations are expired.\n"
            "      A payment re-imported for one of those lands flagged, not paid."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
