"""Team disciplines: discipline kind and roster bounds, tournament composition
deadline, and the teams/team_members tables.

Every existing discipline becomes individual (kind defaults to
'individual'); team_min, team_max, and team_composition_deadline default to
null. Nothing is backfilled and no existing tournament's pricing,
availability, or output changes (design team-disciplines Migration Plan).

Revision ID: a3f7c9d21e08
Revises: 2eb5a0fb8898
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op

revision = "a3f7c9d21e08"
down_revision = "2eb5a0fb8898"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("disciplines") as batch:
        batch.add_column(
            sa.Column(
                "kind",
                sa.Enum("individual", "team", name="disciplinekind", native_enum=False, length=30),
                nullable=False,
                server_default="individual",
            )
        )
        batch.add_column(sa.Column("team_min", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("team_max", sa.Integer(), nullable=True))
    with op.batch_alter_table("disciplines") as batch:
        batch.alter_column("kind", server_default=None)

    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(sa.Column("team_composition_deadline", sa.Date(), nullable=True))

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("discipline_id", sa.Integer(), sa.ForeignKey("disciplines.id"), nullable=False),
        sa.Column("registration_id", sa.Integer(), sa.ForeignKey("registrations.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("waitlisted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("composition_reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    with op.batch_alter_table("teams") as batch:
        batch.alter_column("waitlisted", server_default=None)

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("hr_id", sa.Integer(), nullable=True),
        sa.Column("club", sa.String(length=200), nullable=True),
        sa.Column("nationality", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_team_members_hr_id", "team_members", ["hr_id"])


def downgrade() -> None:
    op.drop_index("ix_team_members_hr_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_table("teams")

    with op.batch_alter_table("tournaments") as batch:
        batch.drop_column("team_composition_deadline")

    with op.batch_alter_table("disciplines") as batch:
        batch.drop_column("team_max")
        batch.drop_column("team_min")
        batch.drop_column("kind")
