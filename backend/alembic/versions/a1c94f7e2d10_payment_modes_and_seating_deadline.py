"""payment modes, seating deadline, flat deposits

Revision ID: a1c94f7e2d10
Revises: c61e07c3fe54
Create Date: 2026-08-04 00:00:00.000000

Adds the five tournament columns the payment modes need:
`payment_mode` (immediate | deposit | reservation), `seating_deadline`,
`deposit_amount` / `deposit_amount_eur`, and `seating_settled_at`.

Every existing tournament gets `payment_mode = 'immediate'`, which is exactly
what it already does — full amount owed at registration, held for the payment
window, expired if unpaid — so the migration is behaviour-preserving and no
data is rewritten (design Decision 9). `reservation_validity_days` is
deliberately left alone: the shipped default is 10 and live tournaments carry
it, while the new 2-7 range is enforced on write only, so clamping stored
values here would change a running tournament's behaviour to satisfy a UI
range.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c94f7e2d10"
down_revision: str | Sequence[str] | None = "c61e07c3fe54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "payment_mode",
                sa.String(length=30),
                nullable=False,
                server_default="immediate",
            )
        )
        batch_op.add_column(sa.Column("seating_deadline", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("deposit_amount", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("deposit_amount_eur", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("seating_settled_at", sa.DateTime(timezone=True), nullable=True)
        )

    # the default existed only to backfill; the ORM supplies it from here on
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.alter_column("payment_mode", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("seating_settled_at")
        batch_op.drop_column("deposit_amount_eur")
        batch_op.drop_column("deposit_amount")
        batch_op.drop_column("seating_deadline")
        batch_op.drop_column("payment_mode")
