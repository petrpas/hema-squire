"""Exercises the actual `b5e9c3d7f2a1` revision against a throwaway sqlite
file, shelling out so the run picks up its own database URL and feed-token key
(change encrypt-fio-token, design D4)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "a4d8f2c6e1b9"
REVISION = "b5e9c3d7f2a1"
KEY = Fernet.generate_key().decode()
PLAIN = "fio-plain-token-0123456789abcdef"


def _run_alembic(*args: str, db_path: Path, key: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}",
        "HEMA_SQUIRE_FIO_TOKEN_KEY": key,
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _seed(conn: sqlite3.Connection, tid: int, token: str | None) -> None:
    """A tournament row with every NOT NULL column filled, whatever the schema
    at this revision demands, so the test does not restate it."""
    columns = conn.execute("PRAGMA table_info(tournaments)").fetchall()
    values: dict[str, object] = {"id": tid, "slug": f"t{tid}", "vs_series": tid}
    for _, name, kind, notnull, default, _ in columns:
        if name in values or not notnull or default is not None:
            continue
        kind = kind.upper()
        if "INT" in kind or "BOOL" in kind:
            values[name] = 2099 if name == "vs_year" else 0
        elif "DATE" in kind:
            values[name] = "2099-12-05"
        elif "JSON" in kind:
            values[name] = "[]"
        else:
            values[name] = "x"
    values["fio_token"] = token
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO tournaments ({names}) VALUES ({marks})", tuple(values.values()))  # noqa: S608 - column names from the schema itself


def _tokens(db_path: Path) -> dict[int, str | None]:
    with sqlite3.connect(db_path) as conn:
        return dict(conn.execute("SELECT id, fio_token FROM tournaments").fetchall())


@pytest.fixture(scope="module")
def template(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("seal") / "template.sqlite"
    result = _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path, key="")
    assert result.returncode == 0, result.stderr
    return db_path


@pytest.fixture
def db(template, migration_db_copy) -> Path:
    db_path = migration_db_copy(template)
    already = Fernet(KEY.encode()).encrypt(b"already-sealed").decode()
    stale = Fernet(Fernet.generate_key()).encrypt(b"under-a-lost-key").decode()
    with sqlite3.connect(db_path) as conn:
        _seed(conn, 1, PLAIN)
        _seed(conn, 2, already)
        _seed(conn, 3, stale)
        _seed(conn, 4, None)
    return db_path


def test_plain_tokens_are_sealed_and_sealed_ones_left_alone(db):
    """And the downgrade opens them back under the same key."""
    before = _tokens(db)

    result = _run_alembic("upgrade", REVISION, db_path=db, key=KEY)

    assert result.returncode == 0, result.stderr
    after = _tokens(db)
    fernet = Fernet(KEY.encode())
    sealed = after[1]
    assert sealed is not None and PLAIN not in sealed
    assert fernet.decrypt(sealed.encode()).decode() == PLAIN
    assert after[2] == before[2]
    # sealed under a key since replaced: left unreadable, never sealed twice
    assert after[3] == before[3]
    assert after[4] is None

    assert _run_alembic("downgrade", PREVIOUS_REVISION, db_path=db, key=KEY).returncode == 0
    restored = _tokens(db)
    assert restored[1] == PLAIN
    assert restored[2] == "already-sealed"
    assert restored[3] is None, "unreadable under either schema, so cleared"


def test_refused_without_a_key_while_plain_tokens_exist(db):
    result = _run_alembic("upgrade", REVISION, db_path=db, key="")

    assert result.returncode != 0
    assert "HEMA_SQUIRE_FIO_TOKEN_KEY" in result.stderr
    assert _tokens(db)[1] == PLAIN, "nothing was left half-done"
    # setting the key and running it again finishes the job
    assert _run_alembic("upgrade", REVISION, db_path=db, key=KEY).returncode == 0
    assert _tokens(db)[1] != PLAIN
