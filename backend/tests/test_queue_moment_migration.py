"""Exercises the actual `e3a5c07d19b4` Alembic revision against a throwaway
sqlite file, shelling out so the run picks up a fresh
`HEMA_SQUIRE_DATABASE_URL`. Mirrors tests/test_registrations_kept_by_migration.py.

The contract is that nothing reorders on deploy: every placement's queue moment
is what its queue was ordered by until now — the registration time for an
individual placement, the entry moment for a team (design demotion-hardening,
Migration Plan)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "d4a1c8b7e310"
REVISION = "e3a5c07d19b4"

REGISTERED_EARLY = "2026-03-01 09:15:00.000000"
REGISTERED_LATE = "2026-03-04 18:40:00.000000"
TEAM_ENTERED = "2026-03-06 12:00:00.000000"


def _run_alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _insert(conn: sqlite3.Connection, table: str, **values: object) -> None:
    """Insert a row, filling every other required column with a placeholder of
    its type — the columns this migration reads are the ones named."""
    for _cid, name, kind, notnull, default, pk in conn.execute(f"PRAGMA table_info({table})"):
        if name in values or not notnull or default is not None or pk:
            continue
        kind = (kind or "").upper()
        if "INT" in kind or "BOOL" in kind or "NUMERIC" in kind or "FLOAT" in kind:
            values[name] = 0
        elif "DATE" in kind:
            values[name] = "2026-10-11"
        elif "JSON" in kind:
            values[name] = "[]"
        else:
            values[name] = f"{name}-{len(values)}"
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))


@pytest.fixture(scope="module")
def _pre_migration_template(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("queue_moment") / "queue_moment.sqlite"
    result = _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(db_path)
    _insert(conn, "tournaments", id=1, slug="t", vs_series=1)
    _insert(conn, "disciplines", id=1, tournament_id=1, slug="ls", capacity=1, kind="individual")
    _insert(conn, "disciplines", id=2, tournament_id=1, slug="team", capacity=1, kind="team")
    for rid in (1, 2):
        _insert(conn, "fencers", id=rid, email=f"f{rid}@example.org", display_name=f"F{rid}")
    _insert(
        conn,
        "registrations",
        id=1,
        tournament_id=1,
        fencer_id=1,
        state="reserved",
        registered_at=REGISTERED_EARLY,
    )
    _insert(
        conn,
        "registrations",
        id=2,
        tournament_id=1,
        fencer_id=2,
        state="reserved",
        registered_at=REGISTERED_LATE,
    )
    _insert(conn, "registration_disciplines", registration_id=1, discipline_id=1, is_substitute=0)
    _insert(conn, "registration_disciplines", registration_id=2, discipline_id=1, is_substitute=1)
    _insert(
        conn,
        "teams",
        id=1,
        tournament_id=1,
        discipline_id=2,
        registration_id=2,
        name="Team",
        waitlisted=1,
        created_at=TEAM_ENTERED,
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def pre_migration_db(_pre_migration_template, migration_db_copy) -> Path:
    return migration_db_copy(_pre_migration_template)


def test_moments_are_what_the_queue_was_ordered_by(pre_migration_db):
    result = _run_alembic("upgrade", REVISION, db_path=pre_migration_db)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(pre_migration_db)
    entries = conn.execute(
        "SELECT registration_id, queued_since, promoted_unpaid FROM registration_disciplines"
        " ORDER BY registration_id"
    ).fetchall()
    teams = conn.execute("SELECT waitlisted_since, promoted_unpaid FROM teams").fetchall()
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(registration_disciplines)")}
    conn.close()
    assert entries == [(1, REGISTERED_EARLY, 0), (2, REGISTERED_LATE, 0)]
    assert teams == [(TEAM_ENTERED, 0)]
    assert columns["queued_since"][3] == 1, "NOT NULL"


def test_the_migration_is_reversible(pre_migration_db):
    _run_alembic("upgrade", REVISION, db_path=pre_migration_db)
    result = _run_alembic("downgrade", PREVIOUS_REVISION, db_path=pre_migration_db)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(pre_migration_db)
    entry_columns = {row[1] for row in conn.execute("PRAGMA table_info(registration_disciplines)")}
    team_columns = {row[1] for row in conn.execute("PRAGMA table_info(teams)")}
    conn.close()
    assert not {"queued_since", "promoted_unpaid"} & entry_columns
    assert not {"waitlisted_since", "promoted_unpaid"} & team_columns
