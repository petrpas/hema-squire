"""reservation lifecycle fixes: expiry grace, amendments, amount_paid_cents

Revision ID: 3f7212c247f3
Revises: 90aeb7ba0f10
Create Date: 2026-07-31 00:00:00.000000

Adds Tournament.expiry_grace_hours (default 48) and Tournament.amendments_close
(nullable, unset means "same window as registration"), plus
Registration.amount_paid_cents (default 0, the one stored money figure —
outstanding is always derived, never stored). Existing PAID registrations are
backfilled to amount_paid_cents = total_amount * 100 so they read as exactly
settled; every other row keeps 0, so no registration acquires a balance it did
not have.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3f7212c247f3'
down_revision: Union[str, Sequence[str], None] = '90aeb7ba0f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'expiry_grace_hours', sa.Integer(), nullable=False, server_default='48'
            )
        )
        batch_op.add_column(sa.Column('amendments_close', sa.Date(), nullable=True))

    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('amount_paid_cents', sa.Integer(), nullable=False, server_default='0')
        )

    op.execute(
        "UPDATE registrations SET amount_paid_cents = total_amount * 100 "
        "WHERE state = 'paid'"
    )

    # defaults existed only to backfill; the ORM supplies them from here on
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column('expiry_grace_hours', server_default=None)
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.alter_column('amount_paid_cents', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_column('amount_paid_cents')

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_column('amendments_close')
        batch_op.drop_column('expiry_grace_hours')
