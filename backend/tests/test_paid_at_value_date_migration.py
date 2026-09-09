"""Exercises the `d5a83c1f206e` revision against a throwaway sqlite file: paid
registrations dated by the day their money arrived, and the rows the migration
deliberately leaves alone (change paid-at-is-value-date, task 4.4)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "c4f2a91b7e30"

# every registration below was stamped with the same import instant, which is
# the fault this migration exists to correct
IMPORT_INSTANT = "2026-09-01 09:15:00.000000"


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


def _registration(conn, registration_id, **values):
    """One fencer per registration: the table admits one registration per
    fencer and tournament."""
    _insert(
        conn,
        "fencers",
        id=registration_id,
        email=f"f{registration_id}@example.com",
        password_hash="x",
        display_name=f"F{registration_id}",
        role="fencer",
        language="cs",
    )
    _insert(
        conn,
        "registrations",
        id=registration_id,
        tournament_id=1,
        fencer_id=registration_id,
        total_amount=1000,
        amount_paid_cents=0,
        **{"state": "paid", **values},
    )


def _transaction(conn, external_id, registration_id, date):
    _insert(
        conn,
        "bank_transactions",
        tournament_id=1,
        external_id=external_id,
        source="csv",
        date=date,
        amount_cents=100000,
        currency="CZK",
        status="matched",
        matched_registration_id=registration_id,
        rejected_fencer_ids="[]",
    )


def _seed(db_path: Path) -> None:
    """Four registrations, one per shape the migration must distinguish:
    settled by one transaction, by two, by a recorded payment, and by hand."""
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
        timezone="Europe/Prague",
    )

    _registration(conn, 1, vs=2601001, paid_at=IMPORT_INSTANT)
    _transaction(conn, "t1", 1, "2026-08-03")

    _registration(conn, 2, vs=2601002, paid_at=IMPORT_INSTANT)
    _transaction(conn, "t2a", 2, "2026-08-05")
    _transaction(conn, "t2b", 2, "2026-08-12")

    _registration(conn, 3, vs=2601003, paid_at=IMPORT_INSTANT)
    _insert(
        conn,
        "manual_payments",
        id=1,
        tournament_id=1,
        registration_id=3,
        amount_cents=100000,
        currency="CZK",
        received_on="2026-08-01",
        method="cash",
        recorded_by="Org <org@example.com>",
    )

    _registration(
        conn,
        4,
        vs=2601004,
        paid_at=IMPORT_INSTANT,
        settled_by_hand_at=IMPORT_INSTANT,
        settled_by_hand_reason="volný vstup",
    )

    # still reserved, holding a partial credit: nothing to date
    _registration(conn, 5, vs=2601005, state="reserved", paid_at=None)
    _transaction(conn, "t5", 5, "2026-08-20")

    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def _migrated_template(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("paid_at_value_date") / "paid_at_value_date.sqlite"
    _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    _seed(db_path)
    _run_alembic("upgrade", "head", db_path=db_path)
    return db_path


@pytest.fixture
def migrated_db(_migrated_template, migration_db_copy) -> Path:
    return migration_db_copy(_migrated_template)


def paid_at(conn, registration_id):
    (value,) = conn.execute(
        "SELECT paid_at FROM registrations WHERE id = ?", (registration_id,)
    ).fetchone()
    return value


def test_one_transaction_dates_the_registration_to_its_day(migrated_db):
    """3 August in Prague begins at 22:00Z on 2 August."""
    conn = sqlite3.connect(migrated_db)
    assert paid_at(conn, 1).startswith("2026-08-02 22:00:00")
    conn.close()


def test_two_transactions_take_the_later_day(migrated_db):
    """The registration was covered when the second arrived."""
    conn = sqlite3.connect(migrated_db)
    assert paid_at(conn, 2).startswith("2026-08-11 22:00:00")
    conn.close()


def test_a_recorded_payment_is_left_alone(migrated_db):
    """Recoverable in principle, deliberately not recovered: a registration may
    hold both a transaction and a recorded payment, and deciding which wins is
    a rule nobody asked for (design D6)."""
    conn = sqlite3.connect(migrated_db)
    assert paid_at(conn, 3) == IMPORT_INSTANT
    conn.close()


def test_a_hand_mark_is_left_alone(migrated_db):
    """No money arrived, so there is no day to read — and the moment of the
    mark is the right answer already."""
    conn = sqlite3.connect(migrated_db)
    assert paid_at(conn, 4) == IMPORT_INSTANT
    conn.close()


def test_an_unpaid_registration_gains_no_date(migrated_db):
    """It holds a transaction and no paid date; the migration writes to rows
    that have one, never to rows that do not."""
    conn = sqlite3.connect(migrated_db)
    assert paid_at(conn, 5) is None
    conn.close()


def test_the_downgrade_is_a_no_op_and_says_so(migrated_db):
    """The instants this replaced are not in `registrations` to restore. The
    downgrade runs — a deployment must be able to step back past it — and
    leaves the dates where they are."""
    _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    conn = sqlite3.connect(migrated_db)
    assert paid_at(conn, 1).startswith("2026-08-02 22:00:00")
    conn.close()
