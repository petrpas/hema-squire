"""drop fencers hr_id unique constraint

Revision ID: f2be659b34da
Revises: f6495f6a87e8
Create Date: 2026-07-19 22:10:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2be659b34da'
down_revision: str | Sequence[str] | None = 'f6495f6a87e8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def upgrade() -> None:
    """Drop the unique constraint on fencers.hr_id (non-exclusive HR claims).

    The constraint is unnamed (sa.UniqueConstraint('hr_id') in the original
    create_table), and SQLite never stores a name for it, so a plain
    drop_constraint needs a name to target. Passing naming_convention makes
    batch mode apply the app's convention to the reflected anonymous
    constraint, producing the same 'uq_fencers_hr_id' name drop_constraint
    can then reference.
    """
    with op.batch_alter_table(
        'fencers', schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint('uq_fencers_hr_id', type_='unique')
        batch_op.create_index(
            batch_op.f('ix_fencers_hr_id'), ['hr_id'], unique=False
        )


def downgrade() -> None:
    """Restore the unique constraint on fencers.hr_id.

    Only safe while no duplicate claims exist; if real duplicates were
    created under non-exclusivity, admin unbinding must resolve them first.
    """
    with op.batch_alter_table('fencers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fencers_hr_id'))
        batch_op.create_unique_constraint('uq_fencers_hr_id', ['hr_id'])
