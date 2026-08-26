"""registration opening time and tournament timezone

Revision ID: c8f5a2e17b30
Revises: b3d1f0a72c45
Create Date: 2026-08-25 00:00:00.000000

Adds the wall-clock time registration opens (`registration_opens_time`, unset
meaning the start of the local day) and the tournament's own zone
(`timezone`), which every timeline date is henceforth read in.

The zone is backfilled to the launch market's zone in the same revision, so no
tournament is ever observable without one — a nullable zone would leave every
read site to decide what NULL means (design add-registration-open-time D2).

Existing tournaments therefore shift: an opening date still in the future
resolves at 00:00 local rather than 00:00 UTC. Europe/Prague is ahead of UTC,
so its day turns first and registration opens one or two hours *earlier* than
it would have — at the start of the day the organizer named, rather than at
01:00 or 02:00 the following morning. No stored value is rewritten, and a
tournament whose opening has already passed is untouched, since the gate is
only consulted before it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8f5a2e17b30"
down_revision: str | Sequence[str] | None = "b3d1f0a72c45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# transcribed rather than imported: a migration states the value it wrote, and
# must keep stating it after the constant moves on (app.constraints)
DEFAULT_TIMEZONE = "Europe/Prague"


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("registration_opens_time", sa.Time(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "timezone",
                sa.String(length=64),
                nullable=False,
                server_default=DEFAULT_TIMEZONE,
            )
        )

    # the default existed only to backfill; the ORM supplies it from here on
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.alter_column("timezone", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("timezone")
        batch_op.drop_column("registration_opens_time")
