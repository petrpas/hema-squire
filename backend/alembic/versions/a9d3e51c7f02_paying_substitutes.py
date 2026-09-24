"""paying substitutes may take free places: the setting and the stored claim

Revision ID: a9d3e51c7f02
Revises: f7b2d94e6c18
Create Date: 2026-09-25 00:00:00.000000

Adds `tournaments.queue_payment_seats`, not null and false for every existing
tournament (off by default, spec tournament-admin), and the two nullable claim
columns on `registrations`. No backfill: a claim is computed when totals are,
and on reading instructions where the setting is on and none is stored yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9d3e51c7f02"
down_revision: str | Sequence[str] | None = "f7b2d94e6c18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "queue_payment_seats", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
    with op.batch_alter_table("registrations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("claim_total", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("claim_total_eur", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("registrations", schema=None) as batch_op:
        batch_op.drop_column("claim_total_eur")
        batch_op.drop_column("claim_total")
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("queue_payment_seats")
