"""Exercises the actual `d4e18a3c07b6` Alembic revision against a throwaway
sqlite file, shelling out so the run picks up a fresh
`HEMA_SQUIRE_DATABASE_URL`. Mirrors tests/test_tournament_modes_migration.py.

Unlike the four feature flags, nothing is derived here. Every existing
tournament is Squire-kept because that is what every one of them is: its
registration form is open and its scheduler runs, whatever else it holds. A
tournament that has been imported into is no exception — being imported into
was never what made a tournament the organizer's to keep."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "c3f27a91d0e5"
REVISION = "d4e18a3c07b6"


def _run_alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _seed_tournament(conn: sqlite3.Connection, tid: int, slug: str) -> None:
    conn.execute(
        "INSERT INTO tournaments (id, slug, display_name, date, language, "
        "reservation_validity_days, reminder_day, amount_tolerance_percent, "
        "unpaid_list_treatment, weapon_rental_fee, afterparty_fee, hr_category_map, "
        "organizers, discounts, qualification_open, local_currency, "
        "eur_payments_enabled, expiry_grace_hours, vs_year, vs_series, vs_next_seq, "
        "payment_mode, timezone, feature_schedule, feature_payments, "
        "feature_teams, feature_extras) "
        "VALUES (?, ?, ?, '2026-10-11', 'cs', 10, 5, 5, "
        "'greyed', 0, 0, '{}', '[]', '[]', 1, 'CZK', 0, 48, 2026, ?, 1, "
        "'immediate', 'Europe/Prague', 0, 0, 0, 0)",
        (tid, slug, slug, tid),
    )


@pytest.fixture(scope="module")
def _pre_migration_template(tmp_path_factory) -> Path:
    # built once per module and copied per test (conftest
    # `migration_db_copy`), so each test still gets a database it may
    # migrate or downgrade freely without rebuilding this one
    db_path = tmp_path_factory.mktemp("registrations_kept_by") / "registrations_kept_by.sqlite"
    result = _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(db_path)
    _seed_tournament(conn, 1, "plain")
    # one that has been imported into: the case a derivation would have been
    # tempted by, and the one this migration deliberately does not read
    _seed_tournament(conn, 2, "imported-into")
    conn.execute(
        "INSERT INTO import_batches (id, tournament_id, filename, uploaded_by, "
        "row_count) VALUES (1, 2, 'roster.csv', 1, 54)"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def pre_migration_db(_pre_migration_template, migration_db_copy) -> Path:
    return migration_db_copy(_pre_migration_template)


def _kept_by(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT slug, registrations_kept_by FROM tournaments ORDER BY id"
    ).fetchall()
    conn.close()
    return dict(rows)


def test_every_existing_tournament_is_squire_kept(pre_migration_db):
    result = _run_alembic("upgrade", REVISION, db_path=pre_migration_db)
    assert result.returncode == 0, result.stderr
    assert _kept_by(pre_migration_db) == {
        "plain": "squire",
        "imported-into": "squire",
    }


def test_the_column_is_not_null_after_the_migration(pre_migration_db):
    _run_alembic("upgrade", REVISION, db_path=pre_migration_db)
    conn = sqlite3.connect(pre_migration_db)
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(tournaments)").fetchall()}
    conn.close()
    assert columns["registrations_kept_by"][3] == 1, "NOT NULL"


def test_the_migration_is_reversible(pre_migration_db):
    _run_alembic("upgrade", REVISION, db_path=pre_migration_db)
    result = _run_alembic("downgrade", PREVIOUS_REVISION, db_path=pre_migration_db)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(pre_migration_db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tournaments)").fetchall()}
    conn.close()
    assert "registrations_kept_by" not in columns
