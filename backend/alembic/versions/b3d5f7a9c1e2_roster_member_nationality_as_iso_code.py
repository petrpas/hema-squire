"""a roster member's nationality as its ISO country code

Revision ID: b3d5f7a9c1e2
Revises: a2c4e6f8b0d1
Create Date: 2026-11-07 19:00:00.000000

Converts `team_members.nationality` to the two-letter ISO code of the country it
names (change roster-nationality-in-one-vocabulary). Members bound through the
HEMA Ratings search were stored with the fighters index's own English country
name, in a column that reads as codes everywhere else in the application.

A spelling no country can be read from is left as it stands, exactly as the
application's own reading leaves it: a spelling we cannot read is still what we
were given.

The reading is spelled out here rather than imported from `app.hr_index`: a
migration is replayed from the baseline against whatever the application looks
like then, and no revision in this directory depends on application code. The
alias list mirrors `hr_index._COUNTRY_ALIASES`; it exists in two places because
the alternative is a migration that stops working when a module moves.
"""

from collections.abc import Sequence

import pycountry
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d5f7a9c1e2"
down_revision: str | Sequence[str] | None = "a2c4e6f8b0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALIASES = {
    "russia": "RU",
    "turkey": "TR",
    "palestine": "PS",
    "uk": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
}


def _code(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return pycountry.countries.lookup(stripped).alpha_2
    except LookupError:
        return _ALIASES.get(stripped.casefold())


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, nationality FROM team_members WHERE nationality IS NOT NULL")
    ).all()
    for member_id, nationality in rows:
        code = _code(nationality)
        if code is not None and code != nationality:
            connection.execute(
                sa.text("UPDATE team_members SET nationality = :code WHERE id = :id"),
                {"code": code, "id": member_id},
            )


def downgrade() -> None:
    """Nothing to undo. A code is a valid nationality for every reader before
    this revision and after it, and the spelling it replaced is not recoverable
    — several of them map to one code."""
