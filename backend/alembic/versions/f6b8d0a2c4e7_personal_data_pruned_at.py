"""personal data pruned at

Revision ID: f6b8d0a2c4e7
Revises: c4e6a8b0d2f3
Create Date: 2026-11-10 18:00:00.000000

Adds `tournaments.personal_data_pruned_at` (change data-retention). Nothing is
backfilled: no tournament has been pruned yet, and the pass finds the old ones
itself.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6b8d0a2c4e7"
down_revision: str | Sequence[str] | None = "c4e6a8b0d2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(
            sa.Column("personal_data_pruned_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_column("personal_data_pruned_at")
