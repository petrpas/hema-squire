"""payments an organizer records by hand, and the settled-by-hand mark

Revision ID: b3d90a1f5c47
Revises: a7e6c1b40d92
Create Date: 2026-09-06 00:00:00.000000

Both additions back-fill to nothing, and that is the whole of the data story.
No registration has been settled by hand under a stored mark, because until now
there was none: the marks made on payments-off tournaments wrote state and an
audit event and nothing else. They keep working unchanged — they are PAID with
empty counters, which is what they were — and simply carry no timestamp. The
console reads the column where it exists and the state where it does not.

`registrations.amount_paid_cents` is untouched here and changes meaning anyway:
from money Squire saw in a statement to money credited, by a statement or by a
person who said so. Nothing to migrate, everything to know
(design add-manual-payment-entry D1).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b3d90a1f5c47'
down_revision: str | Sequence[str] | None = 'a7e6c1b40d92'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'manual_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column(
            'currency',
            sa.Enum('CZK', 'EUR', name='currency', native_enum=False, length=30),
            nullable=False,
        ),
        sa.Column('received_on', sa.Date(), nullable=False),
        sa.Column(
            'method',
            sa.Enum(
                'cash', 'transfer', 'card', 'other',
                name='paymentmethod', native_enum=False, length=30,
            ),
            nullable=False,
        ),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(length=200), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.id']),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('settled_by_hand_at', sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column('settled_by_hand_reason', sa.String(length=200), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_column('settled_by_hand_reason')
        batch_op.drop_column('settled_by_hand_at')

    op.drop_table('manual_payments')
