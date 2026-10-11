"""the unpaid-list treatment is removed: unpaid entrants are always shown faded

Revision ID: c3e8f1a2b4d6
Revises: a9d3e51c7f02
Create Date: 2026-10-11 00:00:00.000000

Drops `tournaments.unpaid_list_treatment`. Every stored value becomes "shown
faded" by owner decision (spec public-entrants): hiding unpaid entrants left a
queue standing behind seats that looked free, so no value needs keeping. The
downgrade restores the column as `greyed`, the old default, for every
tournament.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e8f1a2b4d6"
down_revision: str | Sequence[str] | None = "a9d3e51c7f02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("unpaid_list_treatment")


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "unpaid_list_treatment",
                sa.Enum(
                    "hidden", "greyed", name="unpaidlisttreatment", native_enum=False, length=30
                ),
                nullable=False,
                server_default="greyed",
            )
        )
