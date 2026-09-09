"""Exercises the `a7e6c1b40d92` revision against a throwaway sqlite file: the
collapse of a key held in several batches, and the constraint that replaces
per-batch uniqueness with per-tournament."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "c4d17ea90b52"


def _insert(conn, table: str, **values) -> None:
    """Insert a row, filling every other NOT NULL column the schema at this
    revision demands with a placeholder (as in `test_row_numbers_migration`)."""
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
    """A tournament that uploaded the same export three times, growing: the
    first two rows arrive in every batch, the third in the last two, the fourth
    only in the last. Under the old model that is seven source rows for four
    keys."""
    conn = sqlite3.connect(db_path)
    _insert(
        conn,
        "tournaments",
        id=1,
        slug="cup",
        display_name="Cup",
        date="2026-12-05",
        language="cs",
        organizers="[]",
        discounts="[]",
        hr_category_map="{}",
        local_currency="CZK",
    )
    _insert(
        conn,
        "fencers",
        id=1,
        email="a@example.com",
        password_hash="x",
        display_name="A",
        role="organizer",
        language="cs",
    )
    batches = {
        1: ["aaaa", "bbbb"],
        2: ["aaaa", "bbbb", "cccc"],
        3: ["aaaa", "bbbb", "cccc", "dddd"],
    }
    for batch_id, keys in batches.items():
        _insert(
            conn,
            "import_batches",
            id=batch_id,
            tournament_id=1,
            filename="regs.csv",
            uploaded_by=1,
            row_count=len(keys),
        )
        for row_number, key in enumerate(keys, start=1):
            _insert(
                conn,
                "imported_rows",
                batch_id=batch_id,
                tournament_id=1,
                row_number=row_number,
                key=key,
                raw="{}",
            )
    for number, key in enumerate(batches[3], start=1):
        _insert(conn, "sheet_row_numbers", tournament_id=1, row_id=f"imp:{key}", number=number)
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def _migrated_template(tmp_path_factory) -> Path:
    # built once per module and copied per test (conftest
    # `migration_db_copy`): the alembic run below is the expensive part and
    # is identical for every test in this file
    db_path = tmp_path_factory.mktemp("imported_rows_union") / "imported_rows_union.sqlite"
    _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    _seed(db_path)
    _run_alembic("upgrade", "head", db_path=db_path)
    return db_path


@pytest.fixture
def migrated_db(_migrated_template, migration_db_copy) -> Path:
    return migration_db_copy(_migrated_template)


def test_one_row_survives_per_key_and_it_is_the_earliest(migrated_db):
    conn = sqlite3.connect(migrated_db)
    rows = conn.execute("SELECT key, batch_id FROM imported_rows ORDER BY key").fetchall()
    conn.close()
    # the batch that first carried each key, which is the arrival its number
    # was allocated against
    assert rows == [("aaaa", 1), ("bbbb", 1), ("cccc", 2), ("dddd", 3)]


def test_the_numbers_are_untouched(migrated_db):
    conn = sqlite3.connect(migrated_db)
    numbers = dict(conn.execute("SELECT row_id, number FROM sheet_row_numbers ORDER BY number"))
    conn.close()
    assert numbers == {"imp:aaaa": 1, "imp:bbbb": 2, "imp:cccc": 3, "imp:dddd": 4}


def test_a_key_cannot_be_imported_twice_into_one_tournament(migrated_db):
    conn = sqlite3.connect(migrated_db)
    with pytest.raises(sqlite3.IntegrityError):
        _insert(
            conn, "imported_rows", batch_id=3, tournament_id=1, row_number=9, key="aaaa", raw="{}"
        )
    conn.close()


def test_the_same_key_in_another_tournament_is_fine(migrated_db):
    conn = sqlite3.connect(migrated_db)
    _insert(
        conn,
        "tournaments",
        id=2,
        slug="other",
        display_name="Other",
        date="2026-12-06",
        language="cs",
        organizers="[]",
        discounts="[]",
        hr_category_map="{}",
        local_currency="CZK",
        vs_year=27,
        vs_series=1,
    )
    _insert(
        conn,
        "import_batches",
        id=4,
        tournament_id=2,
        filename="regs.csv",
        uploaded_by=1,
        row_count=1,
    )
    _insert(conn, "imported_rows", batch_id=4, tournament_id=2, row_number=1, key="aaaa", raw="{}")
    conn.commit()
    conn.close()


def test_downgrade_restores_per_batch_uniqueness(migrated_db):
    _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    conn = sqlite3.connect(migrated_db)
    # the collapse is not undone; what comes back is the room for a key to sit
    # in several batches again
    keys = [row[0] for row in conn.execute("SELECT key FROM imported_rows ORDER BY key")]
    _insert(conn, "imported_rows", batch_id=3, tournament_id=1, row_number=9, key="aaaa", raw="{}")
    conn.commit()
    conn.close()
    assert keys == ["aaaa", "bbbb", "cccc", "dddd"]
