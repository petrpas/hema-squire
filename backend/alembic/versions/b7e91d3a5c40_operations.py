"""recorded console operations

Revision ID: b7e91d3a5c40
Revises: f4c81b7e0a29
Create Date: 2026-08-29 00:00:00.000000

`operations` records one run of a long console operation — a parse, a matching,
a deduplication — so the console can report on work that outlives the request
that started it (spec console-operations, An operation is a record, not a
request).

No backfill: there is no history of runs to reconstruct, and no row is the
correct reading for every existing tournament — none of them ever recorded one.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e91d3a5c40"
down_revision: str | Sequence[str] | None = "f4c81b7e0a29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("parse", "match", "dedup", name="operationkind", native_enum=False, length=30),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "done",
                "failed",
                "interrupted",
                name="operationstatus",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("done", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_by", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["started_by"], ["fencers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # the shape of every poll ("what is unconcluded for this tournament") and of
    # the startup sweep's predicate
    op.create_index(
        "ix_operations_tournament_finished", "operations", ["tournament_id", "finished_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_operations_tournament_finished", table_name="operations")
    op.drop_table("operations")
