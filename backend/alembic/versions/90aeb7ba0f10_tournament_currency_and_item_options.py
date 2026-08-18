"""tournament currency, registration instructions, and extra-item options

Revision ID: 90aeb7ba0f10
Revises: 480088fdaa2a
Create Date: 2026-07-30 00:00:00.000000

Every default reproduces pre-change behavior exactly: existing tournaments are
CZK with EUR payments off, existing items declare no option, and existing
selections carry no option value.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '90aeb7ba0f10'
down_revision: str | Sequence[str] | None = '480088fdaa2a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'primary_currency',
                sa.Enum('CZK', 'EUR', name='currency', native_enum=False, length=30),
                nullable=False,
                server_default='CZK',
            )
        )
        batch_op.add_column(
            sa.Column(
                'eur_payments_enabled',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column('eur_rate', sa.Numeric(12, 4), nullable=True))
        batch_op.add_column(
            sa.Column('registration_instructions', sa.Text(), nullable=True)
        )

    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('option_label', sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column('option_choices', sa.JSON(), nullable=False, server_default='[]')
        )

    with op.batch_alter_table('registration_extras', schema=None) as batch_op:
        batch_op.add_column(sa.Column('option_value', sa.String(length=100), nullable=True))

    # defaults existed only to backfill; the ORM supplies them from here on
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column('primary_currency', server_default=None)
        batch_op.alter_column('eur_payments_enabled', server_default=None)
    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.alter_column('option_choices', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('registration_extras', schema=None) as batch_op:
        batch_op.drop_column('option_value')

    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.drop_column('option_choices')
        batch_op.drop_column('option_label')

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_column('registration_instructions')
        batch_op.drop_column('eur_rate')
        batch_op.drop_column('eur_payments_enabled')
        batch_op.drop_column('primary_currency')
