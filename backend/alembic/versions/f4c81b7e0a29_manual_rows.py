"""manually entered fencers

Revision ID: f4c81b7e0a29
Revises: d2a71f4b83c6
Create Date: 2026-08-29 00:00:00.000000

`manual_rows` holds the fencers an organizer enters by hand at the console: the
third source population beside in-app registrations and imported rows (spec
etl-console, Manual entry of a fencer). Nothing existing becomes a manual row,
so there is no backfill — the table starts empty and fills as organizers type.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4c81b7e0a29"
down_revision: str | Sequence[str] | None = "d2a71f4b83c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manual_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("club", sa.String(length=200), nullable=True),
        sa.Column("hr_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disciplines", sa.JSON(), nullable=False),
        sa.Column("weapon_rentals", sa.JSON(), nullable=False),
        sa.Column("afterparty", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["fencers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("manual_rows")
