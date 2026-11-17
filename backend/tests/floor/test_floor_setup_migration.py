"""Exercises the actual `floor_0008` revision against a throwaway sqlite file
(design rework-floor-setup, Migration Plan): a day pin becomes the
discipline's day, a reserve piste serves every formatted discipline as
reserve, staffing becomes referees per stage, and the parameters' keys move.
Mirrors tests/test_discipline_identity_migration.py's approach."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _run_alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def _template(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("floor_setup") / "floor_setup.sqlite"
    result = _run_alembic("upgrade", "floor_0007", db_path=db_path)
    assert result.returncode == 0, result.stderr
    # foreign keys stay off in a bare connection: the tournament row itself
    # is not what this migration reads
    conn = sqlite3.connect(db_path)
    for did, slug in ((1, "LS"), (2, "SB")):
        conn.execute(
            "INSERT INTO disciplines (id, tournament_id, slug, name, capacity, kind, weapon, "
            "gender, material, ordinal) VALUES (?, 1, ?, ?, 10, 'individual', ?, 'open', "
            "'steel', ?)",
            (did, slug, slug, slug, did),
        )
    conn.execute(
        'INSERT INTO floor_days (id, tournament_id, date, start, "end", breaks) '
        "VALUES (1, 1, '2099-12-05', '09:00:00', '19:00:00', '[]'), "
        "(2, 1, '2099-12-06', '09:00:00', '19:00:00', '[]')"
    )
    conn.execute(
        "INSERT INTO floor_pins (id, tournament_id, kind, target, value, created_at) "
        "VALUES (1, 1, 'day', '2', '{\"day\": \"2099-12-06\"}', '2099-01-01 00:00:00')"
    )
    conn.execute(
        "INSERT INTO floor_pistes (id, tournament_id, name, ordinal, reserve) "
        "VALUES (1, 1, '1', 1, 0), (2, 1, '2', 2, 1)"
    )
    for did in (1, 2):
        conn.execute(
            "INSERT INTO floor_formats (tournament_id, discipline_id, pool_min, pool_max, "
            "third_place, staffing, slot_pool_bout, slot_elim_bout, slot_pool_overhead) "
            "VALUES (1, ?, 5, 7, 0, ?, 4, 6, 5)",
            (did, json.dumps({"referee": 2, "judge": 1, "table": 0})),
        )
    conn.execute(
        "INSERT INTO floor_officials (id, tournament_id, name, roles, discipline_ids, ordinal) "
        "VALUES (1, 1, 'Eva', '[\"referee\"]', '[1]', 1)"
    )
    conn.execute(
        "INSERT INTO floor_settings (tournament_id, params) VALUES (1, ?)",
        (json.dumps({"finals_last": True, "prefer_larger_pools": False, "club_weight": 4}),),
    )
    conn.commit()
    conn.close()
    result = _run_alembic("upgrade", "floor_0008", db_path=db_path)
    assert result.returncode == 0, result.stderr
    return db_path


@pytest.fixture
def migrated(_template, migration_db_copy) -> sqlite3.Connection:
    return sqlite3.connect(migration_db_copy(_template))


def test_a_day_pin_becomes_the_disciplines_day(migrated):
    days = dict(migrated.execute("SELECT discipline_id, day_id FROM floor_discipline_days"))

    assert days == {1: 1, 2: 2}
    assert migrated.execute("SELECT count(*) FROM floor_pins WHERE kind = 'day'").fetchone() == (0,)


def test_pistes_serve_every_formatted_discipline_with_their_reserve(migrated):
    rows = set(
        migrated.execute("SELECT piste_id, discipline_id, reserve FROM floor_piste_disciplines")
    )

    assert rows == {(1, 1, 0), (1, 2, 0), (2, 1, 1), (2, 2, 1)}


def test_staffing_becomes_referees_per_stage(migrated):
    rows = set(
        migrated.execute(
            "SELECT discipline_id, referees_pool, referees_elim, pause_between_pools "
            "FROM floor_formats"
        )
    )

    assert rows == {(1, 2, 2, 5), (2, 2, 2, 5)}


def test_officials_keep_their_disciplines_and_are_main(migrated):
    served = list(
        migrated.execute(
            "SELECT official_id, discipline_id, reserve FROM floor_official_disciplines"
        )
    )
    main = migrated.execute("SELECT main FROM floor_officials").fetchone()

    assert (served, main) == ([(1, 1, 0)], (1,))


def test_the_parameters_keys_move_and_scope_is_read_from_what_is_stored(migrated):
    params, schedule, multi, officials = migrated.execute(
        "SELECT params, plan_schedule, multi_day, plan_officials FROM floor_settings"
    ).fetchone()

    assert json.loads(params) == {"finals": "day", "pool_size": "smaller", "club_weight": 4}
    assert (schedule, multi, officials) == (1, 1, 1)


def test_the_downgrade_runs(_template, migration_db_copy):
    db_path = migration_db_copy(_template)

    result = _run_alembic("downgrade", "floor_0007", db_path=db_path)

    assert result.returncode == 0, result.stderr
