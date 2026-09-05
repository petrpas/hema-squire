"""resolving a payment by the words the payer wrote

Revision ID: f1a83c6e42d7
Revises: e7b25f4a9c31
Create Date: 2026-09-05 00:00:00.000000

A variable symbol is a shortcut: quoted, it finds a registration without anybody
reading the message. About one payment in ten carries none or carries one that is
wrong, and on a tournament whose registrations the organizer keeps none carries
one at all. Those are resolved from the payer's own text, which needs three
things stored (spec name-assisted-matching).

`named_person` is who the payment is *for*, as the statement's own text named
them, read at parse time. Never the payer: one person routinely pays for another,
and the pilot's statement has one club organizer paying for three fencers.

`proposed_fencer_id` is who the resolver proposes, while the transaction sits in
the new `likely` status. That status needs no migration of its own — the column
is a plain `String(20)` with no check constraint — and it is a *proposal*: no
money moves and no mail is sent until a person confirms.

`rejected_fencer_ids` remembers who the organizer refused for this payment, so
the resolver does not offer the same wrong answer twice. Per payment, not per
fencer: a name that mis-attracts one payment has not stopped being somebody's
name.

No backfill. Transactions ingested before this carry no named person, and
running the resolver over them retrospectively is a deliberate action rather
than a migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a83c6e42d7"
down_revision: str | Sequence[str] | None = "e7b25f4a9c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bank_transactions", sa.Column("named_person", sa.Text(), nullable=True))
    op.add_column(
        "bank_transactions",
        sa.Column("proposed_fencer_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column(
            "rejected_fencer_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    # SQLite cannot add a foreign key to an existing table, and the schema this
    # deployment runs on is SQLite. The reference is enforced in the ORM, where
    # every writer of this column lives; naming it here would need a table
    # rebuild for a constraint no writer can violate.


def downgrade() -> None:
    op.drop_column("bank_transactions", "rejected_fencer_ids")
    op.drop_column("bank_transactions", "proposed_fencer_id")
    op.drop_column("bank_transactions", "named_person")
