"""tournament subtitle/logo and discipline/extra schedule fields

Revision ID: b4d9c1e07a52
Revises: f2be659b34da
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d9c1e07a52'
down_revision: Union[str, Sequence[str], None] = 'f2be659b34da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional tournament subtitle/logo, discipline schedule + ruleset,
    and extra-item schedule + remark. All columns are nullable and additive;
    existing rows read as NULL and existing totals are unaffected."""
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subtitle', sa.String(length=400), nullable=True))
        batch_op.add_column(sa.Column('logo_bytes', sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column('logo_mime', sa.String(length=100), nullable=True))

    with op.batch_alter_table('disciplines', schema=None) as batch_op:
        batch_op.add_column(sa.Column('schedule_when', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('schedule_where', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('ruleset_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('ruleset_url', sa.String(length=500), nullable=True))

    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('schedule_when', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('schedule_where', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('remark', sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.drop_column('remark')
        batch_op.drop_column('schedule_where')
        batch_op.drop_column('schedule_when')

    with op.batch_alter_table('disciplines', schema=None) as batch_op:
        batch_op.drop_column('ruleset_url')
        batch_op.drop_column('ruleset_name')
        batch_op.drop_column('schedule_where')
        batch_op.drop_column('schedule_when')

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_column('logo_mime')
        batch_op.drop_column('logo_bytes')
        batch_op.drop_column('subtitle')
