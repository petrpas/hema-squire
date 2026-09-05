"""where a tournament's registration is held when Squire does not hold it

Revision ID: e7b25f4a9c31
Revises: d4e18a3c07b6
Create Date: 2026-09-05 00:00:00.000000

`external_registration_url` is the address a fencer is sent to when the
organizer keeps the registrations (spec external-registration). It is mandatory
to publish such a tournament and optional on every other, so the column is
nullable and there is nothing to backfill: every tournament predating this is
Squire-kept and needs no address.

Squire stores it and presents it. It never fetches it, never checks that it
resolves and never reports it as dead.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7b25f4a9c31"
down_revision: str | Sequence[str] | None = "d4e18a3c07b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column("external_registration_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "external_registration_url")
