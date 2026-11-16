"""a ratings snapshot remembers whom it asked

Revision ID: c4d8e2a6f1b3
Revises: e7a1c3f5b9d2
Create Date: 2026-11-16 19:00:00.000000

Adds `hr_rating_snapshots.hr_ids`, the HEMA Ratings identifiers a snapshot
fetched pages for, so a fighter asked and unrated in a category can be told
from one never asked (design team-export-layouts D8). Nullable and not
backfilled: an older snapshot did not record it, and reads as unknown.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8e2a6f1b3"
down_revision: str | Sequence[str] | None = "e7a1c3f5b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("hr_rating_snapshots") as batch:
        batch.add_column(sa.Column("hr_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("hr_rating_snapshots") as batch:
        batch.drop_column("hr_ids")
