"""the tournament records its bank account's holder

Revision ID: e5a7c9b1d3f6
Revises: d4f6a8c1e3b5
Create Date: 2026-10-29 12:00:00.000000

Adds `tournament.bank_account_holder`, the beneficiary name an EPC (EUR)
payment code must carry (change eur-payment-qr-epc). No backfill: a tournament
taking EUR is told on `PUBLISH` to record it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a7c9b1d3f6"
down_revision: str | Sequence[str] | None = "d4f6a8c1e3b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(sa.Column("bank_account_holder", sa.String(length=70), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_column("bank_account_holder")
