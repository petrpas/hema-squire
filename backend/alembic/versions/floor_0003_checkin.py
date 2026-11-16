"""the tournament day's check-in: arrivals, withdrawals, lineups, snapshots

Revision ID: floor_0003
Revises: floor_0002

Arrivals, withdrawals and lineups over roster keys, floor-only persons, and
the snapshot a closed check-in freezes (design add-floor-checkin D1). Floor
tables only: the office's own drift that autogenerate reports is left alone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0003"
down_revision: str | Sequence[str] | None = "floor_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_arrivals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("person_key", sa.String(length=80), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_arrivals_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_arrivals")),
        sa.UniqueConstraint(
            "tournament_id", "person_key", name=op.f("uq_floor_arrivals_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_arrivals", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_arrivals_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_lineups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("team_key", sa.String(length=80), nullable=False),
        sa.Column("person_key", sa.String(length=80), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_lineups_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_lineups")),
        sa.UniqueConstraint(
            "tournament_id", "team_key", "person_key", name=op.f("uq_floor_lineups_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_lineups", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_lineups_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_local_persons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("club", sa.String(length=200), nullable=True),
        sa.Column("nationality", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_local_persons_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_local_persons")),
    )
    with op.batch_alter_table("floor_local_persons", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_local_persons_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_withdrawals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("entry_key", sa.String(length=120), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_withdrawals_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_withdrawals")),
        sa.UniqueConstraint(
            "tournament_id", "entry_key", name=op.f("uq_floor_withdrawals_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_withdrawals", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_withdrawals_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f("fk_floor_snapshots_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_snapshots_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_snapshots")),
        sa.UniqueConstraint(
            "tournament_id", "discipline_id", name=op.f("uq_floor_snapshots_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_snapshots", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_snapshots_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_snapshot_entrants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("entrant_key", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("club", sa.String(length=200), nullable=True),
        sa.Column("nationality", sa.String(length=80), nullable=True),
        sa.Column("hr_id", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("members", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["floor_snapshots.id"],
            name=op.f("fk_floor_snapshot_entrants_snapshot_id_floor_snapshots"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_snapshot_entrants")),
    )
    with op.batch_alter_table("floor_snapshot_entrants", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_snapshot_entrants_snapshot_id"), ["snapshot_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("floor_snapshot_entrants", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_snapshot_entrants_snapshot_id"))

    op.drop_table("floor_snapshot_entrants")
    with op.batch_alter_table("floor_snapshots", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_snapshots_tournament_id"))

    op.drop_table("floor_snapshots")
    with op.batch_alter_table("floor_withdrawals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_withdrawals_tournament_id"))

    op.drop_table("floor_withdrawals")
    with op.batch_alter_table("floor_local_persons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_local_persons_tournament_id"))

    op.drop_table("floor_local_persons")
    with op.batch_alter_table("floor_lineups", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_lineups_tournament_id"))

    op.drop_table("floor_lineups")
    with op.batch_alter_table("floor_arrivals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_arrivals_tournament_id"))

    op.drop_table("floor_arrivals")
