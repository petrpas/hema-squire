"""Rewrite discipline slugs that fail the pattern the discipline slug field
now enforces (design `add-field-validation` D6).

`split-discipline-identity` renamed `disciplines.code` to `slug` in place,
without rewriting values — so a discipline created before that split still
carries its old taxonomy code, and the plastic codes contained a space
(`Plastic SAW`). The new field pattern (`^[A-Za-z0-9-]{1,30}$`) rejects that
space. This migration folds every such slug through the same normalization
`app.taxonomy.normalize_slug` performs (diacritics to ASCII, every run
outside letters/digits/`-` collapsed to a single `-`, stripped, truncated to
30 characters), then disambiguates any resulting collision with the `-2`,
`-3`, ... counter `generate_slug` already uses — a legacy `Plastic SAW` and a
post-split `Plastic-SAW` can coexist in one tournament today, and normalizing
the first onto the second would trip `UNIQUE(tournament_id, slug)`.

The downgrade is a documented no-op (design D6, task 8a.6): once two rows
have been separated by a `-2`/`-3` counter, there is no representation of
"the pre-split form" to restore them to that would not immediately collide
again — restoring a space to a slug a counter was invented to avoid
duplicating would recreate the exact ambiguity this migration removes.

Revision ID: c61e07c3fe54
Revises: 52ba5b743d48
Create Date: 2026-08-02
"""

import re
import unicodedata

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

revision = "c61e07c3fe54"
down_revision = "52ba5b743d48"
branch_labels = None
depends_on = None

SLUG_MAX_LENGTH = 30
SLUG_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,30}$")


def _normalize_slug(value: str) -> str:
    """Inlined copy of app.taxonomy.normalize_slug — migrations must not
    depend on application code that may change shape after this revision is
    written."""
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^A-Za-z0-9-]+", "-", folded)
    trimmed = collapsed.strip("-")
    if len(trimmed) > SLUG_MAX_LENGTH:
        trimmed = trimmed[:SLUG_MAX_LENGTH].rstrip("-")
    return trimmed


def _disambiguate(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    counter = 2
    while f"{base}-{counter}" in taken:
        counter += 1
    return f"{base}-{counter}"


def upgrade() -> None:
    conn = op.get_bind()
    disciplines = table(
        "disciplines",
        column("id", sa.Integer),
        column("tournament_id", sa.Integer),
        column("slug", sa.String),
    )
    rows = conn.execute(
        sa.select(disciplines.c.id, disciplines.c.tournament_id, disciplines.c.slug).order_by(
            disciplines.c.tournament_id, disciplines.c.id
        )
    ).fetchall()

    by_tournament: dict[int, list] = {}
    for row in rows:
        by_tournament.setdefault(row.tournament_id, []).append(row)

    for tournament_rows in by_tournament.values():
        taken = {row.slug for row in tournament_rows}
        for row in tournament_rows:
            if SLUG_PATTERN.match(row.slug):
                continue
            normalized = _normalize_slug(row.slug) or "Discipline"
            new_slug = _disambiguate(normalized, taken - {row.slug})
            taken.discard(row.slug)
            taken.add(new_slug)
            conn.execute(
                disciplines.update().where(disciplines.c.id == row.id).values(slug=new_slug)
            )


def downgrade() -> None:
    # documented no-op — see module docstring
    pass
