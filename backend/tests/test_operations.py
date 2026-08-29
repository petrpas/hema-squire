"""The operation record: starting, refusing, counting, concluding, sweeping."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app import operations
from app.models import (
    Fencer,
    ImportDecision,
    Operation,
    OperationKind,
    OperationStatus,
    Role,
    Tournament,
)


def make_tournament(session: Session, slug: str = "cup") -> Tournament:
    # vs_series is unique within a year, so a second tournament needs its own
    series = session.query(Tournament).count() + 1
    tournament = Tournament(
        slug=slug,
        display_name=slug.title(),
        date=date(2026, 12, 5),
        vs_year=2026,
        vs_series=series,
    )
    session.add(tournament)
    session.commit()
    return tournament


def make_organizer(session: Session, email: str = "organizer@example.com") -> Fencer:
    fencer = Fencer(
        email=email, display_name="Organizer", password_hash="x", role=Role.ORGANIZER
    )
    session.add(fencer)
    session.commit()
    return fencer


def test_start_records_the_run(engine):
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)

        operation = operations.start(
            session, tournament, OperationKind.PARSE, total=220, started_by=organizer.id
        )

        assert operation.id is not None
        assert operation.status == OperationStatus.RUNNING
        assert operation.total == 220
        assert operation.done == 0
        assert operation.finished_at is None
        assert operations.running(session, tournament) is operation


def test_second_start_is_refused_whatever_its_kind(engine):
    """Any kind blocks any other: the three operations write the same
    decisions (spec console-operations, One operation at a time)."""
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operations.start(
            session, tournament, OperationKind.PARSE, total=10, started_by=organizer.id
        )

        with pytest.raises(operations.OperationInFlightError) as refused:
            operations.start(
                session, tournament, OperationKind.DEDUP, total=5, started_by=organizer.id
            )

        assert refused.value.kind == OperationKind.PARSE


def test_another_tournament_is_unaffected(engine):
    with Session(engine) as session:
        one = make_tournament(session, "cup")
        other = make_tournament(session, "open")
        organizer = make_organizer(session)
        operations.start(session, one, OperationKind.PARSE, total=10, started_by=organizer.id)

        second = operations.start(
            session, other, OperationKind.PARSE, total=10, started_by=organizer.id
        )

        assert second.status == OperationStatus.RUNNING


def test_a_concluded_operation_no_longer_blocks(engine):
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        first = operations.start(
            session, tournament, OperationKind.PARSE, total=10, started_by=organizer.id
        )
        operations.conclude(session, first, OperationStatus.DONE, {"rows": 10})

        assert operations.running(session, tournament) is None
        operations.start(
            session, tournament, OperationKind.MATCH, total=3, started_by=organizer.id
        )


def test_advance_commits_work_and_count_together(engine):
    """`done` counts stored results, so the two land in one transaction
    (spec, The count never runs ahead of the results)."""
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.PARSE, total=40, started_by=organizer.id
        )

        session.add(
            ImportDecision(
                tournament_id=tournament.id, kind="parse", key="abc", payload={}, source="llm"
            )
        )
        operations.advance(session, operation, 20)
        operation_id = operation.id

    with Session(engine) as fresh:
        assert fresh.get(Operation, operation_id).done == 20
        assert fresh.query(ImportDecision).count() == 1


def test_rollback_leaves_neither_the_decision_nor_the_count(engine):
    """The other half of the same rule: uncommitted work leaves no count
    behind claiming it."""
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.PARSE, total=40, started_by=organizer.id
        )

        session.add(
            ImportDecision(
                tournament_id=tournament.id, kind="parse", key="abc", payload={}, source="llm"
            )
        )
        operation.done += 20
        operation_id = operation.id
        session.rollback()

    with Session(engine) as fresh:
        assert fresh.get(Operation, operation_id).done == 0
        assert fresh.query(ImportDecision).count() == 0


def test_advance_adds_rather_than_assigns(engine):
    """A counter, not an index into a sequence — so it stays correct however
    units are ordered (design D6)."""
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.PARSE, total=60, started_by=organizer.id
        )

        operations.advance(session, operation, 20)
        operations.advance(session, operation, 20)
        operations.advance(session, operation, 20)

        assert operation.done == 60


def test_conclude_records_the_outcome(engine):
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.MATCH, total=3, started_by=organizer.id
        )

        operations.conclude(
            session, operation, OperationStatus.DONE, {"matched": 2, "unmatched": 1}
        )

        assert operation.status == OperationStatus.DONE
        assert operation.finished_at is not None
        assert operation.outcome == {"matched": 2, "unmatched": 1}


def test_latest_concluded_is_one_per_kind(engine):
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        for index in range(2):
            operation = operations.start(
                session, tournament, OperationKind.PARSE, total=1, started_by=organizer.id
            )
            operations.conclude(session, operation, OperationStatus.DONE, {"run": index})
        match = operations.start(
            session, tournament, OperationKind.MATCH, total=1, started_by=organizer.id
        )
        operations.conclude(session, match, OperationStatus.DONE, {"matched": 1})

        concluded = {op.kind: op for op in operations.latest_concluded(session, tournament)}

        assert set(concluded) == {OperationKind.PARSE, OperationKind.MATCH}
        assert concluded[OperationKind.PARSE].outcome == {"run": 1}


def test_sweep_concludes_what_a_dead_process_left_running(engine):
    """Nothing unconcluded can belong to a live run under one worker
    (spec, Restart clears a phantom)."""
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        stranded = operations.start(
            session, tournament, OperationKind.PARSE, total=220, started_by=organizer.id
        )
        operations.advance(session, stranded, 60)
        swept = operations.sweep_interrupted(session)

        assert swept == 1
        assert stranded.status == OperationStatus.INTERRUPTED
        assert stranded.finished_at is not None
        # what it had committed stands: interruption is not a rollback
        assert stranded.done == 60
        assert operations.running(session, tournament) is None


def test_sweep_leaves_concluded_operations_alone(engine):
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        finished = operations.start(
            session, tournament, OperationKind.PARSE, total=1, started_by=organizer.id
        )
        operations.conclude(session, finished, OperationStatus.DONE, {"rows": 1})

        assert operations.sweep_interrupted(session) == 0
        assert finished.status == OperationStatus.DONE


def test_startup_sweep_runs_against_the_configured_engine(engine, monkeypatch):
    """The lifespan hook, wired to the same recovery (design D5)."""
    import app.db
    from app.main import _sweep_interrupted_operations

    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        stranded = operations.start(
            session, tournament, OperationKind.DEDUP, total=5, started_by=organizer.id
        )
        stranded_id = stranded.id

    monkeypatch.setattr(app.db, "engine", engine)
    _sweep_interrupted_operations()

    with Session(engine) as fresh:
        assert fresh.get(Operation, stranded_id).status == OperationStatus.INTERRUPTED


def bind_session_factory(monkeypatch, engine) -> None:
    """Point the runner's own session at the test engine."""
    from sqlalchemy.orm import sessionmaker

    monkeypatch.setattr(
        operations,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )


def test_a_body_that_raises_concludes_the_operation_failed(engine, monkeypatch):
    """Nothing stays running after it stops (spec, Nothing stays running
    after it stops)."""
    bind_session_factory(monkeypatch, engine)
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.MATCH, total=3, started_by=organizer.id
        )
        operation_id, tournament_id = operation.id, tournament.id

    def body(session, operation):
        raise RuntimeError("the model is unreachable")

    operations.run_now(operation_id, body)

    with Session(engine) as fresh:
        concluded = fresh.get(Operation, operation_id)
        assert concluded.status == OperationStatus.FAILED
        assert concluded.finished_at is not None
        assert "unreachable" in concluded.outcome["error"]
        # and the tournament is free to try again
        assert operations.running(fresh, fresh.get(Tournament, tournament_id)) is None


def test_a_failure_keeps_what_the_body_committed(engine, monkeypatch):
    """A partial run's stored work stands (spec table-import, Partial parse
    survives a failure)."""
    bind_session_factory(monkeypatch, engine)
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.PARSE, total=40, started_by=organizer.id
        )
        operation_id, tournament_id = operation.id, tournament.id

    def body(session, operation):
        session.add(
            ImportDecision(
                tournament_id=tournament_id, kind="parse", key="abc", payload={}, source="llm"
            )
        )
        operations.advance(session, operation, 20)
        raise RuntimeError("the model went away")

    operations.run_now(operation_id, body)

    with Session(engine) as fresh:
        concluded = fresh.get(Operation, operation_id)
        assert concluded.status == OperationStatus.FAILED
        assert concluded.done == 20
        assert fresh.query(ImportDecision).count() == 1


def test_a_completed_body_records_its_outcome(engine, monkeypatch):
    bind_session_factory(monkeypatch, engine)
    with Session(engine) as session:
        tournament = make_tournament(session)
        organizer = make_organizer(session)
        operation = operations.start(
            session, tournament, OperationKind.DEDUP, total=2, started_by=organizer.id
        )
        operation_id = operation.id

    operations.run_now(operation_id, lambda session, operation: {"merged": 1})

    with Session(engine) as fresh:
        concluded = fresh.get(Operation, operation_id)
        assert concluded.status == OperationStatus.DONE
        assert concluded.outcome == {"merged": 1}
