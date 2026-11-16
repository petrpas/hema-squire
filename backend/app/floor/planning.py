"""The plan service (spec floor-plan; design add-floor-planner D6, D7).

Builds the engine's `Problem` from floor Setup and the roster port, runs the
engine, and stores what the organizer chooses as versions. The engine knows
minutes and day indexes; this module is where they become dates and instants
in the tournament's zone.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.floor import people, progress
from app.floor.engine.model import (
    Activity,
    Break,
    Choice,
    Day,
    DayPin,
    DisciplineFacts,
    Format,
    KPin,
    Params,
    Pin,
    Piste,
    PlacePin,
    Plan,
    Problem,
    Result,
    Role,
    SequencePin,
)
from app.floor.engine.sensitivity import Sensitivity, sensitivity
from app.floor.engine.structure import pool_sizes
from app.floor.engine.variants import evaluate
from app.floor.engine.variants import plan as run_planner
from app.floor.models import (
    FloorDay,
    FloorFormat,
    FloorOfficial,
    FloorOfficialDay,
    FloorPin,
    FloorPiste,
    FloorPisteDay,
    FloorPlan,
    FloorPlanActivity,
)
from app.floor.roster import Roster
from app.floor.setup import Tournament, read_params

ROLES: tuple[Role, ...] = ("referee", "judge", "table")


class SetupIncomplete(Exception):
    """The planner refuses a tournament floor Setup names incomplete."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(", ".join(missing))


@dataclass(frozen=True)
class Context:
    """What the service needs to turn engine output back into the world."""

    problem: Problem
    dates: tuple[date, ...]
    zone: ZoneInfo
    # disciplines left out because nobody is entered yet
    empty: tuple[int, ...]

    def index_of(self, when: date) -> int | None:
        return self.dates.index(when) if when in self.dates else None

    def instant(self, day: int, minutes: int) -> datetime:
        local = datetime.combine(self.dates[day], time()) + timedelta(minutes=minutes)
        return local.replace(tzinfo=self.zone).astimezone(UTC)

    def local(self, instant: datetime) -> tuple[date, int]:
        # SQLite hands an aware column back naive, in UTC as it was stored
        aware = instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)
        moment = aware.astimezone(self.zone)
        return moment.date(), moment.hour * 60 + moment.minute


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def clock_minutes(clock: str) -> int:
    hours, mins = clock.split(":")
    return int(hours) * 60 + int(mins)


def _counts(
    session: Session, tid: int, tournament: Tournament, roster: Roster
) -> tuple[dict[str, int], dict[str, int], dict[str, set[str]]]:
    """Per discipline slug: pool participants, bracket entrants, and who.
    Read through `people.entrants`: the roster before a discipline's
    check-in closes, its snapshot after (spec floor-planner, Which N)."""
    n_pool: dict[str, int] = {}
    n_bracket: dict[str, int] = {}
    who: dict[str, set[str]] = {}
    for discipline in tournament.disciplines:
        found = people.entrants(session, tid, roster, discipline)
        if discipline.kind == "team":
            members = [key for team in found for key in team.members]
            n_pool[discipline.slug] = len(members)
            who[discipline.slug] = set(members)
        else:
            n_pool[discipline.slug] = len(found)
            who[discipline.slug] = {e.key for e in found}
        n_bracket[discipline.slug] = len(found)
    return n_pool, n_bracket, who


def _format(row: FloorFormat) -> Format:
    staffing = row.staffing or {}
    return Format(
        pool_min=row.pool_min,
        pool_max=row.pool_max,
        advance=row.advance,
        third_place=row.third_place,
        staffing=tuple((role, int(staffing.get(role, 0))) for role in ROLES),
        slot_pool_bout=row.slot_pool_bout,
        slot_elim_bout=row.slot_elim_bout,
        slot_pool_overhead=row.slot_pool_overhead,
        slot_team_match=row.slot_team_match,
    )


def _pins(session: Session, tid: int, ctx_dates: Sequence[date]) -> tuple[Pin, ...]:
    out: list[Pin] = []
    for row in pins(session, tid):
        value = row.value
        if row.kind == "day":
            when = date.fromisoformat(str(value["day"]))
            if when in ctx_dates:
                out.append(DayPin(discipline=int(row.target), day=list(ctx_dates).index(when)))
        elif row.kind == "k":
            out.append(KPin(discipline=int(row.target), k=int(str(value["k"]))))
        elif row.kind == "place":
            when = date.fromisoformat(str(value["day"]))
            if when in ctx_dates:
                out.append(
                    PlacePin(
                        activity=row.target,
                        piste=int(str(value["piste"])),
                        day=list(ctx_dates).index(when),
                        start=clock_minutes(str(value["start"])),
                    )
                )
        elif row.kind == "n":
            # check-in's pin: N is read from the snapshot itself
            continue
        elif row.kind == "sequence":
            when = date.fromisoformat(str(value["day"]))
            listed = value.get("disciplines")
            if when in ctx_dates and isinstance(listed, list):
                out.append(
                    SequencePin(
                        day=list(ctx_dates).index(when),
                        disciplines=tuple(int(str(d)) for d in listed),
                    )
                )
    return tuple(out)


def pins(session: Session, tid: int) -> list[FloorPin]:
    return list(
        session.scalars(select(FloorPin).where(FloorPin.tournament_id == tid).order_by(FloorPin.id))
    )


def build(
    session: Session,
    tournament: Tournament,
    roster: Roster,
    *,
    replan_at: datetime | None = None,
) -> Context:
    """The engine's `Problem` for this tournament as it stands. Re-planning
    freezes what has started and lets reserve pistes in."""
    tid = tournament.id
    zone = ZoneInfo(tournament.timezone)
    day_rows = list(
        session.scalars(
            select(FloorDay).where(FloorDay.tournament_id == tid).order_by(FloorDay.date)
        )
    )
    formats = {
        row.discipline_id: row
        for row in session.scalars(select(FloorFormat).where(FloorFormat.tournament_id == tid))
    }
    piste_rows = list(session.scalars(select(FloorPiste).where(FloorPiste.tournament_id == tid)))

    missing: list[str] = []
    if not day_rows:
        missing.append("days")
    if not piste_rows:
        missing.append("pistes")
    for discipline in tournament.disciplines:
        row = formats.get(discipline.id)
        if row is None:
            missing.append(f"format:{discipline.id}")
        elif row.staffing is None:
            missing.append(f"staffing:{discipline.id}")
    if missing:
        raise SetupIncomplete(missing)

    dates = tuple(day.date for day in day_rows)
    index = {day.id: i for i, day in enumerate(day_rows)}
    days = tuple(
        Day(
            index=i,
            start=_minutes(day.start),
            end=_minutes(day.end),
            breaks=tuple(Break(clock_minutes(a), clock_minutes(b)) for a, b in day.breaks),
        )
        for i, day in enumerate(day_rows)
    )
    available: dict[int, set[int]] = {}
    for piste_id, day_id in session.execute(
        select(FloorPisteDay.piste_id, FloorPisteDay.day_id).where(
            FloorPisteDay.piste_id.in_([p.id for p in piste_rows])
        )
    ).tuples():
        available.setdefault(piste_id, set()).add(index[day_id])
    pistes = tuple(
        Piste(
            id=p.id,
            ordinal=p.ordinal,
            days=frozenset(available.get(p.id, set())),
            reserve=p.reserve,
        )
        for p in piste_rows
    )

    n_pool, n_bracket, who = _counts(session, tid, tournament, roster)
    facts: list[DisciplineFacts] = []
    empty: list[int] = []
    for discipline in tournament.disciplines:
        if n_pool.get(discipline.slug, 0) == 0:
            empty.append(discipline.id)
            continue
        facts.append(
            DisciplineFacts(
                id=discipline.id,
                key=discipline.slug,
                kind=discipline.kind,
                n_pool=n_pool[discipline.slug],
                n_bracket=n_bracket[discipline.slug],
                format=_format(formats[discipline.id]),
            )
        )
    slug_of = {d.id: d.slug for d in tournament.disciplines}
    shared: list[tuple[int, int, int]] = []
    for i, a in enumerate(facts):
        for b in facts[i + 1 :]:
            both = len(who.get(slug_of[a.id], set()) & who.get(slug_of[b.id], set()))
            if both:
                shared.append((min(a.id, b.id), max(a.id, b.id), both))

    officials: dict[tuple[int, Role], int] = {}
    official_rows = list(
        session.scalars(select(FloorOfficial).where(FloorOfficial.tournament_id == tid))
    )
    if official_rows:
        days_of: dict[int, set[int]] = {}
        for official_id, day_id in session.execute(
            select(FloorOfficialDay.official_id, FloorOfficialDay.day_id).where(
                FloorOfficialDay.official_id.in_([o.id for o in official_rows])
            )
        ).tuples():
            days_of.setdefault(official_id, set()).add(index[day_id])
        for official in official_rows:
            for day in days_of.get(official.id, set()):
                # an official counts toward each role they can fill: an upper
                # bound the officials assignment settles (design D3)
                for role in official.roles:
                    if role in ROLES:
                        key = (day, role)
                        officials[key] = officials.get(key, 0) + 1
        # a role nobody fills is a zero, not an absence
        for day in range(len(days)):
            for role in ROLES:
                officials.setdefault((day, role), 0)

    stored = read_params(session, tid)
    params = Params(
        finals_last=stored.finals_last,
        prefer_larger_pools=stored.prefer_larger_pools,
        min_rest=stored.min_rest_minutes,
    )

    frozen: tuple[Activity, ...] = ()
    held: list[Pin] = []
    context = Context(
        problem=Problem(days=(), pistes=(), disciplines=()), dates=dates, zone=zone, empty=()
    )
    if replan_at is not None:
        started = progress.started(session, tid, replan_at)
        current = published(session, tid)
        frozen = tuple(a for a in _activities(session, current, context) if a.id in started)
        # a discipline that has started keeps the pool count it started with
        moving = {a.discipline for a in frozen}
        for entry in current.variant if current is not None else []:
            discipline = int(str(entry["discipline_id"]))
            if discipline in moving:
                held.append(KPin(discipline=discipline, k=int(str(entry["k"]))))

    problem = Problem(
        days=days,
        pistes=pistes,
        disciplines=tuple(facts),
        shared=tuple(shared),
        officials=tuple((day, role, count) for (day, role), count in sorted(officials.items())),
        pins=_pins(session, tid, dates) + tuple(held),
        params=params,
        frozen=frozen,
        use_reserve=replan_at is not None,
    )
    return Context(problem=problem, dates=dates, zone=zone, empty=tuple(empty))


# ------------------------------------------------------------ versions


def working(session: Session, tid: int) -> FloorPlan | None:
    return _status(session, tid, "working")


def published(session: Session, tid: int) -> FloorPlan | None:
    return _status(session, tid, "published")


def _status(session: Session, tid: int, status: str) -> FloorPlan | None:
    return session.scalar(
        select(FloorPlan).where(FloorPlan.tournament_id == tid, FloorPlan.status == status)
    )


def history(session: Session, tid: int) -> list[FloorPlan]:
    return list(
        session.scalars(
            select(FloorPlan)
            .where(FloorPlan.tournament_id == tid, FloorPlan.status == "history")
            .order_by(FloorPlan.version.desc())
        )
    )


def _activities(session: Session, plan: FloorPlan | None, context: Context) -> list[Activity]:
    if plan is None:
        return []
    out: list[Activity] = []
    rows = session.scalars(
        select(FloorPlanActivity).where(FloorPlanActivity.plan_id == plan.id)
    ).all()
    for row in rows:
        when, start = context.local(row.starts_at)
        _, end = context.local(row.ends_at)
        day = context.index_of(when)
        if day is None:
            continue
        out.append(
            Activity(
                id=row.activity_id,
                discipline=row.discipline_id,
                kind="pool" if row.kind == "pool" else "bout",
                ordinal=row.ordinal,
                round=row.round,
                piste=row.piste_id,
                day=day,
                start=start,
                end=end,
                final=row.final,
                size=row.size,
            )
        )
    return out


def store(
    session: Session, tid: int, context: Context, chosen: Plan, author: int | None, now: datetime
) -> FloorPlan:
    """The chosen variant becomes the working version, replacing any."""
    previous = working(session, tid)
    if previous is not None:
        session.execute(delete(FloorPlanActivity).where(FloorPlanActivity.plan_id == previous.id))
        session.delete(previous)
        session.flush()
    version = (
        session.scalar(select(func.max(FloorPlan.version)).where(FloorPlan.tournament_id == tid))
        or 0
    ) + 1
    sizes = {
        c.discipline: pool_sizes(
            next(d.n_pool for d in context.problem.disciplines if d.id == c.discipline), c.k
        )
        for c in chosen.choices
    }
    row = FloorPlan(
        tournament_id=tid,
        version=version,
        status="working",
        variant=[
            {
                "discipline_id": c.discipline,
                "k": c.k,
                "day": context.dates[c.day].isoformat(),
                "sizes": list(sizes[c.discipline]),
            }
            for c in chosen.choices
        ],
        metrics=metrics_json(context, chosen),
        exclusions=[
            {
                "a": e.a,
                "b": e.b,
                "parallel_waves": list(e.parallel_waves),
                "shared": e.shared,
                "free_places": e.free_places,
            }
            for e in chosen.exclusions
        ],
        collisions=[
            {"a": c.a, "round_a": c.round_a, "b": c.b, "round_b": c.round_b}
            for c in chosen.collisions
        ],
        created_at=now,
        created_by=author,
    )
    session.add(row)
    session.flush()
    for activity in chosen.activities:
        session.add(
            FloorPlanActivity(
                plan_id=row.id,
                activity_id=activity.id,
                discipline_id=activity.discipline,
                kind=activity.kind,
                ordinal=activity.ordinal,
                round=activity.round,
                piste_id=activity.piste,
                starts_at=context.instant(activity.day, activity.start),
                ends_at=context.instant(activity.day, activity.end),
                final=activity.final,
                size=activity.size,
            )
        )
    session.flush()
    return row


def clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def metrics_json(context: Context, chosen: Plan) -> dict[str, object]:
    m = chosen.metrics
    return {
        "last_end": {context.dates[day].isoformat(): clock(end) for day, end in m.last_end},
        "exclusion_load": m.exclusion_load,
        "collisions": m.collisions,
        "shortage": m.shortage,
        "average_pool": m.average_pool,
    }


def obstacles(session: Session, tournament: Tournament, plan: FloorPlan) -> list[str]:
    """What stands in the way of publishing (spec floor-plan, Publishing is a
    gate with its obstacles listed)."""
    found: list[str] = []
    formats = {
        row.discipline_id: row
        for row in session.scalars(
            select(FloorFormat).where(FloorFormat.tournament_id == tournament.id)
        )
    }
    for discipline in tournament.disciplines:
        if discipline.id not in formats:
            found.append(f"format:{discipline.id}")
    used_days = {str(choice["day"]) for choice in plan.variant}
    day_rows = session.scalars(select(FloorDay).where(FloorDay.tournament_id == tournament.id))
    for day in day_rows:
        if day.date.isoformat() not in used_days:
            continue
        has_piste = session.scalar(
            select(FloorPisteDay.piste_id)
            .join(FloorPiste, FloorPiste.id == FloorPisteDay.piste_id)
            .where(FloorPisteDay.day_id == day.id, FloorPiste.reserve.is_(False))
        )
        if has_piste is None:
            found.append(f"no_piste:{day.date.isoformat()}")
    for entry in plan.exclusions:
        if int(str(entry["shared"])) > int(str(entry["free_places"])):
            # one side short is enough only if the other is short too
            other = next(
                (e for e in plan.exclusions if e["a"] == entry["b"] and e["b"] == entry["a"]),
                None,
            )
            if other is None or int(str(other["shared"])) > int(str(other["free_places"])):
                pair = sorted((int(str(entry["a"])), int(str(entry["b"]))))
                key = f"shortage:{pair[0]}:{pair[1]}"
                if key not in found:
                    found.append(key)
    return found


def publish(session: Session, tid: int) -> FloorPlan:
    plan = working(session, tid)
    if plan is None:
        raise LookupError("no working version")
    previous = published(session, tid)
    if previous is not None:
        previous.status = "history"
        session.flush()
    plan.status = "published"
    session.flush()
    return plan


@dataclass(frozen=True)
class Change:
    activity: str
    kind: str  # moved | added | removed
    before: tuple[int, str, str] | None  # piste, date, "HH:MM"
    after: tuple[int, str, str] | None


def diff(session: Session, context: Context, tid: int) -> list[Change]:
    """The working version against the published one, by activity id."""
    work, pub = working(session, tid), published(session, tid)
    if work is None or pub is None:
        return []
    old = {a.id: a for a in _activities(session, pub, context)}
    new = {a.id: a for a in _activities(session, work, context)}

    def where(a: Activity) -> tuple[int, str, str]:
        return (a.piste, context.dates[a.day].isoformat(), clock(a.start))

    out: list[Change] = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        if before is None and after is not None:
            out.append(Change(key, "added", None, where(after)))
        elif after is None and before is not None:
            out.append(Change(key, "removed", where(before), None))
        elif before is not None and after is not None and where(before) != where(after):
            out.append(Change(key, "moved", where(before), where(after)))
    return out


def run(context: Context) -> Result:
    return run_planner(context.problem)


def sensitivity_of(session: Session, context: Context, tid: int) -> Sensitivity | None:
    """Sensitivity of the working version, scheduled again from its choices."""
    plan = working(session, tid) or published(session, tid)
    if plan is None:
        return None
    choices: list[Choice] = []
    for entry in plan.variant:
        day = context.index_of(date.fromisoformat(str(entry["day"])))
        discipline = int(str(entry["discipline_id"]))
        if day is None or not any(d.id == discipline for d in context.problem.disciplines):
            return None
        choices.append(Choice(discipline=discipline, k=int(str(entry["k"])), day=day))
    chosen = evaluate(context.problem, choices)
    return None if chosen is None else sensitivity(context.problem, chosen)


# ------------------------------------------------------------ answers


def choices_json(context: Context, chosen: Plan) -> list[dict[str, object]]:
    sizes = {d.id: d.n_pool for d in context.problem.disciplines}
    return [
        {
            "discipline_id": c.discipline,
            "k": c.k,
            "day": context.dates[c.day].isoformat(),
            "sizes": list(pool_sizes(sizes[c.discipline], c.k)),
        }
        for c in chosen.choices
    ]


def activity_json(context: Context, a: Activity) -> dict[str, object]:
    return {
        "id": a.id,
        "discipline_id": a.discipline,
        "kind": a.kind,
        "ordinal": a.ordinal,
        "round": a.round,
        "piste_id": a.piste,
        "day": context.dates[a.day].isoformat(),
        "start": clock(a.start),
        "end": clock(a.end),
        "final": a.final,
        "size": a.size,
    }


def variant_json(context: Context, chosen: Plan) -> dict[str, object]:
    return {
        "key": chosen.key,
        "choices": choices_json(context, chosen),
        "metrics": metrics_json(context, chosen),
        "exclusions": [
            {
                "a": e.a,
                "b": e.b,
                "parallel_waves": list(e.parallel_waves),
                "shared": e.shared,
                "free_places": e.free_places,
            }
            for e in chosen.exclusions
        ],
        "collisions": [
            {"a": c.a, "round_a": c.round_a, "b": c.b, "round_b": c.round_b}
            for c in chosen.collisions
        ],
        "activities": [activity_json(context, a) for a in chosen.activities],
    }


def stored_json(session: Session, context: Context, plan: FloorPlan | None) -> dict | None:
    if plan is None:
        return None
    return {
        "version": plan.version,
        "status": plan.status,
        "created_at": plan.created_at,
        "choices": plan.variant,
        "metrics": plan.metrics,
        "exclusions": plan.exclusions,
        "collisions": plan.collisions,
        "activities": [
            activity_json(context, a)
            for a in sorted(
                _activities(session, plan, context), key=lambda a: (a.day, a.start, a.piste)
            )
        ],
    }


def infeasible_json(context: Context, result: Result) -> dict[str, object] | None:
    found = result.infeasible
    if found is None:
        return None
    subject: object = found.subject
    if found.reason == "pin" and found.subject.isdigit():
        index = int(found.subject)
        pin = context.problem.pins[index] if index < len(context.problem.pins) else None
        subject = _pin_label(context, pin)
    return {
        "reason": found.reason,
        "subject": subject,
        "minutes": found.minutes,
        "detail": found.detail,
    }


def _pin_label(context: Context, pin: Pin | None) -> dict[str, object]:
    if isinstance(pin, DayPin):
        return {
            "kind": "day",
            "target": str(pin.discipline),
            "day": context.dates[pin.day].isoformat(),
        }
    if isinstance(pin, KPin):
        return {"kind": "k", "target": str(pin.discipline), "k": pin.k}
    if isinstance(pin, PlacePin):
        return {"kind": "place", "target": pin.activity}
    if isinstance(pin, SequencePin):
        return {"kind": "sequence", "target": ",".join(str(d) for d in pin.disciplines)}
    return {"kind": "unknown", "target": ""}


def sensitivity_json(context: Context, found: Sensitivity | None) -> dict[str, object] | None:
    if found is None:
        return None
    return {
        "thresholds": [
            {"discipline_id": t.discipline, "below": t.below, "above": t.above}
            for t in found.thresholds
        ],
        "days": [
            {
                "day": context.dates[e.day].isoformat(),
                "one_fewer": e.one_fewer,
                "one_more": e.one_more,
                "two_more": e.two_more,
                "limit": e.limit,
            }
            for e in found.days
        ],
    }


def pin_errors(
    session: Session, tournament: Tournament, kind: str, target: str, value: dict[str, object]
) -> list[dict]:
    """What is wrong with a pin before it is stored, field by field."""
    errors: list[dict] = []
    disciplines = {str(d.id) for d in tournament.disciplines}
    dates = {
        d.isoformat()
        for d in session.scalars(
            select(FloorDay.date).where(FloorDay.tournament_id == tournament.id)
        )
    }
    if kind in ("day", "k") and target not in disciplines:
        errors.append({"field": "target", "code": "unknown_discipline"})
    if kind in ("day", "place", "sequence") and str(value.get("day")) not in dates:
        errors.append({"field": "value.day", "code": "unknown_day"})
    if kind == "k" and not (isinstance(value.get("k"), int) and int(str(value["k"])) >= 1):
        errors.append({"field": "value.k", "code": "invalid"})
    if kind == "place":
        pistes = {
            p
            for p in session.scalars(
                select(FloorPiste.id).where(FloorPiste.tournament_id == tournament.id)
            )
        }
        if value.get("piste") not in pistes:
            errors.append({"field": "value.piste", "code": "unknown_piste"})
        start = value.get("start")
        if not (isinstance(start, str) and len(start) == 5 and start[2] == ":"):
            errors.append({"field": "value.start", "code": "invalid"})
    if kind == "sequence":
        listed = value.get("disciplines")
        if not (
            isinstance(listed, list)
            and len(listed) >= 2
            and all(str(d) in disciplines for d in listed)
        ):
            errors.append({"field": "value.disciplines", "code": "unknown_discipline"})
    existing = [
        p
        for p in pins(session, tournament.id)
        if p.kind == kind and p.target == target and kind in ("day", "k", "place")
    ]
    if existing:
        errors.append({"field": "target", "code": "duplicate"})
    return errors
