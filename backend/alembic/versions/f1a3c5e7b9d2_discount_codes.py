"""a discount a fencer types in

Revision ID: f1a3c5e7b9d2
Revises: e5a7c9b1d3f6
Create Date: 2026-11-01 12:00:00.000000

Adds `discount_codes`, and on `registrations` the code a registration carries
and whether it covered the total (change add-discount-codes). No backfill: no
registration has a code yet. Downgrading once codes are in use strips them from
registrations whose stored totals keep the discount.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a3c5e7b9d2"
down_revision: str | Sequence[str] | None = "e5a7c9b1d3f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discount_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("effect", sa.JSON(), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.UniqueConstraint("tournament_id", "code"),
    )
    with op.batch_alter_table("registrations") as batch:
        batch.add_column(sa.Column("discount_code_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("code_covered", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.create_foreign_key(
            "fk_registrations_discount_code_id",
            "discount_codes",
            ["discount_code_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("registrations") as batch:
        batch.drop_constraint("fk_registrations_discount_code_id", type_="foreignkey")
        batch.drop_column("code_covered")
        batch.drop_column("discount_code_id")
    op.drop_table("discount_codes")
