"""a placement's queue moment, and the mark a promotion leaves until paid

Revision ID: e3a5c07d19b4
Revises: d4a1c8b7e310
Create Date: 2026-09-24 00:00:00.000000

Adds `registration_disciplines.queued_since` and `teams.waitlisted_since`, the
moment a placement's place in the queue counts from, and `promoted_unpaid` on
both, the mark a promotion leaves on what it seated until the registration is
paid (design demotion-hardening D1, D6b).

The moments are backfilled from what the queue was ordered by until now — the
registration time for an individual placement, the moment the team was entered
for a team — so no queue reorders on deploy. Only then are they made not null.
No existing placement was seated by a promotion this change can recognise, so
every mark starts false.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3a5c07d19b4"
down_revision: str | Sequence[str] | None = "d4a1c8b7e310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("registration_disciplines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("queued_since", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("promoted_unpaid", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    with op.batch_alter_table("teams", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("waitlisted_since", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("promoted_unpaid", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    op.execute(
        "UPDATE registration_disciplines SET queued_since = ("
        " SELECT registrations.registered_at FROM registrations"
        " WHERE registrations.id = registration_disciplines.registration_id)"
    )
    # `created_at` is nullable in the schema though a server default always
    # fills it; the registration time stands in for one that is missing
    op.execute(
        "UPDATE teams SET waitlisted_since = COALESCE(created_at, ("
        " SELECT registrations.registered_at FROM registrations"
        " WHERE registrations.id = teams.registration_id))"
    )

    with op.batch_alter_table("registration_disciplines", schema=None) as batch_op:
        batch_op.alter_column(
            "queued_since", existing_type=sa.DateTime(timezone=True), nullable=False
        )
    with op.batch_alter_table("teams", schema=None) as batch_op:
        batch_op.alter_column(
            "waitlisted_since", existing_type=sa.DateTime(timezone=True), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("teams", schema=None) as batch_op:
        batch_op.drop_column("promoted_unpaid")
        batch_op.drop_column("waitlisted_since")
    with op.batch_alter_table("registration_disciplines", schema=None) as batch_op:
        batch_op.drop_column("promoted_unpaid")
        batch_op.drop_column("queued_since")
