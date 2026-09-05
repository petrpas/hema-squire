"""who keeps a tournament's registrations

Revision ID: d4e18a3c07b6
Revises: c3f27a91d0e5
Create Date: 2026-09-05 00:00:00.000000

`registrations_kept_by` says whether Squire owns a tournament's list of entrants
or the organizer keeps it somewhere else and imports it (spec
registration-ownership). An organizer-kept tournament accepts no in-app
registration and is excluded from the scheduler's pass over tournaments
outright, so nothing runs against its roster whatever created it.

Every existing tournament is `squire`, unconditionally and without deriving
anything from what it holds. Unlike the four feature flags, which were derived
generously from evidence of use, there is nothing to infer here: a tournament
that has been imported into still has an open registration form and a running
scheduler, which is precisely what `squire` means. Turning one organizer-kept is
a decision its organizer takes, with a confirmation stating what stops.

The column is a short string with no check constraint, following `str_enum`'s
`native_enum=False` treatment throughout this schema, so a third member could be
added later without a migration.

Note on rollback: a tournament switched to `organizer` and then rolled back
becomes Squire-kept again, which reopens its registration form and puts its
roster back under the lifecycle clocks. Once the switch has been used on a live
tournament, a rollback needs the same warning the switch itself carries.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e18a3c07b6"
down_revision: str | Sequence[str] | None = "c3f27a91d0e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column(
            "registrations_kept_by",
            sa.String(length=30),
            nullable=False,
            server_default="squire",
        ),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "registrations_kept_by")
