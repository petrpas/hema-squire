"""account deletion

Revision ID: c4e6a8b0d2f3
Revises: e5a7c9b1d3f4
Create Date: 2026-11-03 21:00:00.000000

Adds `fencers.deletion_requested_at`, `fencers.deleted_at` and the
`account_erasures` log (change account-deletion). Nothing is backfilled: no
account has asked to be deleted yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e6a8b0d2f3"
down_revision: str | Sequence[str] | None = "e5a7c9b1d3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("fencers") as batch:
        batch.add_column(
            sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "account_erasures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fencer_id", sa.Integer(), sa.ForeignKey("fencers.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_erasures_fencer_id", "account_erasures", ["fencer_id"])


def downgrade() -> None:
    op.drop_index("ix_account_erasures_fencer_id", table_name="account_erasures")
    op.drop_table("account_erasures")
    with op.batch_alter_table("fencers") as batch:
        batch.drop_column("deleted_at")
        batch.drop_column("deletion_requested_at")
