"""User roles, tournament ownership, organizer pleas.

Adds fencers.role (global role ladder), tournaments.owner_id + cancelled_at
(Tournament Owner and cancel lifecycle), and the organizer_requests plea
table. Backfills each tournament's owner from its earliest team row.

Revision ID: e58f2c7d91a4
Revises: a7c41e90d2b5
Create Date: 2026-07-19
"""

import sqlalchemy as sa
from alembic import op

revision = "e58f2c7d91a4"
down_revision = "a7c41e90d2b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fencers") as batch:
        batch.add_column(
            sa.Column("role", sa.String(length=30), nullable=False, server_default="fencer")
        )

    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_tournaments_owner_id", "fencers", ["owner_id"], ["id"])

    op.create_table(
        "organizer_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fencer_id", sa.Integer(), sa.ForeignKey("fencers.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("fencers.id"), nullable=True),
    )

    # existing tournaments: the earliest team member becomes the Tournament
    # Owner; tournaments with no team rows stay NULL until an Admin assigns one
    op.execute(
        sa.text(
            """
            UPDATE tournaments SET owner_id = (
                SELECT fencer_id FROM tournament_organizers
                WHERE tournament_organizers.tournament_id = tournaments.id
                ORDER BY tournament_organizers.id
                LIMIT 1
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("organizer_requests")
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_constraint("fk_tournaments_owner_id", type_="foreignkey")
        batch.drop_column("cancelled_at")
        batch.drop_column("owner_id")
    with op.batch_alter_table("fencers") as batch:
        batch.drop_column("role")
