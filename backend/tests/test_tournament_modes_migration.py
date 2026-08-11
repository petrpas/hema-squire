"""Exercises the actual `b3d1f0a72c45` Alembic revision (not a simulation)
against a throwaway sqlite file, shelling out so the run picks up a fresh
`HEMA_SQUIRE_DATABASE_URL` (design tournament-modes D9, task 1.5). Mirrors
tests/test_discipline_identity_migration.py's approach.

The derivation is generous by design: any evidence at all turns a feature on,
so an existing organizer's console looks exactly as it did before, while a
never-configured draft lands in easy mode."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "8cea4fd092f9"
REVISION = "b3d1f0a72c45"

FLAGS = ("feature_schedule", "feature_payments", "feature_teams", "feature_extras")


def _run_alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _seed_tournament(
    conn: sqlite3.Connection,
    tid: int,
    slug: str,
    *,
    bank_account: str | None = None,
    payment_mode: str = "immediate",
) -> None:
    conn.execute(
        "INSERT INTO tournaments (id, slug, display_name, date, language, "
        "reservation_validity_days, reminder_day, amount_tolerance_percent, "
        "unpaid_list_treatment, weapon_rental_fee, afterparty_fee, hr_category_map, "
        "organizers, discounts, qualification_open, local_currency, "
        "eur_payments_enabled, expiry_grace_hours, vs_year, vs_series, vs_next_seq, "
        "payment_mode, bank_account) "
        "VALUES (?, ?, ?, '2026-10-11', 'cs', 10, 5, 5, "
        "'greyed', 0, 0, '{}', '[]', '[]', 1, 'CZK', 0, 48, 2026, ?, 1, ?, ?)",
        (tid, slug, slug, tid, payment_mode, bank_account),
    )


def _seed_discipline(
    conn: sqlite3.Connection,
    did: int,
    tid: int,
    *,
    kind: str = "individual",
    schedule_when: str | None = None,
    schedule_where: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO disciplines (id, tournament_id, slug, name, kind, capacity, "
        "weapon, gender, material, ordinal, schedule_when, schedule_where) "
        "VALUES (?, ?, ?, ?, ?, 10, 'LS', '', '', 0, ?, ?)",
        (did, tid, f"d{did}", f"Discipline {did}", kind, schedule_when, schedule_where),
    )


def _flags(db_path: Path) -> dict[str, dict[str, int]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        f"SELECT slug, {', '.join(FLAGS)} FROM tournaments ORDER BY id"  # noqa: S608
    ).fetchall()
    conn.close()
    return {row[0]: dict(zip(FLAGS, row[1:], strict=True)) for row in rows}


@pytest.fixture
def pre_migration_db(tmp_path) -> Path:
    db_path = tmp_path / "tournament_modes.sqlite"
    result = _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(db_path)

    # a fully configured tournament: schedule fields, an account, a team
    # discipline and an extra item
    _seed_tournament(conn, 1, "configured", bank_account="CZ6508000000192000145399")
    _seed_discipline(conn, 1, 1, schedule_when="Saturday 09:00", schedule_where="Hall A")
    _seed_discipline(conn, 2, 1, kind="team")
    conn.execute(
        "INSERT INTO extra_items (id, tournament_id, name, category, price, max_qty, "
        "option_choices) VALUES (1, 1, 'Afterparty', 'afterparty', 300, 1, '[]')"
    )

    # a bare draft: one individual discipline, nothing else
    _seed_tournament(conn, 2, "bare-draft")
    _seed_discipline(conn, 3, 2)

    # payments evidenced by an ingested transaction alone
    _seed_tournament(conn, 3, "ingested-only")
    conn.execute(
        "INSERT INTO bank_transactions (id, tournament_id, external_id, source, date, "
        "amount_cents, currency, ingested_at) "
        "VALUES (1, 3, 'tx-1', 'fio', '2026-05-01', 120000, 'CZK', '2026-05-01 10:00:00')"
    )

    # payments evidenced by a non-immediate payment mode alone
    _seed_tournament(conn, 4, "deposit-mode", payment_mode="deposit")

    # an empty string is not evidence: a schedule field cleared back to blank
    _seed_tournament(conn, 5, "blank-schedule")
    _seed_discipline(conn, 4, 5, schedule_when="", schedule_where="")

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def migrated_db(pre_migration_db) -> Path:
    result = _run_alembic("upgrade", REVISION, db_path=pre_migration_db)
    assert result.returncode == 0, result.stderr
    return pre_migration_db


def test_configured_tournament_keeps_everything_visible(migrated_db):
    assert _flags(migrated_db)["configured"] == {
        "feature_schedule": 1,
        "feature_payments": 1,
        "feature_teams": 1,
        "feature_extras": 1,
    }


def test_bare_draft_lands_in_easy_mode(migrated_db):
    assert _flags(migrated_db)["bare-draft"] == dict.fromkeys(FLAGS, 0)


def test_payments_derived_from_an_ingested_transaction_alone(migrated_db):
    flags = _flags(migrated_db)["ingested-only"]
    assert flags["feature_payments"] == 1
    assert flags["feature_schedule"] == 0
    assert flags["feature_teams"] == 0
    assert flags["feature_extras"] == 0


def test_payments_derived_from_a_non_immediate_mode(migrated_db):
    assert _flags(migrated_db)["deposit-mode"]["feature_payments"] == 1


def test_blank_schedule_fields_are_not_evidence(migrated_db):
    assert _flags(migrated_db)["blank-schedule"]["feature_schedule"] == 0


def test_downgrade_drops_the_flags(migrated_db):
    result = _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(migrated_db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tournaments)")}
    conn.close()
    assert not set(FLAGS) & columns
