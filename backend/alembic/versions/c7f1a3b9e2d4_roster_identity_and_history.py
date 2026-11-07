"""roster member identity and the roster change log

Revision ID: c7f1a3b9e2d4
Revises: b3d5f7a9c1e2
Create Date: 2026-11-07 00:00:00.000000

A roster member's identity is its primary key, which it always had — what it
lacked was a save that kept it. Nothing is backfilled: every existing member is
live (`removed_at` NULL) and keeps the id it has.

The log starts empty. The history begins when it is first kept, which the
organizer's view says rather than implying the rosters were never touched
(design roster-identity-and-history, Migration Plan).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7f1a3b9e2d4"
down_revision: str | Sequence[str] | None = "b3d5f7a9c1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("team_members", schema=None) as batch_op:
        batch_op.add_column(sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("removed_by_fencer_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_team_members_removed_by_fencer_id",
            "fencers",
            ["removed_by_fencer_id"],
            ["id"],
        )

    op.create_table(
        "roster_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("member_name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("field", sa.String(length=50), nullable=True),
        sa.Column("before", sa.Text(), nullable=True),
        sa.Column("after", sa.Text(), nullable=True),
        sa.Column("actor_fencer_id", sa.Integer(), nullable=False),
        sa.Column("by_organizer", sa.Boolean(), nullable=False),
        sa.Column("after_deadline", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["team_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_fencer_id"], ["fencers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roster_changes_team_id", "roster_changes", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_roster_changes_team_id", table_name="roster_changes")
    op.drop_table("roster_changes")
    with op.batch_alter_table("team_members", schema=None) as batch_op:
        batch_op.drop_constraint("fk_team_members_removed_by_fencer_id", type_="foreignkey")
        batch_op.drop_column("removed_by_fencer_id")
        batch_op.drop_column("removed_at")
