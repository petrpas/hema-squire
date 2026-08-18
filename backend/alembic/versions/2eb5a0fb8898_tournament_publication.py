"""Tournament publication record.

Adds tournaments.published_at (null = draft) and published_by_id (who
published it). No backfill: every existing tournament becomes a draft,
including any currently live and taking registrations — it must be
published explicitly through its PUBLISH tab after this migration runs
(design D1, Migration Plan of add-explicit-publishing).

Revision ID: 2eb5a0fb8898
Revises: 9c2e4795967b
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op

revision = "2eb5a0fb8898"
down_revision = "9c2e4795967b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("published_by_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_tournaments_published_by_id", "fencers", ["published_by_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_constraint("fk_tournaments_published_by_id", type_="foreignkey")
        batch.drop_column("published_by_id")
        batch.drop_column("published_at")
