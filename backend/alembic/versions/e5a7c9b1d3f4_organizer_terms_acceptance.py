"""organizer terms acceptance

Revision ID: e5a7c9b1d3f4
Revises: d4a7c2e8b015
Create Date: 2026-11-03 20:00:00.000000

Adds `fencers.organizer_terms_version` and `fencers.organizer_terms_accepted_at`
(change privacy-baseline). No backfill: every existing owner is asked once.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a7c9b1d3f4"
down_revision: str | Sequence[str] | None = "d4a7c2e8b015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("fencers") as batch:
        batch.add_column(sa.Column("organizer_terms_version", sa.String(20), nullable=True))
        batch.add_column(
            sa.Column("organizer_terms_accepted_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("fencers") as batch:
        batch.drop_column("organizer_terms_accepted_at")
        batch.drop_column("organizer_terms_version")
