"""a registration may carry a contact address of its own

Revision ID: d4a1c8b7e310
Revises: c7b31e4a9d02
Create Date: 2026-09-13 00:00:00.000000

Adds Registration.contact_email, nullable and not unique: the address belonging
to the seat rather than to the account holding it, written by a substitution
that kept the address the seat came with (spec `registration`, "A registration
may carry a contact address of its own").

Additive and empty. No registration has one today, nothing reads it until a
substitution writes one, and so there is nothing to backfill.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a1c8b7e310"
down_revision: str | Sequence[str] | None = "c7b31e4a9d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("registrations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contact_email", sa.String(length=320), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("registrations", schema=None) as batch_op:
        batch_op.drop_column("contact_email")
