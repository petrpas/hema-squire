"""the tournament day's setup: days, pistes, formats, officials, parameters

Revision ID: floor_0001
Revises: c4d8e2a6f1b3
Create Date: 2026-11-16 23:00:00.000000

The floor's first tables (design add-floor-console D3). They refer to the office
by string foreign keys only. A format goes with its discipline (ON DELETE
CASCADE), so the office's discipline delete needs no knowledge of the floor.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0001"
down_revision: str | Sequence[str] | None = "c4d8e2a6f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_days",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start", sa.Time(), nullable=False),
        sa.Column("end", sa.Time(), nullable=False),
        sa.Column("breaks", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], name="fk_floor_days_tournament_id_tournaments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_floor_days"),
        sa.UniqueConstraint("tournament_id", "date", name="uq_floor_days_tournament_id"),
    )
    op.create_index("ix_floor_days_tournament_id", "floor_days", ["tournament_id"])

    op.create_table(
        "floor_pistes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("reserve", sa.Boolean(), nullable=False),
        sa.Column("tag", sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], name="fk_floor_pistes_tournament_id_tournaments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_floor_pistes"),
        sa.UniqueConstraint("tournament_id", "name", name="uq_floor_pistes_tournament_id"),
    )
    op.create_index("ix_floor_pistes_tournament_id", "floor_pistes", ["tournament_id"])

    op.create_table(
        "floor_piste_days",
        sa.Column("piste_id", sa.Integer(), nullable=False),
        sa.Column("day_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["piste_id"], ["floor_pistes.id"], name="fk_floor_piste_days_piste_id_floor_pistes"
        ),
        sa.ForeignKeyConstraint(
            ["day_id"], ["floor_days.id"], name="fk_floor_piste_days_day_id_floor_days"
        ),
        sa.PrimaryKeyConstraint("piste_id", "day_id", name="pk_floor_piste_days"),
    )

    op.create_table(
        "floor_formats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("pool_min", sa.Integer(), nullable=False),
        sa.Column("pool_max", sa.Integer(), nullable=False),
        sa.Column("advance", sa.Integer(), nullable=True),
        sa.Column("third_place", sa.Boolean(), nullable=False),
        sa.Column("staffing", sa.JSON(), nullable=True),
        sa.Column("slot_pool_bout", sa.Integer(), nullable=False),
        sa.Column("slot_elim_bout", sa.Integer(), nullable=False),
        sa.Column("slot_pool_overhead", sa.Integer(), nullable=False),
        sa.Column("slot_team_match", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], name="fk_floor_formats_tournament_id_tournaments"
        ),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name="fk_floor_formats_discipline_id_disciplines",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_floor_formats"),
        sa.UniqueConstraint("discipline_id", name="uq_floor_formats_discipline_id"),
    )
    op.create_index("ix_floor_formats_tournament_id", "floor_formats", ["tournament_id"])

    op.create_table(
        "floor_officials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("person_key", sa.String(80), nullable=True),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.Column("discipline_ids", sa.JSON(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name="fk_floor_officials_tournament_id_tournaments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_floor_officials"),
    )
    op.create_index("ix_floor_officials_tournament_id", "floor_officials", ["tournament_id"])

    op.create_table(
        "floor_official_days",
        sa.Column("official_id", sa.Integer(), nullable=False),
        sa.Column("day_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["official_id"],
            ["floor_officials.id"],
            name="fk_floor_official_days_official_id_floor_officials",
        ),
        sa.ForeignKeyConstraint(
            ["day_id"], ["floor_days.id"], name="fk_floor_official_days_day_id_floor_days"
        ),
        sa.PrimaryKeyConstraint("official_id", "day_id", name="pk_floor_official_days"),
    )

    op.create_table(
        "floor_settings",
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name="fk_floor_settings_tournament_id_tournaments",
        ),
        sa.PrimaryKeyConstraint("tournament_id", name="pk_floor_settings"),
    )


def downgrade() -> None:
    op.drop_table("floor_settings")
    op.drop_table("floor_official_days")
    op.drop_index("ix_floor_officials_tournament_id", table_name="floor_officials")
    op.drop_table("floor_officials")
    op.drop_index("ix_floor_formats_tournament_id", table_name="floor_formats")
    op.drop_table("floor_formats")
    op.drop_table("floor_piste_days")
    op.drop_index("ix_floor_pistes_tournament_id", table_name="floor_pistes")
    op.drop_table("floor_pistes")
    op.drop_index("ix_floor_days_tournament_id", table_name="floor_days")
    op.drop_table("floor_days")
