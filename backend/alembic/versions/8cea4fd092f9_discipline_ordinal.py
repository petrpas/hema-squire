"""discipline ordinal

Revision ID: 8cea4fd092f9
Revises: a1c94f7e2d10
Create Date: 2026-08-11 00:00:00.000000

Adds `ordinal` to `disciplines`, so the Setup table's disciplines can be
manually reordered (up arrow) instead of always sitting in id order. Existing
rows are backfilled in their current `id` order per tournament, so every
tournament's displayed order is unchanged until an organizer reorders it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8cea4fd092f9"
down_revision: str | Sequence[str] | None = "a1c94f7e2d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("disciplines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0")
        )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, tournament_id FROM disciplines ORDER BY tournament_id, id")
    ).fetchall()
    counters: dict[int, int] = {}
    for discipline_id, tournament_id in rows:
        ordinal = counters.get(tournament_id, 0)
        conn.execute(
            sa.text("UPDATE disciplines SET ordinal = :ordinal WHERE id = :id"),
            {"ordinal": ordinal, "id": discipline_id},
        )
        counters[tournament_id] = ordinal + 1

    # the default existed only to backfill; the ORM supplies it from here on
    with op.batch_alter_table("disciplines", schema=None) as batch_op:
        batch_op.alter_column("ordinal", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("disciplines", schema=None) as batch_op:
        batch_op.drop_column("ordinal")
