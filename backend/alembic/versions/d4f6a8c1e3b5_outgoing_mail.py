"""outgoing mail is queued with the action that causes it and delivered after the commit

Revision ID: d4f6a8c1e3b5
Revises: c3e5f7a9b2d4
Create Date: 2026-10-25 20:00:00.000000

Adds `outgoing_mail` (spec outgoing-mail). Nothing is migrated: mail sent
before the deploy was never queued.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f6a8c1e3b5"
down_revision: str | Sequence[str] | None = "c3e5f7a9b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outgoing_mail",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("raw", sa.LargeBinary(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outgoing_mail_pending", "outgoing_mail", ["sent_at", "failed_at"])


def downgrade() -> None:
    op.drop_index("ix_outgoing_mail_pending", table_name="outgoing_mail")
    op.drop_table("outgoing_mail")
