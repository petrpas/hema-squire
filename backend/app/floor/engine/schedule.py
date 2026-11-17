"""List scheduling with a resource cap (spec floor-planner, Activities are
scheduled within days, pistes and precedence; design add-floor-planner D3,
design rework-floor-setup D8).

Activities are taken in priority order and each is put at the earliest start
any eligible piste allows, lowest piste ordinal first. A placement may run past
its day's end: that is how an overrun is measured, and a variant with one is
infeasible. Breaks, pistes, precedence, rest and the referees cap are never
broken.

A piste is eligible for a discipline that it serves as regular; one serving it
as reserve only on a day named in `reserve_days`, which the variants open for
a day that overruns without them.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.floor.engine.model import (
    Activity,
    Choice,
    DisciplineFacts,
    PlacePin,
    Problem,
    SequencePin,
    Stage,
)
from app.floor.engine.structure import advancing, bracket, pool_bouts, pool_sizes

# the rules a caller may lift to explain an empty result
RULES = ("finals", "rest", "officials")


@dataclass(frozen=True)
class Template:
    """An activity before it is placed."""

    id: str
    discipline: int
    kind: str
    ordinal: int
    round: int
    duration: int
    final: bool
    size: int
    # longest chain of durations from this activity to its discipline's end
    tail: int


def templates(discipline: DisciplineFacts, k: int) -> list[Template]:
    """A discipline's pools and elimination bouts for k pools. A discipline
    that takes over has no pools (k = 0)."""
    fmt = discipline.format
    key = discipline.key
    out: list[Template] = []
    team = discipline.kind == "team"
    bout = (fmt.slot_team_match or fmt.slot_elim_bout) if team else fmt.slot_elim_bout
    shape = bracket(advancing(discipline.n_bracket, None if team else fmt.advance))
    rounds = len(shape.rounds)
    elimination = rounds * bout
    sizes = pool_sizes(discipline.n_pool, k) if k > 0 and discipline.takes_from is None else ()
    for number, size in enumerate(sizes, start=1):
        duration = pool_bouts(size) * fmt.slot_pool_bout
        out.append(
            Template(
                id=f"{key}:pool:{number}",
                discipline=discipline.id,
                kind="pool",
                ordinal=number,
                round=0,
                duration=duration,
                final=False,
                size=size,
                tail=duration + fmt.pause + elimination,
            )
        )
    for index, bouts in enumerate(shape.rounds, start=1):
        last = index == rounds
        for number in range(1, bouts + 1):
            out.append(
                Template(
                    id=f"{key}:r{index}:{number}",
                    discipline=discipline.id,
                    kind="bout",
                    ordinal=number,
                    round=index,
                    duration=bout,
                    final=last,
                    size=0,
                    tail=(rounds - index + 1) * bout,
                )
            )
        if last and fmt.third_place and shape.size >= 4:
            out.append(
                Template(
                    id=f"{key}:third",
                    discipline=discipline.id,
                    kind="bout",
                    ordinal=2,
                    round=index,
                    duration=bout,
                    final=True,
                    size=0,
                    tail=bout,
                )
            )
    return out


@dataclass(frozen=True)
class Outcome:
    activities: tuple[Activity, ...]
    # (day, minutes past its end), only days that overrun
    overrun: tuple[tuple[int, int], ...]
    # the index in `Problem.pins` of a placement pin that cannot hold
    broken_pin: int | None = None
    # a discipline whose one piste needs more referees than its day has
    understaffed: int | None = None
    # reserve pistes used, by id
    reserve_used: tuple[int, ...] = ()


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def stage_of(activity_kind: str) -> Stage:
    return "pool" if activity_kind == "pool" else "elim"


class _Floor:
    """The state of a placement in progress."""

    def __init__(
        self,
        problem: Problem,
        need: Mapping[tuple[int, Stage], int],
        lifted: frozenset[str],
        reserve_days: frozenset[int],
        extra_pistes: int,
        fewer_pistes: int,
    ) -> None:
        self.problem = problem
        self.need = need
        self.placed: list[Activity] = []
        # a piste's busy spans, per day: times count from each day's midnight
        self.busy: dict[tuple[int, int], list[tuple[int, int]]] = {}
        self.capped = bool(problem.officials) and "officials" not in lifted
        self.available: dict[int, int] = {}
        for referees in problem.officials:
            open_reserve = referees.day in reserve_days
            self.available[referees.day] = referees.regular + (
                referees.reserve if open_reserve else 0
            )
        self.reserve_days = reserve_days
        ordered = sorted(problem.pistes, key=lambda p: p.ordinal)
        self.regular: dict[int, list[int]] = {}
        self.reserve: dict[int, list[int]] = {}
        for discipline in problem.disciplines:
            ids = [p.id for p in ordered if discipline.id in p.regular]
            if fewer_pistes:
                ids = ids[: max(len(ids) - fewer_pistes, 0)]
            # a hypothetical piste for sensitivity: ids no stored piste has
            ids += [-(n + 1) for n in range(extra_pistes)]
            self.regular[discipline.id] = ids
            self.reserve[discipline.id] = [
                p.id
                for p in ordered
                if discipline.id in p.reserve and discipline.id not in p.regular
            ]
        self.reserve_pistes = {p.id for p in ordered if p.reserve}
        self.days = {day.index: day for day in problem.days}

    def pistes_for(self, discipline: int, day: int) -> list[int]:
        regular = self.regular.get(discipline, [])
        if day in self.reserve_days:
            return regular + self.reserve.get(discipline, [])
        return regular

    def officials_fit(self, need: int, day: int, start: int, end: int) -> bool:
        if not self.capped or need == 0:
            return True
        limit = self.available.get(day, 0)
        running = [a for a in self.placed if a.day == day and _overlaps(a.start, a.end, start, end)]
        points = [start] + [a.start for a in running if a.start > start]
        for point in points:
            load = need + sum(
                self.need[(a.discipline, stage_of(a.kind))]
                for a in running
                if a.start <= point < a.end
            )
            if load > limit:
                return False
        return True

    def fits(self, piste: int, template: Template, day: int, start: int) -> bool:
        end = start + template.duration
        for pause in self.days[day].breaks:
            if _overlaps(start, end, pause.start, pause.end):
                return False
        for b_start, b_end in self.busy.get((piste, day), ()):
            if _overlaps(start, end, b_start, b_end):
                return False
        need = self.need[(template.discipline, stage_of(template.kind))]
        return self.officials_fit(need, day, start, end)

    def earliest(self, template: Template, day: int, ready: int) -> tuple[int, int] | None:
        """(start, piste) at the earliest start any piste allows, lowest
        ordinal first among equal starts."""
        best: tuple[int, int] | None = None
        pistes = self.pistes_for(template.discipline, day)
        day_placed_ends = [a.end for a in self.placed if a.day == day]
        breaks = [b.end for b in self.days[day].breaks]
        for order, piste in enumerate(pistes):
            candidates = sorted(
                {ready}
                | {e for _, e in self.busy.get((piste, day), ()) if e > ready}
                | {e for e in day_placed_ends if e > ready}
                | {e for e in breaks if e > ready}
            )
            for start in candidates:
                if best is not None and start >= best[0]:
                    break
                if self.fits(piste, template, day, start):
                    if best is None or start < best[0]:
                        best = (start, order)
                    break
        if best is None:
            return None
        return best[0], pistes[best[1]]

    def put(self, activity: Activity, pause: int = 0) -> None:
        """A pool keeps its piste for the pause after it."""
        self.placed.append(activity)
        tail = pause if activity.kind == "pool" else 0
        self.busy.setdefault((activity.piste, activity.day), []).append(
            (activity.start, activity.end + tail)
        )


def needs(problem: Problem) -> dict[tuple[int, Stage], int]:
    """Referees one running piste needs, by discipline and stage."""
    out: dict[tuple[int, Stage], int] = {}
    for d in problem.disciplines:
        out[(d.id, "pool")] = d.format.referees_for("pool")
        out[(d.id, "elim")] = d.format.referees_for("elim")
    return out


def schedule(
    problem: Problem,
    choices: Iterable[Choice],
    *,
    lifted: frozenset[str] = frozenset(),
    ignored_pin: int | None = None,
    reserve_days: frozenset[int] = frozenset(),
    extra_pistes: int = 0,
    fewer_pistes: int = 0,
) -> Outcome:
    """Place every activity of the chosen variant. `lifted` names hard rules
    left out, `ignored_pin` a pin left out, both only to explain an empty
    result; `reserve_days` the days whose reserve pistes and referees are
    open; `extra_pistes` and `fewer_pistes` change each discipline's piste
    count, only for sensitivity."""
    by_id = {d.id: d for d in problem.disciplines}
    chosen = {c.discipline: c for c in choices}
    need = needs(problem)
    floor = _Floor(problem, need, lifted, reserve_days, extra_pistes, fewer_pistes)
    last_day = max((day.index for day in problem.days), default=0)
    finals = "elimination" if "finals" in lifted else problem.params.finals

    # a discipline whose one piste outnumbers its day's referees never fits
    if floor.capped:
        for choice in chosen.values():
            most = max(need[(choice.discipline, "pool")], need[(choice.discipline, "elim")])
            if most > floor.available.get(choice.day, 0):
                return Outcome((), (), understaffed=choice.discipline)

    pending: dict[str, Template] = {}
    for discipline_id, choice in chosen.items():
        for template in templates(by_id[discipline_id], choice.k):
            pending[template.id] = template

    def day_of(template: Template) -> int:
        if finals == "tournament" and template.final:
            return last_day
        return chosen[template.discipline].day

    def pause_of(discipline: int) -> int:
        return by_id[discipline].format.pause

    # what has started stays where it stands
    for activity in problem.frozen:
        floor.put(activity, pause_of(activity.discipline) if activity.discipline in by_id else 0)
        pending.pop(activity.id, None)

    # placement pins hold exactly, or the variant cannot exist
    for index, pin in enumerate(problem.pins):
        if index == ignored_pin or not isinstance(pin, PlacePin):
            continue
        template = pending.get(pin.activity)
        if template is None:
            if not any(a.id == pin.activity for a in problem.frozen):
                return Outcome(tuple(floor.placed), (), broken_pin=index)
            continue
        if day_of(template) != pin.day or not floor.fits(pin.piste, template, pin.day, pin.start):
            return Outcome(tuple(floor.placed), (), broken_pin=index)
        floor.put(_activity(template, pin.piste, pin.day, pin.start), pause_of(template.discipline))
        del pending[pin.activity]

    sequence: dict[int, int] = {}
    after: dict[int, int | None] = {}
    for index, pin in enumerate(problem.pins):
        if index == ignored_pin or not isinstance(pin, SequencePin):
            continue
        listed = [d for d in pin.disciplines if d in chosen and chosen[d].day == pin.day]
        for position, discipline_id in enumerate(listed):
            sequence[discipline_id] = position
            after[discipline_id] = listed[position - 1] if position else None

    rest = 0 if "rest" in lifted else problem.params.min_rest
    finals_late = finals != "elimination"

    def priority(t: Template) -> tuple[bool, int, int, int, int, str]:
        # a taken-over discipline waits on its source: after the pools
        follows = 1 if by_id[t.discipline].takes_from is not None else 0
        return (
            finals_late and t.final,
            sequence.get(t.discipline, 0),
            t.round,
            follows,
            -t.tail,
            t.id,
        )

    for template in sorted(pending.values(), key=priority):
        day = day_of(template)
        ready = floor.days[day].start
        discipline = by_id[template.discipline]
        mine = [a for a in floor.placed if a.discipline == template.discipline]
        if template.round == 0:
            previous = after.get(template.discipline)
            if previous is not None:
                theirs = [a.end for a in floor.placed if a.discipline == previous and not a.final]
                if theirs:
                    ready = max(ready, max(theirs) + rest)
        elif template.round == 1:
            seeds_from = discipline.takes_from or discipline.id
            pools = [
                a.end
                for a in floor.placed
                if a.discipline == seeds_from and a.round == 0 and a.day == day
            ]
            if pools:
                ready = max(ready, max(pools) + rest)
        else:
            # a final moved to the last day follows its semifinals on their day
            earlier = [a.end for a in mine if a.round == template.round - 1 and a.day == day]
            if earlier:
                ready = max(ready, max(earlier))
        if finals_late and template.final:
            others = [a.end for a in floor.placed if a.day == day and not a.final]
            if others:
                ready = max(ready, max(others))
        found = floor.earliest(template, day, ready)
        if found is None:
            # no piste at all that day
            return Outcome(tuple(floor.placed), ((day, 24 * 60),))
        start, piste = found
        floor.put(_activity(template, piste, day, start), pause_of(template.discipline))

    overrun: dict[int, int] = {}
    for activity in floor.placed:
        late = activity.end - floor.days[activity.day].end
        if late > 0:
            overrun[activity.day] = max(overrun.get(activity.day, 0), late)
    placed = tuple(sorted(floor.placed, key=lambda a: (a.day, a.start, a.piste, a.id)))
    used = tuple(
        sorted(
            {
                a.piste
                for a in placed
                if a.piste in floor.reserve_pistes
                and a.piste not in floor.regular.get(a.discipline, [])
            }
        )
    )
    return Outcome(placed, tuple(sorted(overrun.items())), reserve_used=used)


def main_warnings(
    problem: Problem, activities: Iterable[Activity]
) -> tuple[tuple[int, int, int], ...]:
    """Moments where more pistes run than the day has main referees: a
    warning, never a constraint (spec floor-planner, Main referees,
    tolerated). Each is (day, minute, pistes beyond)."""
    mains = {r.day: r.main for r in problem.officials}
    if not mains:
        return ()
    placed = list(activities)
    out: list[tuple[int, int, int]] = []
    for day, available in sorted(mains.items()):
        mine = [a for a in placed if a.day == day]
        previous = 0
        for point in sorted({a.start for a in mine} | {a.end for a in mine}):
            running = len({a.piste for a in mine if a.start <= point < a.end})
            short = max(running - available, 0)
            # a run of the same shortfall is one warning, at its first moment
            if short and short != previous:
                out.append((day, point, short))
            previous = short
    return tuple(out)


def _activity(template: Template, piste: int, day: int, start: int) -> Activity:
    return Activity(
        id=template.id,
        discipline=template.discipline,
        kind="pool" if template.kind == "pool" else "bout",
        ordinal=template.ordinal,
        round=template.round,
        piste=piste,
        day=day,
        start=start,
        end=start + template.duration,
        final=template.final,
        size=template.size,
    )
