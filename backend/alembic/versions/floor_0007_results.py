"""the tournament day's results: which disciplines' standings are public

Revision ID: floor_0007
Revises: floor_0006

The publish gate's record per discipline; the standing itself is computed
(design add-floor-results D4). Floor tables only: the office's own drift
that autogenerate reports is left alone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0007"
down_revision: str | Sequence[str] | None = "floor_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_published_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f("fk_floor_published_results_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_published_results_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_published_results")),
        sa.UniqueConstraint(
            "tournament_id", "discipline_id", name=op.f("uq_floor_published_results_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_published_results", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_published_results_tournament_id"), ["tournament_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("floor_published_results", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_published_results_tournament_id"))

    op.drop_table("floor_published_results")
