"""an extra item's capacity

Revision ID: a2c4e6f8b0d1
Revises: f1a3c5e7b9d2
Create Date: 2026-11-01 18:00:00.000000

Adds `extra_items.capacity` (change add-item-capacity). No backfill: every
existing item stays unlimited.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c4e6f8b0d1"
down_revision: str | Sequence[str] | None = "f1a3c5e7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("extra_items") as batch:
        batch.add_column(sa.Column("capacity", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("extra_items") as batch:
        batch.drop_column("capacity")
