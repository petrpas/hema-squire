"""eur rate two decimal places

Revision ID: 15abc1d789f4
Revises: 3ebc04d896eb
Create Date: 2026-08-01 12:19:52.803984

`eur_rate` is a Setup convenience the organizer types back, not a computed
figure — two decimal places is what they actually enter (25.50 Kč per EUR),
not four. Rounds any already-stored rate to two decimal places, half-up, then
narrows the column. Nothing else reads this column (design
add-dual-currency-prices Decision 3), so no price, total, or payment
instruction is affected.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision: str = '15abc1d789f4'
down_revision: Union[str, Sequence[str], None] = '3ebc04d896eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    tournaments = table(
        'tournaments', column('id', sa.Integer), column('eur_rate', sa.Numeric(12, 4))
    )
    rows = conn.execute(
        sa.select(tournaments.c.id, tournaments.c.eur_rate).where(
            tournaments.c.eur_rate.isnot(None)
        )
    ).fetchall()
    for row in rows:
        rounded = Decimal(str(row.eur_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        conn.execute(
            tournaments.update().where(tournaments.c.id == row.id).values(eur_rate=rounded)
        )

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column(
            'eur_rate', existing_type=sa.Numeric(12, 4), type_=sa.Numeric(12, 2)
        )


def downgrade() -> None:
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column(
            'eur_rate', existing_type=sa.Numeric(12, 2), type_=sa.Numeric(12, 4)
        )
