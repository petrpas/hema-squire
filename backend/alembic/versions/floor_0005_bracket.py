"""the tournament day's elimination: brackets, their slots, elimination bouts

Revision ID: floor_0005
Revises: floor_0004

The bracket and its slots, and the columns that make a bout an elimination
bout (design add-floor-bracket D2). Floor tables only: the office's own drift
that autogenerate reports is left alone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0005"
down_revision: str | Sequence[str] | None = "floor_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_brackets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("advancing", sa.Integer(), nullable=False),
        sa.Column("third_place", sa.Boolean(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f("fk_floor_brackets_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_brackets_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_brackets")),
        sa.UniqueConstraint(
            "tournament_id", "discipline_id", name=op.f("uq_floor_brackets_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_brackets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_brackets_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_bracket_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bracket_id", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("entrant_key", sa.String(length=80), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("bye", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["bracket_id"],
            ["floor_brackets.id"],
            name=op.f("fk_floor_bracket_slots_bracket_id_floor_brackets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_bracket_slots")),
        sa.UniqueConstraint(
            "bracket_id", "round", "position", name=op.f("uq_floor_bracket_slots_bracket_id")
        ),
    )
    with op.batch_alter_table("floor_bracket_slots", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_bracket_slots_bracket_id"), ["bracket_id"], unique=False
        )

    with op.batch_alter_table("floor_bouts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bracket_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("round", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("position", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("piste_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_floor_bouts_bracket_id"), ["bracket_id"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_floor_bouts_bracket_id_floor_brackets"),
            "floor_brackets",
            ["bracket_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("floor_bouts", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_floor_bouts_bracket_id_floor_brackets"), type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_floor_bouts_bracket_id"))
        batch_op.drop_column("piste_id")
        batch_op.drop_column("position")
        batch_op.drop_column("round")
        batch_op.drop_column("bracket_id")

    with op.batch_alter_table("floor_bracket_slots", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_bracket_slots_bracket_id"))

    op.drop_table("floor_bracket_slots")
    with op.batch_alter_table("floor_brackets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_brackets_tournament_id"))

    op.drop_table("floor_brackets")
