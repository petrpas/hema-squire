"""the floor's Data sheet: hand edits, added entries and teams, fetched ratings

Revision ID: floor_0010
Revises: floor_0009

A layer over the floor roster that the office never sees (design
floor-data-sheet D3), and an HR id for a floor-only person.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0010"
down_revision: str | Sequence[str] | None = "floor_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _owned(name: str, *columns: sa.Column, unique: tuple[str, ...] = ()) -> None:
    """A table hanging from the tournament, indexed by it."""
    args: list[sa.SchemaItem] = [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        *columns,
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f(f"fk_{name}_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{name}")),
    ]
    if unique:
        args.append(
            sa.UniqueConstraint("tournament_id", *unique, name=op.f(f"uq_{name}_tournament_id"))
        )
    op.create_table(name, *args)
    with op.batch_alter_table(name) as batch:
        batch.create_index(batch.f(f"ix_{name}_tournament_id"), ["tournament_id"], unique=False)


def _discipline(name: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f(f"fk_{name}_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
    ]


def upgrade() -> None:
    stamp = [
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("by", sa.Integer(), nullable=True),
    ]
    _owned(
        "floor_sheet_edits",
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("field", sa.String(length=16), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        *[c.copy() for c in stamp],
        unique=("subject", "field"),
    )
    _owned(
        "floor_sheet_entries",
        sa.Column("person_key", sa.String(length=80), nullable=False),
        *_discipline("floor_sheet_entries"),
        *[c.copy() for c in stamp],
        unique=("person_key", "discipline_id"),
    )
    _owned(
        "floor_sheet_teams",
        *_discipline("floor_sheet_teams"),
        sa.Column("name", sa.String(length=200), nullable=False),
        *[c.copy() for c in stamp],
    )
    _owned(
        "floor_sheet_fetches",
        *_discipline("floor_sheet_fetches"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asked", sa.JSON(), nullable=False),
        unique=("discipline_id",),
    )
    op.create_table(
        "floor_sheet_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fetch_id", sa.Integer(), nullable=False),
        sa.Column("hr_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fetch_id"],
            ["floor_sheet_fetches.id"],
            name=op.f("fk_floor_sheet_ratings_fetch_id_floor_sheet_fetches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_sheet_ratings")),
    )
    with op.batch_alter_table("floor_sheet_ratings") as batch:
        batch.create_index(batch.f("ix_floor_sheet_ratings_fetch_id"), ["fetch_id"], unique=False)
    with op.batch_alter_table("floor_local_persons") as batch:
        batch.add_column(sa.Column("hr_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("floor_local_persons") as batch:
        batch.drop_column("hr_id")
    for name in (
        "floor_sheet_ratings",
        "floor_sheet_fetches",
        "floor_sheet_teams",
        "floor_sheet_entries",
        "floor_sheet_edits",
    ):
        op.drop_table(name)
