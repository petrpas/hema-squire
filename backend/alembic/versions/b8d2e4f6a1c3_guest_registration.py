"""a visitor may register without an account; a signup verifies its address

Revision ID: b8d2e4f6a1c3
Revises: a7c1d2e3f4b5
Create Date: 2026-10-25 12:00:00.000000

Adds `pending_signups`, where a signup waits until the mailed link is followed
(spec fencer-accounts, An account exists only once its address is verified),
and `registrations.manage_key_generation`, which marks a guest registration and
names its current manage key (spec guest-registration). No backfill: every
existing account is verified by construction, and no existing registration is
a guest's.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d2e4f6a1c3"
down_revision: str | Sequence[str] | None = "a7c1d2e3f4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pending_signups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("hr_id", sa.Integer(), nullable=True),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("club", sa.String(length=200), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("return_to", sa.String(length=500), nullable=True),
        sa.Column("key_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("registrations") as batch_op:
        batch_op.add_column(sa.Column("manage_key_generation", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("registrations") as batch_op:
        batch_op.drop_column("manage_key_generation")
    op.drop_table("pending_signups")
