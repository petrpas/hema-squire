"""an account's address changes only once the new mailbox follows a link

Revision ID: e7a1c3f5b9d2
Revises: b5e9c3d7f2a1
Create Date: 2026-11-16 15:00:00.000000

Adds `pending_email_changes`, one requested address change per account (spec
profile-page, Address change). Nothing existing is touched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a1c3f5b9d2"
down_revision: str | Sequence[str] | None = "b5e9c3d7f2a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pending_email_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "fencer_id", sa.Integer(), sa.ForeignKey("fencers.id"), nullable=False, unique=True
        ),
        sa.Column("new_email", sa.String(length=320), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pending_email_changes")
