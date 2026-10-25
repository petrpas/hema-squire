"""a forgotten password is reset through a mailed link; a change ends other sessions

Revision ID: c3e5f7a9b2d4
Revises: b8d2e4f6a1c3
Create Date: 2026-10-25 18:00:00.000000

Adds `password_resets`, one pending reset link per account (spec
password-reset), and `fencers.sessions_valid_from`, the watermark before which
an account's session tokens are refused. No backfill: an empty watermark
refuses nothing, so deploying signs nobody out.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e5f7a9b2d4"
down_revision: str | Sequence[str] | None = "b8d2e4f6a1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "fencer_id", sa.Integer(), sa.ForeignKey("fencers.id"), nullable=False, unique=True
        ),
        sa.Column("key_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("fencers") as batch_op:
        batch_op.add_column(
            sa.Column("sessions_valid_from", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("fencers") as batch_op:
        batch_op.drop_column("sessions_valid_from")
    op.drop_table("password_resets")
