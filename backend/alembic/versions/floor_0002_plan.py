"""the tournament day's plan: versions, activities, pins

Revision ID: floor_0002
Revises: floor_0001
Create Date: 2026-11-16 23:59:10.739229

Plan versions with their activities, and the pins the planner does not move
(design add-floor-planner D6). One working and one published version per
tournament, held by partial unique indexes. Floor tables only: the office's
own drift that autogenerate reports is not this migration's to touch.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0002"
down_revision: str | Sequence[str] | None = "floor_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_pins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("target", sa.String(length=80), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("gate", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_pins_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_pins")),
    )
    with op.batch_alter_table("floor_pins", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_pins_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("variant", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("exclusions", sa.JSON(), nullable=False),
        sa.Column("collisions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_plans_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_plans")),
        sa.UniqueConstraint("tournament_id", "version", name=op.f("uq_floor_plans_tournament_id")),
    )
    with op.batch_alter_table("floor_plans", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_plans_tournament_id"), ["tournament_id"], unique=False
        )
        batch_op.create_index(
            "uq_floor_plans_published",
            ["tournament_id"],
            unique=True,
            sqlite_where=sa.text("status = 'published'"),
        )
        batch_op.create_index(
            "uq_floor_plans_working",
            ["tournament_id"],
            unique=True,
            sqlite_where=sa.text("status = 'working'"),
        )

    op.create_table(
        "floor_plan_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.String(length=80), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("piste_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("final", sa.Boolean(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["floor_plans.id"],
            name=op.f("fk_floor_plan_activities_plan_id_floor_plans"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_plan_activities")),
    )
    with op.batch_alter_table("floor_plan_activities", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_plan_activities_plan_id"), ["plan_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("floor_plan_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_plan_activities_plan_id"))

    op.drop_table("floor_plan_activities")
    with op.batch_alter_table("floor_plans", schema=None) as batch_op:
        batch_op.drop_index("uq_floor_plans_working", sqlite_where=sa.text("status = 'working'"))
        batch_op.drop_index(
            "uq_floor_plans_published", sqlite_where=sa.text("status = 'published'")
        )
        batch_op.drop_index(batch_op.f("ix_floor_plans_tournament_id"))

    op.drop_table("floor_plans")
    with op.batch_alter_table("floor_pins", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_pins_tournament_id"))

    op.drop_table("floor_pins")
