"""Exercises the actual `df6a74c06dfa` Alembic revision (not a simulation)
against a throwaway sqlite file, shelling out so the run picks up a fresh
`HEMA_SQUIRE_DATABASE_URL` rather than the settings singleton other tests
already loaded into this process (design Migration Plan step 4)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "3f7212c247f3"


def _run_alembic(*args: str, db_path: Path) -> None:
    env = {**os.environ, "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}"}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_pre_migration_schema(db_path: Path) -> None:
    """Minimal `tournaments`/`registrations` rows shaped like the schema at
    `PREVIOUS_REVISION`, i.e. with no vs_year/vs_series/vs_next_seq columns."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO tournaments (id, slug, display_name, date, language, "
        "reservation_validity_days, reminder_day, amount_tolerance_percent, "
        "unpaid_list_treatment, weapon_rental_fee, afterparty_fee, hr_category_map, "
        "organizers, discounts, qualification_open, primary_currency, "
        "eur_payments_enabled, expiry_grace_hours) VALUES "
        "(1, 'spring-2026', 'Spring 2026', '2026-04-05', 'cs', 10, 5, 5, "
        "'greyed', 0, 0, '{}', '[]', '[]', 1, 'CZK', 0, 48)"
    )
    conn.execute(
        "INSERT INTO tournaments (id, slug, display_name, date, language, "
        "reservation_validity_days, reminder_day, amount_tolerance_percent, "
        "unpaid_list_treatment, weapon_rental_fee, afterparty_fee, hr_category_map, "
        "organizers, discounts, qualification_open, primary_currency, "
        "eur_payments_enabled, expiry_grace_hours) VALUES "
        "(2, 'autumn-2026', 'Autumn 2026', '2026-10-11', 'cs', 10, 5, 5, "
        "'greyed', 0, 0, '{}', '[]', '[]', 1, 'CZK', 0, 48)"
    )
    conn.execute(
        "INSERT INTO fencers (id, email, password_hash, display_name, role, language) "
        "VALUES (1, 'a@example.com', 'x', 'A', 'fencer', 'cs')"
    )
    conn.execute(
        "INSERT INTO registrations "
        "(id, tournament_id, fencer_id, state, vs, total_amount, refund_state, "
        "weapon_rentals, afterparty, aftersparring, amount_paid_cents) "
        "VALUES (1, 1, 1, 'reserved', 1000001, 800, 'not_applicable', '[]', 0, 0, 0)"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def migrated_db(tmp_path) -> Path:
    db_path = tmp_path / "vs_migration.sqlite"
    _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    _seed_pre_migration_schema(db_path)
    _run_alembic("upgrade", "head", db_path=db_path)
    return db_path


def test_migration_assigns_a_series_to_every_tournament(migrated_db):
    conn = sqlite3.connect(migrated_db)
    rows = conn.execute(
        "SELECT id, vs_year, vs_series, vs_next_seq FROM tournaments ORDER BY id"
    ).fetchall()
    conn.close()
    assert len(rows) == 2
    for _id, vs_year, vs_series, vs_next_seq in rows:
        assert vs_year == 2026
        assert vs_next_seq == 1
    series = {row[2] for row in rows}
    assert series == {1, 2}  # distinct series, same year


def test_migration_leaves_registration_vs_untouched(migrated_db):
    conn = sqlite3.connect(migrated_db)
    row = conn.execute("SELECT id, vs FROM registrations").fetchone()
    conn.close()
    assert row == (1, 1000001)


def test_migration_downgrade_drops_the_new_columns(migrated_db):
    _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    conn = sqlite3.connect(migrated_db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tournaments)")}
    conn.close()
    assert not {"vs_year", "vs_series", "vs_next_seq"} & columns
