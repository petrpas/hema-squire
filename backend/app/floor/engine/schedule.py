"""List scheduling with a resource cap (spec floor-planner, Activities are
scheduled within days, pistes and precedence; design add-floor-planner D3).

Activities are taken in priority order and each is put at the earliest start
any eligible piste allows, lowest piste ordinal first. A placement may run past
its day's end: that is how an overrun is measured, and a variant with one is
infeasible. Breaks, pistes, precedence, rest and the officials cap are never
broken.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.floor.engine.model import (
    Activity,
    Choice,
    DisciplineFacts,
    PlacePin,
    Problem,
    Role,
    SequencePin,
)
from app.floor.engine.structure import advancing, bracket, pool_bouts, pool_sizes

# the rules a caller may lift to explain an empty result
RULES = ("finals_last", "rest", "officials")


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
    """A discipline's pools and elimination bouts for k pools."""
    fmt = discipline.format
    key = discipline.key
    out: list[Template] = []
    team = discipline.kind == "team"
    bout = (fmt.slot_team_match or fmt.slot_elim_bout) if team else fmt.slot_elim_bout
    shape = bracket(advancing(discipline.n_bracket, None if team else fmt.advance))
    rounds = len(shape.rounds)
    elimination = rounds * bout
    for number, size in enumerate(pool_sizes(discipline.n_pool, k), start=1):
        duration = pool_bouts(size) * fmt.slot_pool_bout + fmt.slot_pool_overhead
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
                tail=duration + elimination,
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
    # a discipline whose one piste needs more officials than its day has
    understaffed: int | None = None


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


class _Floor:
    """The state of a placement in progress."""

    def __init__(
        self,
        problem: Problem,
        need: Mapping[int, Mapping[Role, int]],
        lifted: frozenset[str],
        extra_pistes: int,
        fewer_pistes: int,
    ) -> None:
        self.problem = problem
        self.need = need
        self.lifted = lifted
        self.placed: list[Activity] = []
        # a piste's busy spans, per day: times count from each day's midnight
        self.busy: dict[tuple[int, int], list[tuple[int, int]]] = {}
        available: dict[tuple[int, Role], int] = {}
        for day, role, count in problem.officials:
            available[(day, role)] = available.get((day, role), 0) + count
        self.available = available
        self.capped = bool(problem.officials) and "officials" not in lifted
        self.pistes_by_day: dict[int, list[int]] = {}
        for day in problem.days:
            usable = sorted(
                (
                    p
                    for p in problem.pistes
                    if day.index in p.days and (problem.use_reserve or not p.reserve)
                ),
                key=lambda p: p.ordinal,
            )
            ids = [p.id for p in usable]
            if fewer_pistes:
                ids = ids[: max(len(ids) - fewer_pistes, 0)]
            # a hypothetical piste for sensitivity: ids no stored piste has
            ids += [-(n + 1) for n in range(extra_pistes)]
            self.pistes_by_day[day.index] = ids
        self.days = {day.index: day for day in problem.days}

    def officials_fit(self, discipline: int, day: int, start: int, end: int) -> bool:
        if not self.capped:
            return True
        running = [a for a in self.placed if a.day == day and _overlaps(a.start, a.end, start, end)]
        points = [start] + [a.start for a in running if a.start > start]
        for role, count in self.need[discipline].items():
            if count == 0:
                continue
            limit = self.available.get((day, role), 0)
            for point in points:
                load = count + sum(
                    self.need[a.discipline].get(role, 0)
                    for a in running
                    if a.start <= point < a.end
                )
                if load > limit:
                    return False
        return True

    def fits(self, piste: int, discipline: int, day: int, start: int, duration: int) -> bool:
        end = start + duration
        for pause in self.days[day].breaks:
            if _overlaps(start, end, pause.start, pause.end):
                return False
        for b_start, b_end in self.busy.get((piste, day), ()):
            if _overlaps(start, end, b_start, b_end):
                return False
        return self.officials_fit(discipline, day, start, end)

    def earliest(self, template: Template, day: int, ready: int) -> tuple[int, int] | None:
        """(start, piste) at the earliest start any piste allows, lowest
        ordinal first among equal starts."""
        best: tuple[int, int] | None = None
        day_placed_ends = [a.end for a in self.placed if a.day == day]
        breaks = [b.end for b in self.days[day].breaks]
        for order, piste in enumerate(self.pistes_by_day[day]):
            candidates = sorted(
                {ready}
                | {e for _, e in self.busy.get((piste, day), ()) if e > ready}
                | {e for e in day_placed_ends if e > ready}
                | {e for e in breaks if e > ready}
            )
            for start in candidates:
                if best is not None and start >= best[0]:
                    break
                if self.fits(piste, template.discipline, day, start, template.duration):
                    if best is None or start < best[0]:
                        best = (start, order)
                    break
        if best is None:
            return None
        return best[0], self.pistes_by_day[day][best[1]]

    def put(self, activity: Activity) -> None:
        self.placed.append(activity)
        self.busy.setdefault((activity.piste, activity.day), []).append(
            (activity.start, activity.end)
        )


def need_of(discipline: DisciplineFacts) -> dict[Role, int]:
    return {role: count for role, count in discipline.format.staffing}


def schedule(
    problem: Problem,
    choices: Iterable[Choice],
    *,
    lifted: frozenset[str] = frozenset(),
    ignored_pin: int | None = None,
    extra_pistes: int = 0,
    fewer_pistes: int = 0,
) -> Outcome:
    """Place every activity of the chosen variant. `lifted` names hard rules
    left out, `ignored_pin` a pin left out, both only to explain an empty
    result; `extra_pistes` and `fewer_pistes` change the piste count on every
    day, only for sensitivity."""
    by_id = {d.id: d for d in problem.disciplines}
    chosen = {c.discipline: c for c in choices}
    need = {d.id: need_of(d) for d in problem.disciplines}
    floor = _Floor(problem, need, lifted, extra_pistes, fewer_pistes)

    # a discipline whose one piste outnumbers its day's officials never fits
    if floor.capped:
        for choice in chosen.values():
            for role, count in need[choice.discipline].items():
                if count > floor.available.get((choice.day, role), 0):
                    return Outcome((), (), understaffed=choice.discipline)

    pending: dict[str, Template] = {}
    for discipline_id, choice in chosen.items():
        for template in templates(by_id[discipline_id], choice.k):
            pending[template.id] = template

    # what has started stays where it stands
    for activity in problem.frozen:
        floor.put(activity)
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
        if chosen[template.discipline].day != pin.day or not floor.fits(
            pin.piste, template.discipline, pin.day, pin.start, template.duration
        ):
            return Outcome(tuple(floor.placed), (), broken_pin=index)
        floor.put(_activity(template, pin.piste, pin.day, pin.start))
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
    finals_last = problem.params.finals_last and "finals_last" not in lifted

    def priority(t: Template) -> tuple[bool, int, int, int, str]:
        return (finals_last and t.final, sequence.get(t.discipline, 0), t.round, -t.tail, t.id)

    for template in sorted(pending.values(), key=priority):
        day = chosen[template.discipline].day
        ready = floor.days[day].start
        mine = [a for a in floor.placed if a.discipline == template.discipline]
        if template.round == 0:
            previous = after.get(template.discipline)
            if previous is not None:
                theirs = [a.end for a in floor.placed if a.discipline == previous and not a.final]
                if theirs:
                    ready = max(ready, max(theirs) + rest)
        elif template.round == 1:
            pools = [a.end for a in mine if a.round == 0]
            if pools:
                ready = max(ready, max(pools) + rest)
        else:
            earlier = [a.end for a in mine if a.round == template.round - 1]
            if earlier:
                ready = max(ready, max(earlier))
        if finals_last and template.final:
            others = [a.end for a in floor.placed if a.day == day and not a.final]
            if others:
                ready = max(ready, max(others))
        found = floor.earliest(template, day, ready)
        if found is None:
            # no piste at all that day
            return Outcome(tuple(floor.placed), ((day, 24 * 60),))
        start, piste = found
        floor.put(_activity(template, piste, day, start))

    overrun: dict[int, int] = {}
    for activity in floor.placed:
        late = activity.end - floor.days[activity.day].end
        if late > 0:
            overrun[activity.day] = max(overrun.get(activity.day, 0), late)
    placed = tuple(sorted(floor.placed, key=lambda a: (a.day, a.start, a.piste, a.id)))
    return Outcome(placed, tuple(sorted(overrun.items())))


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
