"""The production shape of a SQLite connection (deployment spec: "SQLite runs in
WAL mode with enforced integrity"). The engine fixture applies the same pragmas
the application engine gets, so what these tests assert is what production does.
"""

import sqlite3
import threading
import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import apply_sqlite_pragmas
from app.models import Fencer, FencerProfileAudit


def _file_engine(path):
    engine = create_engine(f"sqlite:///{path}")
    apply_sqlite_pragmas(engine)
    return engine


def test_pragmas_are_set_on_every_connection(tmp_path):
    engine = _file_engine(tmp_path / "pragmas.sqlite")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    # a second connection, because the listener runs per connect and a pooled
    # engine hands out more than one
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_contending_writer_waits_instead_of_failing(tmp_path):
    """The registration burst plus the scheduler's own writes: the second writer
    must wait for the first rather than raise `database is locked`."""
    path = tmp_path / "contended.sqlite"
    seed = sqlite3.connect(path)
    seed.execute("create table t (id integer primary key)")
    seed.commit()
    seed.close()

    engine = _file_engine(path)
    holding = threading.Event()
    hold_for = 0.5

    def hold_the_write_lock():
        # the connection is opened here: a sqlite3 connection belongs to the
        # thread that created it
        holder = sqlite3.connect(path, isolation_level=None)
        try:
            holder.execute("begin immediate")
            holder.execute("insert into t (id) values (1)")
            holding.set()
            time.sleep(hold_for)
            holder.commit()
        finally:
            holder.close()

    thread = threading.Thread(target=hold_the_write_lock)
    thread.start()
    try:
        assert holding.wait(timeout=5)
        started = time.monotonic()
        with engine.begin() as conn:
            conn.execute(text("insert into t (id) values (2)"))
        waited = time.monotonic() - started
    finally:
        thread.join()

    # it blocked for most of the holder's transaction rather than failing at once
    assert waited > hold_for / 2
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from t")).scalar() == 2


def test_foreign_keys_are_enforced(engine):
    """An orphan write fails where it is written. Without enforcement it would
    sit in the database until a future Postgres migration rejected it."""
    with Session(engine) as session:
        session.add(FencerProfileAudit(fencer_id=999_999, field="email"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_a_satisfied_foreign_key_still_writes(engine):
    with Session(engine) as session:
        fencer = Fencer(email="fk@example.com", display_name="FK", password_hash=None)
        session.add(fencer)
        session.commit()
        session.add(FencerProfileAudit(fencer_id=fencer.id, field="email"))
        session.commit()
        assert session.query(FencerProfileAudit).count() == 1
