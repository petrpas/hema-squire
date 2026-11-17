"""the tournament day's pools: draws, pools, members, bouts, rankings, piste keys

Revision ID: floor_0004
Revises: floor_0003

The draw and its pools, the bouts recorded by the adopted model, the frozen
pool ranking, and the piste screens' hashed keys (design add-floor-pools D3).
Floor tables only: the office's own drift that autogenerate reports is left
alone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0004"
down_revision: str | Sequence[str] | None = "floor_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "floor_draws",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("score", sa.JSON(), nullable=False),
        sa.Column("previous_score", sa.JSON(), nullable=True),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("announced_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f("fk_floor_draws_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_draws_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_draws")),
        sa.UniqueConstraint(
            "tournament_id", "discipline_id", name=op.f("uq_floor_draws_tournament_id")
        ),
    )
    with op.batch_alter_table("floor_draws", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_draws_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_pool_rankings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("entrant_key", sa.String(length=80), nullable=False),
        sa.Column("place", sa.Integer(), nullable=False),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f("fk_floor_pool_rankings_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_pool_rankings_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_pool_rankings")),
        sa.UniqueConstraint(
            "tournament_id",
            "discipline_id",
            "entrant_key",
            name=op.f("uq_floor_pool_rankings_tournament_id"),
        ),
    )
    with op.batch_alter_table("floor_pool_rankings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_pool_rankings_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_ring_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("piste_id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["piste_id"], ["floor_pistes.id"], name=op.f("fk_floor_ring_keys_piste_id_floor_pistes")
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_ring_keys_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_ring_keys")),
        sa.UniqueConstraint("key_hash", name=op.f("uq_floor_ring_keys_key_hash")),
    )
    with op.batch_alter_table("floor_ring_keys", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_floor_ring_keys_piste_id"), ["piste_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_floor_ring_keys_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_pools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("wave", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.String(length=80), nullable=True),
        sa.Column("piste_id", sa.Integer(), nullable=True),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["draw_id"], ["floor_draws.id"], name=op.f("fk_floor_pools_draw_id_floor_draws")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_pools")),
        sa.UniqueConstraint("draw_id", "number", name=op.f("uq_floor_pools_draw_id")),
    )
    with op.batch_alter_table("floor_pools", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_floor_pools_draw_id"), ["draw_id"], unique=False)

    op.create_table(
        "floor_bouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("a_key", sa.String(length=80), nullable=False),
        sa.Column("b_key", sa.String(length=80), nullable=False),
        sa.Column("score_a", sa.Integer(), nullable=True),
        sa.Column("score_b", sa.Integer(), nullable=True),
        sa.Column("outcome_a", sa.String(length=8), nullable=True),
        sa.Column("outcome_b", sa.String(length=8), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by", sa.String(length=40), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name=op.f("fk_floor_bouts_discipline_id_disciplines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pool_id"], ["floor_pools.id"], name=op.f("fk_floor_bouts_pool_id_floor_pools")
        ),
        sa.ForeignKeyConstraint(
            ["tournament_id"],
            ["tournaments.id"],
            name=op.f("fk_floor_bouts_tournament_id_tournaments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_bouts")),
    )
    with op.batch_alter_table("floor_bouts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_floor_bouts_pool_id"), ["pool_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_floor_bouts_tournament_id"), ["tournament_id"], unique=False
        )

    op.create_table(
        "floor_pool_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("entrant_key", sa.String(length=80), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pool_id"], ["floor_pools.id"], name=op.f("fk_floor_pool_members_pool_id_floor_pools")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_pool_members")),
        sa.UniqueConstraint("pool_id", "entrant_key", name=op.f("uq_floor_pool_members_pool_id")),
    )
    with op.batch_alter_table("floor_pool_members", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_floor_pool_members_pool_id"), ["pool_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("floor_pool_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_pool_members_pool_id"))

    op.drop_table("floor_pool_members")
    with op.batch_alter_table("floor_bouts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_bouts_tournament_id"))
        batch_op.drop_index(batch_op.f("ix_floor_bouts_pool_id"))

    op.drop_table("floor_bouts")
    with op.batch_alter_table("floor_pools", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_pools_draw_id"))

    op.drop_table("floor_pools")
    with op.batch_alter_table("floor_ring_keys", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_ring_keys_tournament_id"))
        batch_op.drop_index(batch_op.f("ix_floor_ring_keys_piste_id"))

    op.drop_table("floor_ring_keys")
    with op.batch_alter_table("floor_pool_rankings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_pool_rankings_tournament_id"))

    op.drop_table("floor_pool_rankings")
    with op.batch_alter_table("floor_draws", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_floor_draws_tournament_id"))

    op.drop_table("floor_draws")
