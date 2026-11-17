"""floor Setup reworked: scope, a day per discipline, pistes and referees by
discipline with a reserve tier, referees per stage, point targets, take-over

Revision ID: floor_0008
Revises: floor_0007

Design rework-floor-setup, Migration Plan. The floor branch was never
deployed, so the mapping serves development databases; the downgrade is
lossy (a per-discipline reserve collapses to "reserve anywhere").
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "floor_0008"
down_revision: str | Sequence[str] | None = "floor_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json(value: object) -> object:
    return json.loads(value) if isinstance(value, str) else value


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "floor_discipline_days",
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("day_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name="fk_floor_discipline_days_discipline_id_disciplines",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["day_id"],
            ["floor_days.id"],
            name="fk_floor_discipline_days_day_id_floor_days",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("discipline_id", name="pk_floor_discipline_days"),
    )
    op.create_table(
        "floor_piste_disciplines",
        sa.Column("piste_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("reserve", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["piste_id"],
            ["floor_pistes.id"],
            name="fk_floor_piste_disciplines_piste_id_floor_pistes",
        ),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name="fk_floor_piste_disciplines_discipline_id_disciplines",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("piste_id", "discipline_id", name="pk_floor_piste_disciplines"),
    )
    op.create_table(
        "floor_official_disciplines",
        sa.Column("official_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("reserve", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["official_id"],
            ["floor_officials.id"],
            name="fk_floor_official_disciplines_official_id_floor_officials",
        ),
        sa.ForeignKeyConstraint(
            ["discipline_id"],
            ["disciplines.id"],
            name="fk_floor_official_disciplines_discipline_id_disciplines",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "official_id", "discipline_id", name="pk_floor_official_disciplines"
        ),
    )

    # 1. a discipline's day: its day pin, failing that the first stored day
    days = bind.execute(
        sa.text("SELECT id, tournament_id, date FROM floor_days ORDER BY date")
    ).all()
    first_day: dict[int, int] = {}
    day_by_date: dict[tuple[int, str], int] = {}
    for day_id, tid, when in days:
        first_day.setdefault(tid, day_id)
        day_by_date[(tid, str(when))] = day_id
    pinned: dict[int, int] = {}
    for tid, target, value in bind.execute(
        sa.text("SELECT tournament_id, target, value FROM floor_pins WHERE kind = 'day'")
    ).all():
        found = day_by_date.get((tid, str(_json(value).get("day"))))
        if found is not None and str(target).isdigit():
            pinned[int(target)] = found
    for discipline_id, tid in bind.execute(
        sa.text("SELECT id, tournament_id FROM disciplines")
    ).all():
        day = pinned.get(discipline_id, first_day.get(tid))
        if day is not None:
            bind.execute(
                sa.text(
                    "INSERT INTO floor_discipline_days (discipline_id, day_id) VALUES (:d, :day)"
                ),
                {"d": discipline_id, "day": day},
            )
    bind.execute(sa.text("DELETE FROM floor_pins WHERE kind = 'day'"))

    # 2. pistes serve every discipline that has a format, reserve as they were
    formats = bind.execute(sa.text("SELECT tournament_id, discipline_id FROM floor_formats")).all()
    by_tournament: dict[int, list[int]] = {}
    for tid, discipline_id in formats:
        by_tournament.setdefault(tid, []).append(discipline_id)
    for piste_id, tid, reserve in bind.execute(
        sa.text("SELECT id, tournament_id, reserve FROM floor_pistes")
    ).all():
        for discipline_id in by_tournament.get(tid, []):
            bind.execute(
                sa.text(
                    "INSERT INTO floor_piste_disciplines (piste_id, discipline_id, reserve) "
                    "VALUES (:p, :d, :r)"
                ),
                {"p": piste_id, "d": discipline_id, "r": bool(reserve)},
            )
    op.drop_table("floor_piste_days")
    with op.batch_alter_table("floor_pistes") as batch:
        batch.drop_column("reserve")

    # 3. officials: their disciplines as regular, every one a main referee
    known = {row[0] for row in bind.execute(sa.text("SELECT id FROM disciplines")).all()}
    for official_id, listed in bind.execute(
        sa.text("SELECT id, discipline_ids FROM floor_officials")
    ).all():
        for discipline_id in sorted({int(d) for d in _json(listed) or []} & known):
            bind.execute(
                sa.text(
                    "INSERT INTO floor_official_disciplines (official_id, discipline_id, reserve) "
                    "VALUES (:o, :d, 0)"
                ),
                {"o": official_id, "d": discipline_id},
            )
    with op.batch_alter_table("floor_officials") as batch:
        batch.add_column(sa.Column("main", sa.Boolean(), nullable=False, server_default="1"))
        batch.drop_column("roles")
        batch.drop_column("discipline_ids")

    # 4. formats: referees per stage, the pause, points and the take-over
    with op.batch_alter_table("floor_formats") as batch:
        batch.add_column(
            sa.Column("referees_pool", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(
            sa.Column("referees_elim", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(sa.Column("points_pool", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("points_elim", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("points_final", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("points_team_bout", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("points_team_final", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("takes_pools_from", sa.Integer(), nullable=True))
        batch.alter_column("slot_pool_overhead", new_column_name="pause_between_pools")
        batch.create_foreign_key(
            "fk_floor_formats_takes_pools_from_disciplines",
            "disciplines",
            ["takes_pools_from"],
            ["id"],
            ondelete="SET NULL",
        )
    for format_id, staffing in bind.execute(
        sa.text("SELECT id, staffing FROM floor_formats")
    ).all():
        referees = max(int((_json(staffing) or {}).get("referee", 1) or 1), 1)
        bind.execute(
            sa.text(
                "UPDATE floor_formats SET referees_pool = :r, referees_elim = :r WHERE id = :i"
            ),
            {"r": referees, "i": format_id},
        )
    with op.batch_alter_table("floor_formats") as batch:
        batch.drop_column("staffing")

    # 5. scope, and the parameters' keys
    with op.batch_alter_table("floor_settings") as batch:
        batch.add_column(
            sa.Column("plan_schedule", sa.Boolean(), nullable=False, server_default="1")
        )
        batch.add_column(sa.Column("multi_day", sa.Boolean(), nullable=False, server_default="0"))
        batch.add_column(
            sa.Column("plan_officials", sa.Boolean(), nullable=False, server_default="0")
        )
    day_counts: dict[int, int] = {}
    for _, tid, _ in days:
        day_counts[tid] = day_counts.get(tid, 0) + 1
    with_officials = {
        row[0] for row in bind.execute(sa.text("SELECT tournament_id FROM floor_officials")).all()
    }
    stored = {
        tid: _json(params) or {}
        for tid, params in bind.execute(
            sa.text("SELECT tournament_id, params FROM floor_settings")
        ).all()
    }
    for tid in set(day_counts) | with_officials | set(stored):
        params = dict(stored.get(tid, {}))
        if "finals_last" in params:
            params["finals"] = "day" if params.pop("finals_last") else "elimination"
        if "prefer_larger_pools" in params:
            params["pool_size"] = "larger" if params.pop("prefer_larger_pools") else "smaller"
        values = {
            "t": tid,
            "p": json.dumps(params),
            "m": day_counts.get(tid, 0) > 1,
            "o": tid in with_officials,
        }
        if tid in stored:
            bind.execute(
                sa.text(
                    "UPDATE floor_settings SET params = :p, multi_day = :m, plan_officials = :o "
                    "WHERE tournament_id = :t"
                ),
                values,
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO floor_settings "
                    "(tournament_id, params, plan_schedule, multi_day, plan_officials) "
                    "VALUES (:t, :p, 1, :m, :o)"
                ),
                values,
            )

    # 6. a plan without a schedule stores pools with no piste and no time
    with op.batch_alter_table("floor_plan_activities") as batch:
        batch.alter_column("piste_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("starts_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch.alter_column("ends_at", existing_type=sa.DateTime(timezone=True), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("DELETE FROM floor_plan_activities WHERE piste_id IS NULL"))
    with op.batch_alter_table("floor_plan_activities") as batch:
        batch.alter_column("piste_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("starts_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.alter_column("ends_at", existing_type=sa.DateTime(timezone=True), nullable=False)

    for tid, params in bind.execute(
        sa.text("SELECT tournament_id, params FROM floor_settings")
    ).all():
        values = dict(_json(params) or {})
        if "finals" in values:
            values["finals_last"] = values.pop("finals") != "elimination"
        if "pool_size" in values:
            values["prefer_larger_pools"] = values.pop("pool_size") != "smaller"
        bind.execute(
            sa.text("UPDATE floor_settings SET params = :p WHERE tournament_id = :t"),
            {"p": json.dumps(values), "t": tid},
        )
    with op.batch_alter_table("floor_settings") as batch:
        batch.drop_column("plan_officials")
        batch.drop_column("multi_day")
        batch.drop_column("plan_schedule")

    with op.batch_alter_table("floor_formats") as batch:
        batch.add_column(sa.Column("staffing", sa.JSON(), nullable=True))
    for format_id, referees in bind.execute(
        sa.text("SELECT id, referees_pool FROM floor_formats")
    ).all():
        bind.execute(
            sa.text("UPDATE floor_formats SET staffing = :s WHERE id = :i"),
            {"s": json.dumps({"referee": referees, "judge": 0, "table": 0}), "i": format_id},
        )
    with op.batch_alter_table("floor_formats") as batch:
        batch.drop_constraint("fk_floor_formats_takes_pools_from_disciplines", type_="foreignkey")
        batch.alter_column("pause_between_pools", new_column_name="slot_pool_overhead")
        batch.drop_column("takes_pools_from")
        batch.drop_column("points_team_final")
        batch.drop_column("points_team_bout")
        batch.drop_column("points_final")
        batch.drop_column("points_elim")
        batch.drop_column("points_pool")
        batch.drop_column("referees_elim")
        batch.drop_column("referees_pool")

    with op.batch_alter_table("floor_officials") as batch:
        batch.add_column(
            sa.Column("roles", sa.JSON(), nullable=False, server_default='["referee"]')
        )
        batch.add_column(
            sa.Column("discipline_ids", sa.JSON(), nullable=False, server_default="[]")
        )
    served: dict[int, list[int]] = {}
    for official_id, discipline_id in bind.execute(
        sa.text("SELECT official_id, discipline_id FROM floor_official_disciplines")
    ).all():
        served.setdefault(official_id, []).append(discipline_id)
    for official_id, listed in served.items():
        bind.execute(
            sa.text("UPDATE floor_officials SET discipline_ids = :d WHERE id = :i"),
            {"d": json.dumps(sorted(listed)), "i": official_id},
        )
    with op.batch_alter_table("floor_officials") as batch:
        batch.drop_column("main")

    with op.batch_alter_table("floor_pistes") as batch:
        batch.add_column(sa.Column("reserve", sa.Boolean(), nullable=False, server_default="0"))
    op.create_table(
        "floor_piste_days",
        sa.Column("piste_id", sa.Integer(), nullable=False),
        sa.Column("day_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["piste_id"], ["floor_pistes.id"], name="fk_floor_piste_days_piste_id_floor_pistes"
        ),
        sa.ForeignKeyConstraint(
            ["day_id"], ["floor_days.id"], name="fk_floor_piste_days_day_id_floor_days"
        ),
        sa.PrimaryKeyConstraint("piste_id", "day_id", name="pk_floor_piste_days"),
    )
    reserve_pistes = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT DISTINCT piste_id FROM floor_piste_disciplines WHERE reserve = 1")
        ).all()
    }
    for piste_id in reserve_pistes:
        bind.execute(sa.text("UPDATE floor_pistes SET reserve = 1 WHERE id = :i"), {"i": piste_id})
    for piste_id, day_id in bind.execute(
        sa.text(
            "SELECT DISTINCT pd.piste_id, dd.day_id FROM floor_piste_disciplines pd "
            "JOIN floor_discipline_days dd ON dd.discipline_id = pd.discipline_id"
        )
    ).all():
        bind.execute(
            sa.text("INSERT INTO floor_piste_days (piste_id, day_id) VALUES (:p, :d)"),
            {"p": piste_id, "d": day_id},
        )

    op.drop_table("floor_official_disciplines")
    op.drop_table("floor_piste_disciplines")
    op.drop_table("floor_discipline_days")
