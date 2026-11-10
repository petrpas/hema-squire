"""Exercises the actual `d4a7c2e8b015` revision against a throwaway sqlite
file: roster members that were added before members were numbered are numbered
by it, and the numbers already held are left where they are.

Without this backfill a team tournament's fencer list reads a dash in the
number column for every fighter, which is what `ttt-2027` did — 67 of 67.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "c7f1a3b9e2d4"


def _insert(conn, table: str, **values) -> None:
    """Insert a row, filling every other NOT NULL column the schema at this
    revision demands with a placeholder (as `test_row_numbers_migration`)."""
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
    """Two tournaments, so the numbering is seen to be per tournament: the
    first holds a numbered registration, a team of two members of which one is
    numbered already, and a removed member; the second holds one member and
    nothing numbered, so its own numbering starts at one."""
    conn = sqlite3.connect(db_path)
    # vs_series is unique per year, so the two tournaments say which they are
    # rather than both taking the placeholder
    for tournament_id, slug in ((1, "cup"), (2, "other")):
        _insert(
            conn,
            "tournaments",
            id=tournament_id,
            slug=slug,
            display_name=slug,
            date="2099-12-05",
            language="cs",
            organizers="[]",
            discounts="[]",
            hr_category_map="{}",
            local_currency="CZK",
            vs_year=2099,
            vs_series=tournament_id,
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
    _insert(
        conn,
        "registrations",
        id=1,
        tournament_id=1,
        fencer_id=1,
        state="reserved",
        vs=1000001,
        total_amount=800,
        refund_state="not_applicable",
        weapon_rentals="[]",
        registered_at="2026-05-01T10:00:00",
    )
    # no disciplines: the backfill joins members to teams to tournaments and
    # never looks at what a team competes in
    for team_id, tournament_id in ((1, 1), (2, 2)):
        _insert(
            conn,
            "teams",
            id=team_id,
            tournament_id=tournament_id,
            discipline_id=team_id,
            registration_id=1,
            name=f"Team {team_id}",
        )
    for member_id, team_id, removed in ((1, 1, None), (2, 1, None), (3, 1, "2026-06-01T10:00:00")):
        _insert(
            conn,
            "team_members",
            id=member_id,
            team_id=team_id,
            ordinal=member_id,
            name=f"M{member_id}",
            removed_at=removed,
        )
    _insert(conn, "team_members", id=4, team_id=2, ordinal=1, name="M4")
    # what the first tournament already holds: the registration, and one member
    # added after the allocation reached the roster diff
    for row_id, number in (("reg:1", 1), ("mem:2", 2)):
        _insert(conn, "sheet_row_numbers", tournament_id=1, row_id=row_id, number=number)
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def _migrated_template(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("member_numbers") / "member_numbers.sqlite"
    _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    _seed(db_path)
    _run_alembic("upgrade", "head", db_path=db_path)
    return db_path


@pytest.fixture
def migrated_db(_migrated_template, migration_db_copy) -> Path:
    return migration_db_copy(_migrated_template)


def _numbers(db_path: Path, tournament_id: int) -> list[tuple[str, int]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT row_id, number FROM sheet_row_numbers WHERE tournament_id = ? ORDER BY number",
        (tournament_id,),
    ).fetchall()
    conn.close()
    return rows


def test_members_are_numbered_without_moving_the_numbers_already_held(migrated_db):
    # reg:1 and mem:2 keep 1 and 2; the two unnumbered members — the removed one
    # among them, since a removed member keeps its number — take the next free
    assert _numbers(migrated_db, 1) == [("reg:1", 1), ("mem:2", 2), ("mem:1", 3), ("mem:3", 4)]


def test_each_tournament_numbers_from_its_own_lowest_free_number(migrated_db):
    assert _numbers(migrated_db, 2) == [("mem:4", 1)]


def test_downgrade_releases_the_member_numbers_alone(migrated_db):
    _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    assert _numbers(migrated_db, 1) == [("reg:1", 1)]
    assert _numbers(migrated_db, 2) == []
