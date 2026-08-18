"""tournament setup and itemized pricing

Revision ID: a7c41e90d2b5
Revises: b0a1f1e36817
Create Date: 2026-07-19

Adds tournament setup fields (location, titular organizer names, registration
window), the itemized-pricing structures (extra_items, registration_extras,
ordered discounts), and makes discipline fees nullable so Setup rows can exist
before pricing is decided. Existing tournaments get empty JSON lists and keep
legacy pricing behavior.
"""

import sqlalchemy as sa
from alembic import op

revision = "a7c41e90d2b5"
down_revision = "b0a1f1e36817"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(sa.Column("location", sa.String(length=300), nullable=True))
        batch.add_column(
            sa.Column(
                "organizer_names",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch.add_column(sa.Column("registration_opens", sa.Date(), nullable=True))
        batch.add_column(sa.Column("registration_closes", sa.Date(), nullable=True))
        batch.add_column(
            sa.Column(
                "discounts",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )

    with op.batch_alter_table("disciplines") as batch:
        batch.alter_column("fee", existing_type=sa.Integer(), nullable=True)

    op.create_table(
        "extra_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("max_qty", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "registration_extras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("registration_id", sa.Integer(), nullable=False),
        sa.Column("extra_item_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"]),
        sa.ForeignKeyConstraint(["extra_item_id"], ["extra_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_id", "extra_item_id"),
    )


def downgrade() -> None:
    op.drop_table("registration_extras")
    op.drop_table("extra_items")
    with op.batch_alter_table("disciplines") as batch:
        batch.alter_column("fee", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_column("discounts")
        batch.drop_column("registration_closes")
        batch.drop_column("registration_opens")
        batch.drop_column("organizer_names")
        batch.drop_column("location")
