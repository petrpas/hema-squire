"""Long console work, recorded so it can be watched.

An operation is a row, not a request. Starting one writes the row and returns;
the work runs behind it and the console learns how it is going by reading the
row (spec console-operations, An operation is a record, not a request). That is
the whole of why a reload no longer loses sight of a running import.

Two rules hold the record honest:

- **A count never runs ahead of its results.** `advance` commits the caller's
  work and the raised count in one transaction, so a `done` of sixty always
  describes sixty stored results.
- **Nothing is left running.** Every path out of `run_now` concludes the row,
  and startup concludes whatever a dead process left behind.

The startup sweep (`sweep_interrupted`) is sound only because one process runs
every operation — see the comment there before adding a second worker.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Operation, OperationKind, OperationStatus, Tournament

logger = logging.getLogger(__name__)


class OperationInFlightError(Exception):
    """A tournament already has work running. Any kind blocks any other: the
    three operations read and write the same decisions and the same replayed
    rows, and two at once is a question this design does not answer."""

    def __init__(self, kind: OperationKind) -> None:
        self.kind = kind
        super().__init__(f"operation already running: {kind}")


def running(session: Session, tournament: Tournament) -> Operation | None:
    return session.scalars(
        select(Operation).where(
            Operation.tournament_id == tournament.id,
            Operation.finished_at.is_(None),
        )
    ).first()


def latest_concluded(session: Session, tournament: Tournament) -> list[Operation]:
    """The most recent concluded operation of each kind — what the panels show
    to an organizer who was not watching when the work landed."""
    found: list[Operation] = []
    for kind in OperationKind:
        operation = session.scalars(
            select(Operation)
            .where(
                Operation.tournament_id == tournament.id,
                Operation.kind == kind,
                Operation.finished_at.is_not(None),
            )
            .order_by(Operation.id.desc())
            .limit(1)
        ).first()
        if operation is not None:
            found.append(operation)
    return found


def start(
    session: Session,
    tournament: Tournament,
    kind: OperationKind,
    total: int,
    started_by: int,
) -> Operation:
    """Record the run, or refuse because one is already under way."""
    in_flight = running(session, tournament)
    if in_flight is not None:
        raise OperationInFlightError(in_flight.kind)
    operation = Operation(
        tournament_id=tournament.id,
        kind=kind,
        status=OperationStatus.RUNNING,
        total=total,
        done=0,
        started_by=started_by,
        outcome={},
    )
    session.add(operation)
    session.commit()
    return operation


def advance(session: Session, operation: Operation, units: int) -> None:
    """Commit the caller's finished work together with the count of it.

    The two travel in one transaction on purpose: a count that outlives a
    rolled-back result would claim work nobody can find (spec, The count never
    runs ahead of the results). Callers write their results into the same
    session and call this instead of committing themselves.

    `units` is added, not assigned — `done` counts what has finished, never
    where the loop has reached, which is what keeps it correct if the units are
    ever run out of order (design D6).
    """
    operation.done += units
    session.commit()


def conclude(
    session: Session,
    operation: Operation,
    status: OperationStatus,
    outcome: dict | None = None,
) -> None:
    operation.status = status
    operation.finished_at = datetime.now(UTC)
    if outcome is not None:
        operation.outcome = outcome
    session.commit()


def sweep_interrupted(session: Session) -> int:
    """Conclude every operation the previous process left running.

    Sound only under one worker: `deploy/Dockerfile` runs uvicorn with
    `--workers 1` and calls that an invariant, so an unconcluded row cannot
    belong to a live run — there is no other run. Under two workers this would
    be actively wrong, marking a peer's live work dead, so a second worker has
    to confront this function first.

    Interruption is not failure. What the run committed before it stopped
    stands, and starting the same work again reuses it (spec, Work interrupted
    by a restart is recovered at startup).
    """
    stranded = list(session.scalars(select(Operation).where(Operation.finished_at.is_(None))))
    for operation in stranded:
        operation.status = OperationStatus.INTERRUPTED
        operation.finished_at = datetime.now(UTC)
    if stranded:
        session.commit()
        logger.info("concluded %d operation(s) interrupted by a restart", len(stranded))
    return len(stranded)


def run_now(operation_id: int, body: Callable[[Session, Operation], dict]) -> None:
    """Run `body` over its own session and conclude the operation either way.

    The body gets a fresh session: the request's is closed long before this
    runs. Anything the body raises concludes the operation as failed — an
    operation that raises must never be left running, since that is the state
    the startup sweep exists to clean up and nothing else should produce it
    (design D3).

    Sync, and separate from the scheduling below, so that both the background
    path and a test can drive exactly the same work.
    """
    session = SessionLocal()
    try:
        operation = session.get(Operation, operation_id)
        if operation is None:  # pragma: no cover - the row was just written
            logger.error("operation %s vanished before its work began", operation_id)
            return
        try:
            outcome = body(session, operation)
        except Exception as error:
            logger.exception("operation %s failed", operation_id)
            session.rollback()
            operation = session.get(Operation, operation_id)
            conclude(
                session,
                operation,
                OperationStatus.FAILED,
                {"error": str(error) or error.__class__.__name__},
            )
        else:
            conclude(session, operation, OperationStatus.DONE, outcome)
    finally:
        session.close()


def run_in_background(
    operation_id: int, body: Callable[[Session, Operation], dict]
) -> asyncio.Task:
    """Schedule `run_now` behind the request that started the operation.

    `asyncio.create_task` over `asyncio.to_thread`, the idiom `scheduler_loop`
    already uses, because every LLM call on these paths is sync.
    """

    async def _task() -> None:
        await asyncio.to_thread(run_now, operation_id, body)

    return asyncio.create_task(_task())
