"""a registration's participation condition, as a flag on its placements

Revision ID: f7b2d94e6c18
Revises: e3a5c07d19b4
Create Date: 2026-09-25 00:00:00.000000

Adds `registration_disciplines.conditional`, not null, false for every existing
placement: every registration made before the condition existed carries none,
and none is re-placed (spec registration, Participation condition).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7b2d94e6c18"
down_revision: str | Sequence[str] | None = "e3a5c07d19b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("registration_disciplines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("conditional", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("registration_disciplines", schema=None) as batch_op:
        batch_op.drop_column("conditional")
