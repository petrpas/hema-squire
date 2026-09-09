"""Exercises the actual `52ba5b743d48` Alembic revision (not a simulation)
against a throwaway sqlite file, shelling out so the run picks up a fresh
`HEMA_SQUIRE_DATABASE_URL` (design discipline-identity Migration Plan,
task 9.10). Mirrors tests/test_vs_migration.py's approach."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "a3f7c9d21e08"


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
        "eur_payments_enabled, expiry_grace_hours, vs_year, vs_series, vs_next_seq) "
        "VALUES (?, ?, ?, '2026-10-11', 'cs', 10, 5, 5, "
        "'greyed', 0, 0, '{}', '[]', '[]', 1, 'CZK', 0, 48, 2026, ?, 1)",
        (tid, slug, slug, tid),
    )


def _seed_discipline(conn: sqlite3.Connection, did: int, tid: int, code: str, name: str) -> None:
    conn.execute(
        "INSERT INTO disciplines (id, tournament_id, code, name, kind, capacity) "
        "VALUES (?, ?, ?, ?, 'individual', 10)",
        (did, tid, code, name),
    )


@pytest.fixture(scope="module")
def _pre_migration_template(tmp_path_factory) -> Path:
    # built once per module and copied per test (conftest
    # `migration_db_copy`), so each test still gets a database it may
    # migrate or downgrade freely without rebuilding this one
    db_path = tmp_path_factory.mktemp("discipline_identity") / "discipline_identity.sqlite"
    result = _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(db_path)
    _seed_tournament(conn, 1, "spring-2026")
    _seed_discipline(conn, 1, 1, "LS", "Longsword Open")
    _seed_discipline(conn, 2, 1, "SAW", "Sabre Women")
    _seed_discipline(conn, 3, 1, "Plastic SB", "Sword & Buckler (Plastic)")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture(scope="module")
def _migrated_template(_pre_migration_template) -> Path:
    # pinned to the revision under test, not "head" — a later migration
    # (add-field-validation's discipline slug rewrite) legitimately touches
    # the same table and would otherwise make this test depend on it
    result = _run_alembic("upgrade", "52ba5b743d48", db_path=_pre_migration_template)
    assert result.returncode == 0, result.stderr
    return _pre_migration_template


@pytest.fixture
def migrated_db(_migrated_template, migration_db_copy) -> Path:
    return migration_db_copy(_migrated_template)


def test_upgrade_backfills_slug_equal_to_old_code_and_classification(migrated_db):
    conn = sqlite3.connect(migrated_db)
    rows = {
        row[0]: row[1:]
        for row in conn.execute(
            "SELECT slug, weapon, gender, material FROM disciplines ORDER BY id"
        )
    }
    conn.close()
    assert rows["LS"] == ("LS", "", "")
    assert rows["SAW"] == ("SA", "W", "")
    assert rows["Plastic SB"] == ("SB", "", "Plastic")


def test_upgrade_preserves_unique_constraint_shape(migrated_db):
    conn = sqlite3.connect(migrated_db)
    # a second discipline with the same slug in the same tournament is refused
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO disciplines "
            "(tournament_id, slug, weapon, gender, material, name, kind, capacity) "
            "VALUES (1, 'LS', 'LS', '', '', 'Longsword Again', 'individual', 5)"
        )
    conn.close()


def test_downgrade_drops_classification_columns_and_restores_code(migrated_db):
    result = _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(migrated_db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(disciplines)")}
    conn.close()
    assert not {"slug", "weapon", "gender", "material"} & columns
    assert "code" in columns


def test_downgrade_raises_on_two_disciplines_sharing_a_taxonomy_code(migrated_db):
    """A tournament with two tiers of one weapon (design discipline-identity)
    — expressible only after this split, since the old schema's identity was
    the taxonomy code itself — has no representation in the pre-split schema;
    downgrade must fail loudly rather than silently collapsing one tier into
    the other."""
    conn = sqlite3.connect(migrated_db)
    # a second LS tier, created post-migration: distinct slug, same taxonomy
    # code ("LS") as the first discipline
    conn.execute(
        "INSERT INTO disciplines "
        "(tournament_id, slug, weapon, gender, material, name, kind, capacity) "
        "VALUES (1, 'LS-2', 'LS', '', '', 'Longsword Top', 'individual', 5)"
    )
    conn.commit()
    conn.close()

    result = _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    assert result.returncode != 0
    assert "taxonomy code" in result.stderr
