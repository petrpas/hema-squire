"""floor pistes lose their tag: nothing read it (owner decision 2026-11-17)

Revision ID: floor_0009
Revises: floor_0008

A separate revision rather than an edit of floor_0008, which development
databases already carry. The downgrade restores the column empty.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0009"
down_revision: str | Sequence[str] | None = "floor_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("floor_pistes") as batch:
        batch.drop_column("tag")


def downgrade() -> None:
    with op.batch_alter_table("floor_pistes") as batch:
        batch.add_column(sa.Column("tag", sa.String(length=80), nullable=True))
