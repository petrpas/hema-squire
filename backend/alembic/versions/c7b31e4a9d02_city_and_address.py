"""city and address

Revision ID: c7b31e4a9d02
Revises: 61ed55f9bfdb
Create Date: 2026-09-12 00:00:00.000000

`location` was one free-text line doing two jobs: the town, which a card has
room for and which needs no link because everyone knows where Berlin is, and
where in that town, which wants a venue name and a map link and is read on the
tournament's own page. It becomes `city`, and `address` is added beside it.

The rename carries every existing value into `city`: a location today is far
more often "Brno" than a street, and a town that turns out to have been an
address is one field for an organizer to re-cut, while the reverse — dropping
the values and asking for both again — is every tournament re-entered.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7b31e4a9d02"
down_revision: str | Sequence[str] | None = "61ed55f9bfdb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.alter_column(
            "location",
            new_column_name="city",
            existing_type=sa.String(length=300),
            type_=sa.String(length=120),
        )
        batch_op.add_column(sa.Column("address", sa.String(length=300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("address")
        batch_op.alter_column(
            "city",
            new_column_name="location",
            existing_type=sa.String(length=120),
            type_=sa.String(length=300),
        )
