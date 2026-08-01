"""dual currency prices: local_currency rename, EUR prices and totals

Revision ID: 3ebc04d896eb
Revises: df6a74c06dfa
Create Date: 2026-08-01 10:49:13.438206

Renames Tournament.primary_currency to local_currency (mechanical; "primary"
implied a value derived from it, which is exactly the model this change
removes) and adds five nullable columns: Discipline.fee_eur/fee_early_eur,
ExtraItem.price_eur, Registration.total_eur, and Registration
.amount_paid_eur_cents (not null, default 0).

Data step, for tournaments with eur_payments_enabled and a positive eur_rate
only: derives an initial EUR price for every filled local price, every
registration's total_eur, and every fixed discount's value_eur, each as the
local amount divided by the rate, rounded half-up to a whole unit — the same
rounding pricing.py already uses everywhere else. Every other tournament gets
NULLs throughout and is untouched.

These derived figures are a one-time approximation of what pricing.to_eur
would have shown for that amount at that rate before this change; from this
migration onward they are authoritative, organizer-editable prices like any
other, not a live conversion. A fencer currently quoted 68.63 EUR may see a
derived 69 EUR — bounded by half a unit per item (design "Risks / Trade-offs:
Backfilled EUR prices shift quoted figures slightly").

Downgrade drops the added columns and reverses the rename. Any EUR price or
total typed by an organizer after this deploys is lost on downgrade, so
downgrade is safe only immediately after deploying — never once organizers
have started pricing in EUR.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision: str = '3ebc04d896eb'
down_revision: Union[str, Sequence[str], None] = 'df6a74c06dfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CURRENCY_TYPE = sa.Enum('CZK', 'EUR', name='currency', native_enum=False, length=30)


def _derive(amount: int | None, rate: Decimal) -> int | None:
    if amount is None:
        return None
    return int((Decimal(amount) / rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def upgrade() -> None:
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column(
            'primary_currency',
            new_column_name='local_currency',
            existing_type=_CURRENCY_TYPE,
        )

    with op.batch_alter_table('disciplines', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fee_eur', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('fee_early_eur', sa.Integer(), nullable=True))

    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('price_eur', sa.Integer(), nullable=True))

    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_eur', sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'amount_paid_eur_cents', sa.Integer(), nullable=False, server_default='0'
            )
        )

    conn = op.get_bind()
    tournaments = table(
        'tournaments',
        column('id', sa.Integer),
        column('eur_payments_enabled', sa.Boolean),
        column('eur_rate', sa.Numeric(12, 4)),
        column('discounts', sa.JSON),
    )
    disciplines = table(
        'disciplines',
        column('id', sa.Integer),
        column('tournament_id', sa.Integer),
        column('fee', sa.Integer),
        column('fee_early', sa.Integer),
        column('fee_eur', sa.Integer),
        column('fee_early_eur', sa.Integer),
    )
    extra_items = table(
        'extra_items',
        column('id', sa.Integer),
        column('tournament_id', sa.Integer),
        column('price', sa.Integer),
        column('price_eur', sa.Integer),
    )
    registrations = table(
        'registrations',
        column('id', sa.Integer),
        column('tournament_id', sa.Integer),
        column('total_amount', sa.Integer),
        column('total_eur', sa.Integer),
    )

    eur_tournaments = conn.execute(
        sa.select(tournaments.c.id, tournaments.c.eur_rate, tournaments.c.discounts).where(
            tournaments.c.eur_payments_enabled.is_(True),
            tournaments.c.eur_rate.isnot(None),
        )
    ).fetchall()

    for row in eur_tournaments:
        rate = Decimal(str(row.eur_rate))
        if rate <= 0:
            continue

        for d in conn.execute(
            sa.select(disciplines.c.id, disciplines.c.fee, disciplines.c.fee_early).where(
                disciplines.c.tournament_id == row.id
            )
        ).fetchall():
            conn.execute(
                disciplines.update()
                .where(disciplines.c.id == d.id)
                .values(fee_eur=_derive(d.fee, rate), fee_early_eur=_derive(d.fee_early, rate))
            )

        for item in conn.execute(
            sa.select(extra_items.c.id, extra_items.c.price).where(
                extra_items.c.tournament_id == row.id
            )
        ).fetchall():
            conn.execute(
                extra_items.update()
                .where(extra_items.c.id == item.id)
                .values(price_eur=_derive(item.price, rate))
            )

        for reg in conn.execute(
            sa.select(registrations.c.id, registrations.c.total_amount).where(
                registrations.c.tournament_id == row.id
            )
        ).fetchall():
            conn.execute(
                registrations.update()
                .where(registrations.c.id == reg.id)
                .values(total_eur=_derive(reg.total_amount, rate))
            )

        discounts = row.discounts or []
        changed = False
        for discount in discounts:
            effect = discount.get('effect') or {}
            if effect.get('kind') == 'fixed' and 'value_eur' not in effect:
                effect['value_eur'] = _derive(effect.get('value', 0), rate)
                changed = True
        if changed:
            conn.execute(
                tournaments.update().where(tournaments.c.id == row.id).values(discounts=discounts)
            )

    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.alter_column('amount_paid_eur_cents', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_column('amount_paid_eur_cents')
        batch_op.drop_column('total_eur')

    with op.batch_alter_table('extra_items', schema=None) as batch_op:
        batch_op.drop_column('price_eur')

    with op.batch_alter_table('disciplines', schema=None) as batch_op:
        batch_op.drop_column('fee_early_eur')
        batch_op.drop_column('fee_eur')

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column(
            'local_currency',
            new_column_name='primary_currency',
            existing_type=_CURRENCY_TYPE,
        )
