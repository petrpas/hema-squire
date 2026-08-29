"""The three console operations as records: 202, refusal, progress, recovery.

The endpoints return the moment the record exists, so every assertion about
what the work produced reads the record rather than the response (spec
console-operations, An operation is a record, not a request).
"""

import io
from datetime import datetime, timedelta

from conftest import settle
from sqlalchemy.orm import Session

from app import operations
from app.dedup import get_dedup_llm
from app.hr_match import get_hr_matcher
from app.importer import ParsedFencer, get_import_parser
from app.main import app
from app.models import (
    Fencer,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    Operation,
    OperationKind,
    OperationStatus,
    SheetRowNumber,
    Tournament,
    TournamentOrganizer,
)

CSV_HEADER = "Time,Name,Club,Nationality,Disciplines,hr,Note\n"


def rows_csv(count: int) -> str:
    return CSV_HEADER + "".join(
        f"1.4.2026 10:{index:02d}:00,Fencer {index},Club,CZ,sabre,,\n" for index in range(count)
    )


class CountingParser:
    """One call per batch, and a place to fail on a chosen one."""

    def __init__(self, fail_on: int | None = None):
        self.calls = 0
        self.rows_seen = 0
        self.fail_on = fail_on

    def parse_batch(self, rows, disciplines, rentals):
        self.calls += 1
        if self.fail_on is not None and self.calls == self.fail_on:
            raise RuntimeError("the model is unreachable")
        self.rows_seen += len(rows)
        return [
            ParsedFencer(
                registration_time="2026-04-01T10:00:00",
                name=raw["Name"],
                disciplines=["SA"],
            )
            for raw in rows
        ]


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 200, "fee": 800},
        headers=organizer,
    )


def upload(client, organizer, content):
    return client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(content.encode()), "text/csv")},
        headers=organizer,
    )


def test_upload_returns_before_the_parse(client, auth_headers, engine):
    """The batch and its rows land in the request; only the parse is
    background work (spec table-import, Upload returns before the parse)."""
    organizer = auth_headers()
    setup(client, organizer)
    parser = CountingParser()
    app.dependency_overrides[get_import_parser] = lambda: parser

    response = upload(client, organizer, rows_csv(45))

    assert response.status_code == 202
    body = response.json()
    assert body["rows"] == 45
    assert "operation_id" in body

    concluded = settle(client, organizer, kind="parse")
    assert concluded["status"] == "done"
    assert concluded["total"] == 45
    assert concluded["done"] == 45
    assert concluded["outcome"]["parsed"] == 45
    # 45 rows in batches of twenty: three calls, three commits
    assert parser.calls == 3


def test_reused_rows_are_not_work(client, auth_headers):
    """A re-upload of an unchanged file starts no operation at all
    (spec console-operations, Reused rows are not work)."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: CountingParser()
    upload(client, organizer, rows_csv(5))
    settle(client, organizer)

    body = upload(client, organizer, rows_csv(5)).json()

    assert body["parsed"] == 0
    assert body["reused"] == 5
    assert "operation_id" not in body
    # the earlier parse is still the latest one on the record
    assert settle(client, organizer, kind="parse")["total"] == 5


def test_no_llm_records_the_batch_and_starts_nothing(client, auth_headers):
    """(spec table-import, No LLM configured)"""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: None

    body = upload(client, organizer, rows_csv(3)).json()

    assert body["detail"] == "llm_not_configured"
    assert body["unparsed"] == 3
    assert "operation_id" not in body
    listing = client.get("/api/tournaments/cup/operations", headers=organizer).json()
    assert listing["running"] is None
    assert listing["concluded"] == []


def test_a_failed_parse_keeps_the_batches_it_finished(client, auth_headers, engine):
    """(spec table-import, Partial parse survives a failure)"""
    organizer = auth_headers()
    setup(client, organizer)
    # fails on its third batch: forty rows stored, the rest not
    parser = CountingParser(fail_on=3)
    app.dependency_overrides[get_import_parser] = lambda: parser

    assert upload(client, organizer, rows_csv(50)).status_code == 202

    concluded = settle(client, organizer, kind="parse")
    assert concluded["status"] == "failed"
    assert concluded["done"] == 40
    assert "unreachable" in concluded["outcome"]["error"]
    with Session(engine) as session:
        stored = session.query(ImportDecision).filter_by(kind="parse").count()
    assert stored == 40


def test_rerunning_after_a_failure_does_only_the_remainder(client, auth_headers):
    """The decision cache makes recovery cheap (spec console-operations,
    Re-running finishes the remainder)."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: CountingParser(fail_on=3)
    upload(client, organizer, rows_csv(50))
    assert settle(client, organizer, kind="parse")["status"] == "failed"

    second = CountingParser()
    app.dependency_overrides[get_import_parser] = lambda: second
    upload(client, organizer, rows_csv(50))

    concluded = settle(client, organizer, kind="parse")
    assert concluded["status"] == "done"
    # only the ten rows the failed run never reached
    assert concluded["total"] == 10
    assert second.rows_seen == 10


def test_an_interrupted_parse_keeps_what_it_committed(client, auth_headers, engine):
    """(spec console-operations, Restart clears a phantom / Re-running
    finishes the remainder)"""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: CountingParser(fail_on=3)
    upload(client, organizer, rows_csv(50))

    # put the record back into the state a killed process leaves behind
    with Session(engine) as session:
        operation = session.query(Operation).one()
        operation.status = OperationStatus.RUNNING
        operation.finished_at = None
        operation.outcome = {}
        session.commit()
        assert operations.sweep_interrupted(session) == 1

    listing = client.get("/api/tournaments/cup/operations", headers=organizer).json()
    assert listing["running"] is None
    assert listing["concluded"][0]["status"] == "interrupted"
    assert listing["concluded"][0]["done"] == 40

    second = CountingParser()
    app.dependency_overrides[get_import_parser] = lambda: second
    upload(client, organizer, rows_csv(50))
    assert settle(client, organizer, kind="parse")["total"] == 10


def test_a_start_while_work_runs_is_refused(client, auth_headers, engine):
    """The record refuses, so a second tab and a second organizer are covered
    (spec console-operations, One operation at a time for a tournament)."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: CountingParser()
    app.dependency_overrides[get_hr_matcher] = lambda: object()
    app.dependency_overrides[get_dedup_llm] = lambda: object()

    with Session(engine) as session:
        tournament = session.query(Tournament).one()
        organizer_id = session.query(Fencer).one().id
        operations.start(session, tournament, OperationKind.PARSE, 100, organizer_id)

    refusals = [
        upload(client, organizer, rows_csv(2)),
        client.post("/api/tournaments/cup/import/match", headers=organizer),
        client.post("/api/tournaments/cup/import/dedup", headers=organizer),
    ]

    for response in refusals:
        assert response.status_code == 409, response.text
        assert response.json()["detail"] == {"code": "operation_running", "kind": "parse"}


def test_operations_listing_refuses_a_stranger(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    outsider = auth_headers(email="someone@example.com", name="Someone")

    assert client.get("/api/tournaments/cup/operations", headers=outsider).status_code == 403


def test_the_batch_is_whole_before_the_parse_begins(client, auth_headers, engine):
    """Intake commits inside the request, so an abandoned upload response still
    leaves the batch and all its rows (spec table-import, Batch survives an
    abandoned upload response). The parser looks for them from a session of its
    own on its first call — the point at which a client would have given up.
    """
    organizer = auth_headers()
    setup(client, organizer)
    seen: dict[str, int] = {}

    class LookingParser(CountingParser):
        def parse_batch(self, rows, disciplines, rentals):
            if not seen:
                with Session(engine) as onlooker:
                    seen["batches"] = onlooker.query(ImportBatch).count()
                    seen["rows"] = onlooker.query(ImportedRow).count()
                    seen["numbers"] = onlooker.query(SheetRowNumber).count()
            return super().parse_batch(rows, disciplines, rentals)

    app.dependency_overrides[get_import_parser] = lambda: LookingParser()
    upload(client, organizer, rows_csv(30))

    # every row of the file, and its number, before a single one was parsed
    assert seen == {"batches": 1, "rows": 30, "numbers": 30}
    assert settle(client, organizer, kind="parse")["outcome"]["parsed"] == 30


def test_a_fresh_console_reports_work_it_did_not_start(client, auth_headers, engine):
    """The reload case, whole: the record is what the console reads, so a page
    that never saw the upload still reports it (spec console-operations, Reload
    during a long import)."""
    organizer = auth_headers()
    setup(client, organizer)

    # the state a client that dropped mid-parse leaves behind: a batch whole,
    # an operation partway
    app.dependency_overrides[get_import_parser] = lambda: CountingParser(fail_on=3)
    upload(client, organizer, rows_csv(50))
    with Session(engine) as session:
        operation = session.query(Operation).one()
        operation.status = OperationStatus.RUNNING
        operation.finished_at = None
        session.commit()

    # a console loading afresh — no memory of the upload, only the record
    listing = client.get("/api/tournaments/cup/operations", headers=organizer).json()

    assert listing["running"]["kind"] == "parse"
    assert (listing["running"]["done"], listing["running"]["total"]) == (40, 50)
    assert listing["running"]["finished_at"] is None
    # and a second organizer of the same tournament sees the same thing: the
    # record is the tournament's, not the starting session's
    second = auth_headers(email="second@example.com", name="Second")
    with Session(engine) as session:
        tournament = session.query(Tournament).one()
        colleague = session.query(Fencer).filter_by(email="second@example.com").one()
        session.add(
            TournamentOrganizer(tournament_id=tournament.id, fencer_id=colleague.id)
        )
        session.commit()

    theirs = client.get("/api/tournaments/cup/operations", headers=second)
    assert theirs.status_code == 200, theirs.text
    assert theirs.json()["running"]["kind"] == "parse"


def test_a_restart_clears_the_phantom_and_leaves_the_work(client, auth_headers, engine):
    """The restart case, whole (spec console-operations, Restart clears a
    phantom): the sweep concludes what the dead process left, the console
    reports it as interrupted rather than running, and the next start is free
    to go."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: CountingParser(fail_on=3)
    upload(client, organizer, rows_csv(50))
    with Session(engine) as session:
        operation = session.query(Operation).one()
        operation.status = OperationStatus.RUNNING
        operation.finished_at = None
        operation.outcome = {}
        session.commit()

    # the process comes back up
    with Session(engine) as session:
        assert operations.sweep_interrupted(session) == 1

    listing = client.get("/api/tournaments/cup/operations", headers=organizer).json()
    assert listing["running"] is None
    interrupted = listing["concluded"][0]
    assert interrupted["status"] == "interrupted"
    assert interrupted["done"] == 40

    # the tournament is not stuck: the next run starts and finishes the rest
    second = CountingParser()
    app.dependency_overrides[get_import_parser] = lambda: second
    assert upload(client, organizer, rows_csv(50)).status_code == 202
    assert settle(client, organizer, kind="parse")["status"] == "done"
    assert second.rows_seen == 10


def test_the_start_moment_is_reported_with_its_zone(client, auth_headers):
    """SQLite hands stored instants back without tzinfo. Serialized that way,
    the console reads a UTC instant as its own local time and states the wrong
    hour — so the endpoint stamps the zone the instant was always in."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_import_parser] = lambda: CountingParser()
    upload(client, organizer, rows_csv(3))

    concluded = settle(client, organizer, kind="parse")

    for field in ("started_at", "finished_at"):
        moment = datetime.fromisoformat(concluded[field])
        assert moment.tzinfo is not None, f"{field} carries no zone: {concluded[field]}"
        assert moment.utcoffset() == timedelta(0)
