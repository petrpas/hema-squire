"""The floor's tables (design add-floor-console D2, D3).

Every table is prefixed `floor_`. A reference to an office table is a string
foreign key (`"tournaments.id"`, `"disciplines.id"`), so nothing here imports
`app.models`. A person is referred to by the roster's opaque key string, with
no foreign key: a key names a replay row, not a table row.

`app.tournament_delete` removes these tables by their prefix, children first,
without importing this module.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FloorDay(Base):
    """One working window of the tournament, in its own timezone's wall clock."""

    __tablename__ = "floor_days"
    __table_args__ = (UniqueConstraint("tournament_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    start: Mapped[time] = mapped_column(Time)
    end: Mapped[time] = mapped_column(Time)
    # [["12:00", "12:45"], …], in order, inside the day, not overlapping
    breaks: Mapped[list[list[str]]] = mapped_column(JSON, default=list)


class FloorPiste(Base):
    __tablename__ = "floor_pistes"
    __table_args__ = (UniqueConstraint("tournament_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    # the display order
    ordinal: Mapped[int] = mapped_column(Integer)
    # held back from the first plan, available to re-planning
    reserve: Mapped[bool] = mapped_column(default=False)
    tag: Mapped[str | None] = mapped_column(String(80))


class FloorPisteDay(Base):
    """A piste is available on this day."""

    __tablename__ = "floor_piste_days"

    piste_id: Mapped[int] = mapped_column(ForeignKey("floor_pistes.id"), primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("floor_days.id"), primary_key=True)


class FloorFormat(Base):
    """How one discipline is fought. Absent means the discipline is incomplete."""

    __tablename__ = "floor_formats"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    # by id, never by slug; a discipline deleted in the office takes its format
    # with it, so the office's delete needs no knowledge of the floor
    discipline_id: Mapped[int] = mapped_column(
        ForeignKey("disciplines.id", ondelete="CASCADE"), unique=True
    )
    pool_min: Mapped[int] = mapped_column(Integer)
    pool_max: Mapped[int] = mapped_column(Integer)
    # how many advance; NULL is "all", the one meaning NULL has here
    advance: Mapped[int | None] = mapped_column(Integer)
    third_place: Mapped[bool] = mapped_column(default=False)
    # role → officials one piste needs; NULL until the organizer states it
    staffing: Mapped[dict[str, int] | None] = mapped_column(JSON)
    slot_pool_bout: Mapped[int] = mapped_column(Integer)
    slot_elim_bout: Mapped[int] = mapped_column(Integer)
    slot_pool_overhead: Mapped[int] = mapped_column(Integer)
    # team disciplines only
    slot_team_match: Mapped[int | None] = mapped_column(Integer)


class FloorOfficial(Base):
    __tablename__ = "floor_officials"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # the roster person this official is, when they also fence
    person_key: Mapped[str | None] = mapped_column(String(80))
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    discipline_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    ordinal: Mapped[int] = mapped_column(Integer)


class FloorOfficialDay(Base):
    """An official is available on this day."""

    __tablename__ = "floor_official_days"

    official_id: Mapped[int] = mapped_column(ForeignKey("floor_officials.id"), primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("floor_days.id"), primary_key=True)


class FloorSettings(Base):
    """The organizer's parameters, one document per tournament. Read through
    `app.floor.setup.Params`, whose defaults stand in for absent keys."""

    __tablename__ = "floor_settings"

    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), primary_key=True)
    params: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class FloorPlan(Base):
    """One version of the tournament's plan (spec floor-plan, A plan is a
    stored version): at most one working, at most one published, the earlier
    published ones kept as history."""

    __tablename__ = "floor_plans"
    __table_args__ = (
        UniqueConstraint("tournament_id", "version"),
        Index(
            "uq_floor_plans_working",
            "tournament_id",
            unique=True,
            sqlite_where=text("status = 'working'"),
        ),
        Index(
            "uq_floor_plans_published",
            "tournament_id",
            unique=True,
            sqlite_where=text("status = 'published'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    # working | published | history
    status: Mapped[str] = mapped_column(String(16))
    # [{"discipline_id", "k", "day": "YYYY-MM-DD"}]
    variant: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    exclusions: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    collisions: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # the account that made it, by id; no foreign key into the office, and no
    # text that would need redacting when the account goes
    created_by: Mapped[int | None] = mapped_column(Integer)


class FloorPlanActivity(Base):
    __tablename__ = "floor_plan_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("floor_plans.id"), index=True)
    # the engine's deterministic id, "LS:pool:3", by which versions are compared
    activity_id: Mapped[str] = mapped_column(String(80))
    discipline_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(8))
    ordinal: Mapped[int] = mapped_column(Integer)
    round: Mapped[int] = mapped_column(Integer)
    piste_id: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    final: Mapped[bool] = mapped_column(Boolean, default=False)
    # a pool's participants
    size: Mapped[int] = mapped_column(Integer, default=0)


class FloorPin(Base):
    """A decision the planner does not move (spec floor-plan, Decisions are
    pinned and unpinned). `gate` names the gate that added it; such a pin goes
    only by reopening that gate."""

    __tablename__ = "floor_pins"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    # day | k | place | sequence
    kind: Mapped[str] = mapped_column(String(16))
    # what it fixes: a discipline id, or an activity id
    target: Mapped[str] = mapped_column(String(80))
    value: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    gate: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(Integer)


# ------------------------------------------------------------ check-in
# (spec floor-checkin; design add-floor-checkin D1). State is rows over roster
# keys; undoing deletes the row. Nothing here is written to the office.


class FloorArrival(Base):
    __tablename__ = "floor_arrivals"
    __table_args__ = (UniqueConstraint("tournament_id", "person_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    person_key: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    by: Mapped[int | None] = mapped_column(Integer)


class FloorWithdrawal(Base):
    __tablename__ = "floor_withdrawals"
    __table_args__ = (UniqueConstraint("tournament_id", "entry_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    # "<person key>@<discipline id>", or a team's "team:<id>"
    entry_key: Mapped[str] = mapped_column(String(120))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    by: Mapped[int | None] = mapped_column(Integer)


class FloorLineup(Base):
    """The day's lineup of a team; absent means the roster's members."""

    __tablename__ = "floor_lineups"
    __table_args__ = (UniqueConstraint("tournament_id", "team_key", "person_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    team_key: Mapped[str] = mapped_column(String(80))
    person_key: Mapped[str] = mapped_column(String(80))
    ordinal: Mapped[int] = mapped_column(Integer)


class FloorLocalPerson(Base):
    """A person who exists only on the floor: a substitute named at the desk.
    Keyed `local:<id>`, a prefix the office never issues."""

    __tablename__ = "floor_local_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    club: Mapped[str | None] = mapped_column(String(200))
    nationality: Mapped[str | None] = mapped_column(String(80))


class FloorSnapshot(Base):
    """A discipline's entrants as check-in closed on them."""

    __tablename__ = "floor_snapshots"
    __table_args__ = (UniqueConstraint("tournament_id", "discipline_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"))
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[int | None] = mapped_column(Integer)
    n: Mapped[int] = mapped_column(Integer)


class FloorSnapshotEntrant(Base):
    __tablename__ = "floor_snapshot_entrants"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("floor_snapshots.id"), index=True)
    entrant_key: Mapped[str] = mapped_column(String(80))
    # person | team
    kind: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(200))
    club: Mapped[str | None] = mapped_column(String(200))
    nationality: Mapped[str | None] = mapped_column(String(80))
    hr_id: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[float | None] = mapped_column()
    rank: Mapped[int | None] = mapped_column(Integer)
    # a team's arrived lineup, person keys in order
    members: Mapped[list[str]] = mapped_column(JSON, default=list)
