"""widened transaction capture: extra Fio text fields, last_evaluated_at

Revision ID: 9c2e4795967b
Revises: 15abc1d789f4
Create Date: 2026-08-01 13:00:00.000000

Adds four nullable text columns to `bank_transactions` — user_identification,
comment, specification, specific_symbol — carrying the additional Fio fields
that may hold a SEPA reference (design harden-payment-matching Decision 4),
plus a nullable `last_evaluated_at` timestamp (Decision 2). Purely additive:
every historical row keeps NULL throughout, which the widened VS scan and the
re-evaluation pass both treat as absent, so no historical transaction changes
status as a result of this migration.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c2e4795967b'
down_revision: str | Sequence[str] | None = '15abc1d789f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('bank_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_identification', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('comment', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('specification', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('specific_symbol', sa.String(50), nullable=True))
        batch_op.add_column(
            sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('bank_transactions', schema=None) as batch_op:
        batch_op.drop_column('last_evaluated_at')
        batch_op.drop_column('specific_symbol')
        batch_op.drop_column('specification')
        batch_op.drop_column('comment')
        batch_op.drop_column('user_identification')
