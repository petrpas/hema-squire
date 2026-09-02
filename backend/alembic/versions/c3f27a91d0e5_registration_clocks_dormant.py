"""registrations issued for a fencer-list row

Revision ID: c3f27a91d0e5
Revises: b7e91d3a5c40
Create Date: 2026-09-02 00:00:00.000000

`clocks_dormant` marks a registration issued for a row that states who is
competing rather than taken from someone registering now (spec
imported-registrations, "An issued registration's clocks never start"). Such a
registration carries no due date, never expires for non-payment, is never
reminded, and is never demoted when seating settles.

`source_row_id` is the fencer-list row such a registration was issued for, and
is that row's identity rather than a back-reference: the registration takes the
row's place in the list under it, so the fencer keeps the fixed number the row
was born with and appears once rather than twice.

Both default to the pre-change reading — clocks run, no source row — so every
existing registration keeps exactly the behaviour it has today. No backfill: no
registration was issued before this change, by definition.

Note on rollback: a registration issued after this migration and then rolled
back loses its dormancy and becomes an ordinary reserved registration, which is
to say it starts expiring and being reminded. Once the issuing action has been
used, treat this migration as one-way (design, Migration Plan).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f27a91d0e5"
down_revision: str | Sequence[str] | None = "b7e91d3a5c40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "registrations",
        sa.Column(
            "clocks_dormant",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "registrations",
        sa.Column("source_row_id", sa.String(length=80), nullable=True),
    )
    # one registration per source row: the backstop that makes issuing
    # idempotent even if two passes were ever to run at once
    op.create_index(
        "ix_registrations_source_row_id",
        "registrations",
        ["source_row_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_registrations_source_row_id", table_name="registrations")
    op.drop_column("registrations", "source_row_id")
    op.drop_column("registrations", "clocks_dormant")
