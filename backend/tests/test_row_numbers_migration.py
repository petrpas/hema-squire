"""Exercises the actual `d2a71f4b83c6` revision against a throwaway sqlite
file: the number backfill, and the rewrite of the retired `load` and `parsing`
phases onto the rules that carry them."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "b3d7f1a05c92"



def _insert(conn, table: str, **values) -> None:
    """Insert a row, filling every other NOT NULL column the schema at this
    revision demands with a placeholder. The test cares about a handful of
    columns; naming the rest would be a copy of the schema that goes stale."""
    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
    row = dict(values)
    for _cid, name, kind, notnull, default, pk in columns:
        if name in row or default is not None or pk:
            continue
        if not notnull:
            continue
        row[name] = 0 if kind.upper() in ("INTEGER", "BOOLEAN", "FLOAT", "NUMERIC") else ""
    names = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    conn.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", list(row.values()))


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


def _seed(db_path: Path) -> None:
    """One tournament with two registrations and a two-row imported batch, plus
    rules in each of the two retired phases, on each kind of target."""
    conn = sqlite3.connect(db_path)
    _insert(conn, "tournaments", id=1, slug="cup", display_name="Cup", date="2026-12-05",
            language="cs", organizers="[]", discounts="[]", hr_category_map="{}",
            local_currency="CZK")
    for fencer_id, email in ((1, "a@example.com"), (2, "b@example.com")):
        _insert(conn, "fencers", id=fencer_id, email=email, password_hash="x",
                display_name=email[0].upper(), role="organizer", language="cs")
    # deliberately out of id order, so the backfill is seen to follow the
    # registration moment rather than the primary key
    for reg_id, moment in ((1, "2026-05-02T10:00:00"), (2, "2026-05-01T10:00:00")):
        _insert(conn, "registrations", id=reg_id, tournament_id=1, fencer_id=reg_id,
                state="reserved", vs=1000000 + reg_id, total_amount=800,
                refund_state="not_applicable", weapon_rentals="[]", registered_at=moment)
    _insert(conn, "import_batches", id=1, tournament_id=1, filename="regs.csv",
            uploaded_by=1, row_count=2)
    for row_number, key in ((1, "aaaa"), (2, "bbbb")):
        _insert(conn, "imported_rows", batch_id=1, tournament_id=1,
                row_number=row_number, key=key, raw="{}")
    for rule_id, phase, target in (
        (1, "load", "imp:aaaa"),
        (2, "parsing", "imp:bbbb"),
        (3, "parsing", "reg:1"),
        (4, "matching", "reg:2"),
    ):
        _insert(conn, "rules", id=rule_id, tournament_id=1, phase=phase,
                kind="field_edit", target=target, created_by=1,
                payload=json.dumps({"field": "club", "value": "X"}))
    conn.commit()
    conn.close()


@pytest.fixture
def migrated_db(tmp_path) -> Path:
    db_path = tmp_path / "row_numbers.sqlite"
    _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    _seed(db_path)
    _run_alembic("upgrade", "head", db_path=db_path)
    return db_path


def test_backfill_numbers_registrations_then_the_latest_batch(migrated_db):
    conn = sqlite3.connect(migrated_db)
    rows = conn.execute(
        "SELECT row_id, number FROM sheet_row_numbers ORDER BY number"
    ).fetchall()
    conn.close()
    # registrations by registration moment — reg:2 registered first — then the
    # imported batch in file order
    assert rows == [("reg:2", 1), ("reg:1", 2), ("imp:aaaa", 3), ("imp:bbbb", 4)]


def test_retired_phases_are_rewritten_by_what_the_rule_targets(migrated_db):
    conn = sqlite3.connect(migrated_db)
    rows = dict(conn.execute("SELECT id, phase FROM rules ORDER BY id").fetchall())
    conn.close()
    assert rows == {
        1: "import",  # a Load rule was always about the file
        2: "import",  # a Parsing rule on an imported row: how the file was read
        3: "fencers",  # a Parsing rule on a registration: a decision about a fencer
        4: "matching",  # every other phase is left alone
    }


def test_downgrade_drops_the_table_and_restores_the_old_names(migrated_db):
    _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    conn = sqlite3.connect(migrated_db)
    tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    phases = {row[0] for row in conn.execute("SELECT DISTINCT phase FROM rules")}
    conn.close()
    assert "sheet_row_numbers" not in tables
    assert phases == {"load", "parsing", "matching"}
