"""variable symbol series

Revision ID: df6a74c06dfa
Revises: 3f7212c247f3
Create Date: 2026-07-31 00:00:00.000000

Adds Tournament.vs_year, vs_series, and vs_next_seq — the YY/NN prefix each
tournament's variable symbols carry (design Decision 1) and the per-tournament
sequence counter (design Decision 3). Backfill assigns every existing
tournament a series from its date's year, walked in (date, id) order, the
lowest free value in that year; vs_next_seq starts at 1 regardless of existing
registrations, because legacy VS come from a different range and consume no
structured sequence. No Registration row is read or written.
"""
from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision: str = 'df6a74c06dfa'
down_revision: str | Sequence[str] | None = '3f7212c247f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vs_year', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('vs_series', sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column('vs_next_seq', sa.Integer(), nullable=False, server_default='1')
        )

    conn = op.get_bind()
    tournaments = table(
        'tournaments',
        column('id', sa.Integer),
        column('date', sa.Date),
        column('vs_year', sa.Integer),
        column('vs_series', sa.Integer),
    )
    rows = conn.execute(
        sa.select(tournaments.c.id, tournaments.c.date).order_by(
            tournaments.c.date, tournaments.c.id
        )
    ).fetchall()

    taken_by_year: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        year = row.date.year
        taken = taken_by_year[year]
        series = 1
        while series in taken:
            series += 1
        if series > 99:
            raise RuntimeError(
                f"vs series backfill: year {year} would need a hundredth series"
            )
        taken.add(series)
        conn.execute(
            tournaments.update()
            .where(tournaments.c.id == row.id)
            .values(vs_year=year, vs_series=series)
        )

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.alter_column('vs_year', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('vs_series', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('vs_next_seq', server_default=None)
        batch_op.create_unique_constraint(
            'uq_tournaments_vs_year_vs_series', ['vs_year', 'vs_series']
        )


def downgrade() -> None:
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_constraint('uq_tournaments_vs_year_vs_series', type_='unique')
        batch_op.drop_column('vs_next_seq')
        batch_op.drop_column('vs_series')
        batch_op.drop_column('vs_year')
