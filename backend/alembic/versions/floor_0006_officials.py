"""the tournament day's officials on blocks: assignments

Revision ID: floor_0006
Revises: floor_0005

Each block's staffing seats with their officials, pinned or not (design
add-floor-officials D3). Floor tables only: the office's own drift that
autogenerate reports is left alone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0006"
down_revision: str | Sequence[str] | None = "floor_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("block_key", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("official_id", sa.Integer(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["official_id"],
            ["floor_officials.id"],
            name=op.f("fk_floor_assignments_official_id_floor_officials"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["floor_plans.id"], name=op.f("fk_floor_assignments_plan_id_floor_plans")
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_assignments_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_assignments")),
        sa.UniqueConstraint(
            "tournament_id",
            "block_key",
            "role",
            "slot",
            name=op.f("uq_floor_assignments_tournament_id"),
        ),
    )
    with op.batch_alter_table("floor_assignments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_floor_assignments_plan_id"), ["plan_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_floor_assignments_tournament_id"), ["tournament_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("floor_assignments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_assignments_tournament_id"))
        batch_op.drop_index(batch_op.f("ix_floor_assignments_plan_id"))

    op.drop_table("floor_assignments")
