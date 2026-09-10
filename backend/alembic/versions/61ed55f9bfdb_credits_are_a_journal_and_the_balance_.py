"""credits are a journal and the balance is derived

Revision ID: 61ed55f9bfdb
Revises: d5a83c1f206e
Create Date: 2026-09-09 00:00:00.000000

**This revision destroys payment state and does not carry it forward.**

It creates the two journals empty, drops the five columns the balance and the
settled state used to live in, and removes `paid` from the registration state
enum. Nothing is backfilled. A registration that read `paid` becomes `reserved`
and, holding no credits, reads as unsettled.

That is only correct because the owner decided on 2026-09-09 that the data in
existence at that moment is test data, to be dropped and re-imported. **This
revision is not a template.** A migration against books somebody relies on
would have to decompose each counter into the credits it was the sum of, and
the whole reason for the change is that no such decomposition exists — the
counter records no composition, and inventing one would write a payment with a
fabricated source into the journal built to make that impossible.

`downgrade` restores the columns and the enum value, empty. It cannot restore
the balances, for the same reason, and says so rather than appearing to.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61ed55f9bfdb"
down_revision: str | Sequence[str] | None = "d5a83c1f206e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "payment_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("registration_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.Enum("CZK", "EUR", name="currency", native_enum=False, length=30),
            nullable=False,
        ),
        sa.Column("value_date", sa.Date(), nullable=False),
        sa.Column(
            "source_kind",
            sa.Enum(
                "bank_transaction",
                "manual_payment",
                name="creditsource",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "origin",
            sa.Enum(
                "auto_vs",
                "payment_link",
                "reinstate",
                "refund_hold",
                "recorded",
                name="creditorigin",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.String(length=200), nullable=True),
        sa.Column("reversed_reason", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # the idempotence guarantee: one source credits one registration at most
    # once while that credit is live. Partial, so a reversal frees the pair to
    # be credited afresh as a new row
    op.create_index(
        "uq_payment_credits_live_source",
        "payment_credits",
        ["registration_id", "source_kind", "source_id"],
        unique=True,
        sqlite_where=sa.text("reversed_at IS NULL"),
        postgresql_where=sa.text("reversed_at IS NULL"),
    )
    op.create_index(
        "ix_payment_credits_registration_live",
        "payment_credits",
        ["registration_id", "reversed_at"],
    )

    op.create_table(
        "payment_waivers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("registration_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("granted_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_waivers_registration_live",
        "payment_waivers",
        ["registration_id", "revoked_at"],
    )

    # every registration reading `paid` becomes `reserved`: the lifecycle keeps
    # what a person or a clock decided, and whether the money is in is now read
    # from the journal, which for existing rows holds nothing
    op.execute("UPDATE registrations SET state = 'reserved' WHERE state = 'paid'")

    with op.batch_alter_table("registrations") as batch:
        batch.drop_column("amount_paid_cents")
        batch.drop_column("amount_paid_eur_cents")
        batch.drop_column("paid_at")
        batch.drop_column("settled_by_hand_at")
        batch.drop_column("settled_by_hand_reason")


def downgrade() -> None:
    """Downgrade schema.

    Restores the shape and not the content. Every registration comes back
    unpaid with empty counters, because the credits the counters were the sum
    of are the only record of them and this drops that record.
    """
    with op.batch_alter_table("registrations") as batch:
        batch.add_column(
            sa.Column("amount_paid_cents", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("amount_paid_eur_cents", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("settled_by_hand_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("settled_by_hand_reason", sa.String(length=200), nullable=True))

    op.drop_index("ix_payment_waivers_registration_live", table_name="payment_waivers")
    op.drop_table("payment_waivers")
    op.drop_index("ix_payment_credits_registration_live", table_name="payment_credits")
    op.drop_index("uq_payment_credits_live_source", table_name="payment_credits")
    op.drop_table("payment_credits")
