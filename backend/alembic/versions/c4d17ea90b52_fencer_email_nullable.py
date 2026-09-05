"""a fencer record enrolled by the organizer needs no address

Revision ID: c4d17ea90b52
Revises: f1a83c6e42d7
Create Date: 2026-09-05 00:00:00.000000

An address identifies an *account*: it is what a login is looked up by, and what
the signup form refuses a second time. A fencer record the organizer creates on
the tournament's behalf is not an account — it holds no credentials, cannot be
logged into, and is never written to (spec `fencer-accounts`) — so the address
was a constraint of the first kind of record imposed on the second.

What it cost is concrete. The pilot's fencer list carries two brothers entered
by one parent on one address; only the first could be enrolled, so neither was
billable, and the organizer met it four screens away as "this fencer is not in
the list".

The unique index stays. An address that is present is still a login and still
unique across the deployment; NULL is not equal to NULL in either SQLite or
Postgres, so the index admits any number of records holding none.

No backfill: every existing row has an address, and none is taken away.

The downgrade reimposes NOT NULL and will fail while any record created under
this revision exists. Like the dormancy column before it, treat as one-way in
practice once used.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d17ea90b52"
down_revision: str | Sequence[str] | None = "f1a83c6e42d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch mode because the deployment runs on SQLite, which cannot alter a
    # column's nullability in place and rebuilds the table instead
    with op.batch_alter_table("fencers", schema=None) as batch_op:
        batch_op.alter_column(
            "email", existing_type=sa.String(length=320), nullable=True
        )


def downgrade() -> None:
    with op.batch_alter_table("fencers", schema=None) as batch_op:
        batch_op.alter_column(
            "email", existing_type=sa.String(length=320), nullable=False
        )
