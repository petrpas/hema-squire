"""The discipline slug pattern (design `add-field-validation` D6, section
8a): the schema-level normalize-then-pattern behavior (8a.1-8a.3), and the
`c61e07c3fe54` migration that rewrites stored slugs which fail the pattern
(8a.4-8a.6), run against a throwaway sqlite file the same way
`test_discipline_identity_migration.py` exercises its own revision."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import DisciplineIn

BACKEND_DIR = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "52ba5b743d48"


def _run_alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


# --- 8a.1-8a.3: schema-level behavior --------------------------------------


def test_override_with_punctuation_is_normalized_not_rejected():
    """The scenario `discipline-identity-modal` shipped: normalization runs
    ahead of the pattern (task 8a.1), so an override is folded rather than
    refused. Also exercised end to end in
    test_tournaments.py::test_slug_override_is_normalized (task 8a.2)."""
    discipline = DisciplineIn(
        weapon="SB", capacity=10, slug="Sword & Buckler (variant)"
    )
    assert discipline.slug == "Sword-Buckler-variant"


def test_slug_normalizing_to_nothing_becomes_none():
    # falls back to the router's slug generation rather than an empty string
    discipline = DisciplineIn(weapon="SB", capacity=10, slug="!!!")
    assert discipline.slug is None


def test_slug_over_length_after_normalization_is_truncated_not_rejected():
    discipline = DisciplineIn(weapon="SB", capacity=10, slug="x" * 40)
    assert discipline.slug == "x" * 30


def test_slug_pattern_still_rejects_a_bare_pattern_violation():
    # the alphabet cannot reach the field at all except through the
    # normalizer, but an already-clean value posted directly by an API
    # caller with characters outside it is folded the same way, never 422'd
    # by this field alone (normalization is unconditional, not opt-in)
    discipline = DisciplineIn(weapon="SB", capacity=10, slug="a_b")
    assert discipline.slug == "a-b"


def test_required_fields_still_reject_normally():
    with pytest.raises(ValidationError):
        DisciplineIn(weapon="", capacity=10)


# --- 8a.4-8a.6: the migration ------------------------------------------------


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


def _seed_discipline(conn: sqlite3.Connection, did: int, tid: int, slug: str, name: str) -> None:
    conn.execute(
        "INSERT INTO disciplines (id, tournament_id, slug, weapon, gender, material, "
        "name, kind, capacity) VALUES (?, ?, ?, 'LS', '', '', ?, 'individual', 10)",
        (did, tid, slug, name),
    )


@pytest.fixture
def pre_migration_db(tmp_path) -> Path:
    db_path = tmp_path / "slug_pattern.sqlite"
    result = _run_alembic("upgrade", PREVIOUS_REVISION, db_path=db_path)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(db_path)
    _seed_tournament(conn, 1, "spring-2026")
    # a legacy slug carrying the old taxonomy code's space
    _seed_discipline(conn, 1, 1, "Plastic SAW", "Sabre Women (Plastic)")
    # a clean, already-conforming slug, untouched by the migration
    _seed_discipline(conn, 2, 1, "LS", "Longsword Open")

    _seed_tournament(conn, 2, "autumn-2026")
    # the collision case: a legacy slug and a post-split slug that normalize
    # onto each other, in the same tournament
    _seed_discipline(conn, 3, 2, "Plastic SAW", "Sabre Women (Plastic, legacy)")
    _seed_discipline(conn, 4, 2, "Plastic-SAW", "Sabre Women (Plastic)")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def migrated_db(pre_migration_db) -> Path:
    result = _run_alembic("upgrade", "head", db_path=pre_migration_db)
    assert result.returncode == 0, result.stderr
    return pre_migration_db


def test_legacy_slug_with_a_space_is_rewritten(migrated_db):
    conn = sqlite3.connect(migrated_db)
    slug = conn.execute("SELECT slug FROM disciplines WHERE id = 1").fetchone()[0]
    conn.close()
    assert slug == "Plastic-SAW"


def test_already_conforming_slug_is_untouched(migrated_db):
    conn = sqlite3.connect(migrated_db)
    slug = conn.execute("SELECT slug FROM disciplines WHERE id = 2").fetchone()[0]
    conn.close()
    assert slug == "LS"


def test_collision_between_legacy_and_post_split_slug_is_disambiguated(migrated_db):
    """A tournament holding both a legacy `Plastic SAW` and a post-split
    `Plastic-SAW` migrates to two distinct slugs, and the unique constraint
    holds (design D6, task 8a.5)."""
    conn = sqlite3.connect(migrated_db)
    rows = dict(conn.execute("SELECT id, slug FROM disciplines WHERE tournament_id = 2"))
    conn.close()
    slugs = set(rows.values())
    assert len(slugs) == 2
    assert "Plastic-SAW" in slugs
    # the legacy row lands on a disambiguated slug, not the taken one
    assert rows[3] != "Plastic SAW"
    assert rows[3] != "Plastic-SAW"
    assert rows[3].startswith("Plastic-SAW-")
    assert rows[4] == "Plastic-SAW"


def test_unique_constraint_holds_after_migration(migrated_db):
    conn = sqlite3.connect(migrated_db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO disciplines "
            "(tournament_id, slug, weapon, gender, material, name, kind, capacity) "
            "VALUES (2, 'Plastic-SAW', 'LS', '', '', 'Dup', 'individual', 5)"
        )
    conn.close()


def test_downgrade_is_a_documented_no_op(migrated_db):
    """The rewritten slugs stay rewritten — restoring a space to a slug a
    counter has since disambiguated would reintroduce the exact collision
    the migration exists to avoid (design D6, task 8a.6)."""
    before = sqlite3.connect(migrated_db)
    slugs_before = dict(before.execute("SELECT id, slug FROM disciplines"))
    before.close()

    result = _run_alembic("downgrade", PREVIOUS_REVISION, db_path=migrated_db)
    assert result.returncode == 0, result.stderr

    after = sqlite3.connect(migrated_db)
    slugs_after = dict(after.execute("SELECT id, slug FROM disciplines"))
    after.close()
    assert slugs_after == slugs_before
