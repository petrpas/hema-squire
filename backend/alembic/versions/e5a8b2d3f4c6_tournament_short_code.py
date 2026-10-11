"""a tournament may carry a short code for its card's plate

Revision ID: e5a8b2d3f4c6
Revises: d4f7a9c1e2b3
Create Date: 2026-10-11 00:00:00.000000

Adds `tournaments.short_code` (spec tournament-admin, Tournament short code):
one to three characters an organizer sets where the monogram derived from
the name will not do. Null for every existing tournament, which keeps
deriving it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a8b2d3f4c6"
down_revision: str | Sequence[str] | None = "d4f7a9c1e2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("short_code", sa.String(length=3), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("short_code")
