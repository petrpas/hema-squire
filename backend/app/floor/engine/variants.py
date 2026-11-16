"""Variants: enumerate the free decisions, schedule each, keep the
non-dominated, order them by preference, and say why when none is left (spec
floor-planner; design add-floor-planner D4, D5)."""

import itertools
from collections.abc import Sequence

from app.floor.engine.model import (
    Activity,
    Choice,
    Collision,
    DayPin,
    DisciplineFacts,
    Exclusion,
    Infeasible,
    KPin,
    Metrics,
    Plan,
    Problem,
    Result,
)
from app.floor.engine.schedule import RULES, Outcome, schedule
from app.floor.engine.structure import pool_counts

CAP = 2000


def _k_choices(
    problem: Problem, discipline: DisciplineFacts, ignored_pin: int | None
) -> tuple[int, ...]:
    fmt = discipline.format
    feasible = pool_counts(discipline.n_pool, fmt.pool_min, fmt.pool_max)
    for index, pin in enumerate(problem.pins):
        if index != ignored_pin and isinstance(pin, KPin) and pin.discipline == discipline.id:
            return tuple(k for k in feasible if k == pin.k)
    return feasible


def _day_choices(
    problem: Problem, discipline: DisciplineFacts, ignored_pin: int | None
) -> tuple[int, ...]:
    frozen_days = {a.day for a in problem.frozen if a.discipline == discipline.id}
    if frozen_days:
        return tuple(sorted(frozen_days))
    for index, pin in enumerate(problem.pins):
        if index != ignored_pin and isinstance(pin, DayPin) and pin.discipline == discipline.id:
            return (pin.day,)
    usable = {
        day
        for piste in problem.pistes
        if problem.use_reserve or not piste.reserve
        for day in piste.days
    }
    return tuple(day.index for day in problem.days if day.index in usable)


def _preferred(ks: Sequence[int], prefer_larger: bool) -> int:
    return ks[0] if prefer_larger else ks[-1]


def _space(problem: Problem, ignored_pin: int | None) -> tuple[list[list[Choice]], tuple[int, ...]]:
    """Each discipline's options, and the disciplines the cap fixed."""
    options: dict[int, list[Choice]] = {}
    ks: dict[int, tuple[int, ...]] = {}
    days: dict[int, tuple[int, ...]] = {}
    for discipline in problem.disciplines:
        ks[discipline.id] = _k_choices(problem, discipline, ignored_pin)
        days[discipline.id] = _day_choices(problem, discipline, ignored_pin)
    capped: list[int] = []

    def size() -> int:
        total = 1
        for d in problem.disciplines:
            total *= max(len(ks[d.id]) * len(days[d.id]), 1)
        return total

    # fix the disciplines with the fewest k choices first, one at a time
    for discipline in sorted(problem.disciplines, key=lambda d: (len(ks[d.id]), d.id)):
        if size() <= CAP:
            break
        if len(ks[discipline.id]) > 1:
            ks[discipline.id] = (_preferred(ks[discipline.id], problem.params.prefer_larger_pools),)
            capped.append(discipline.id)
    # and then, if it must be, the days, first day first
    for discipline in problem.disciplines:
        if size() <= CAP:
            break
        if len(days[discipline.id]) > 1:
            days[discipline.id] = days[discipline.id][:1]
            capped.append(discipline.id)
    for discipline in problem.disciplines:
        options[discipline.id] = [
            Choice(discipline=discipline.id, k=k, day=day)
            for day in days[discipline.id]
            for k in ks[discipline.id]
        ]
    return [options[d.id] for d in problem.disciplines], tuple(capped)


# ------------------------------------------------------------ waves and metrics


def waves(activities: Sequence[Activity], discipline: int) -> dict[str, int]:
    """Each pool's wave: how many pools of its discipline ran on its piste
    before it, from 1. Derived from placement, not from the clock alone."""
    counted: dict[int, int] = {}
    out: dict[str, int] = {}
    pools = sorted(
        (a for a in activities if a.discipline == discipline and a.kind == "pool"),
        key=lambda a: (a.start, a.piste),
    )
    for pool in pools:
        counted[pool.piste] = counted.get(pool.piste, 0) + 1
        out[pool.id] = counted[pool.piste]
    return out


def _overlap(a: Activity, b: Activity) -> bool:
    return a.day == b.day and a.start < b.end and b.start < a.end


def exclusions(problem: Problem, activities: Sequence[Activity]) -> tuple[Exclusion, ...]:
    out: list[Exclusion] = []
    for a_id, b_id, shared in problem.shared:
        if shared <= 0:
            continue
        for a, b in ((a_id, b_id), (b_id, a_id)):
            wave_of = waves(activities, a)
            theirs = [x for x in activities if x.discipline == b]
            parallel = sorted(
                {
                    wave_of[pool.id]
                    for pool in activities
                    if pool.id in wave_of and any(_overlap(pool, other) for other in theirs)
                }
            )
            if not parallel:
                continue
            free = sum(
                pool.size
                for pool in activities
                if pool.id in wave_of and wave_of[pool.id] not in parallel
            )
            out.append(
                Exclusion(a=a, b=b, parallel_waves=tuple(parallel), shared=shared, free_places=free)
            )
    return tuple(out)


def collisions(problem: Problem, activities: Sequence[Activity]) -> tuple[Collision, ...]:
    out: set[Collision] = set()
    for a_id, b_id, shared in problem.shared:
        if shared <= 0:
            continue
        ours = [x for x in activities if x.discipline == a_id and x.kind == "bout"]
        theirs = [x for x in activities if x.discipline == b_id and x.kind == "bout"]
        for x in ours:
            for y in theirs:
                if _overlap(x, y):
                    out.add(Collision(a=a_id, round_a=x.round, b=b_id, round_b=y.round))
    return tuple(sorted(out, key=lambda c: (c.a, c.round_a, c.b, c.round_b)))


def _shortage(found: Sequence[Exclusion]) -> int:
    """Per pair, the persons that fit outside neither discipline's parallel
    waves: the smaller deficit, since either side may take them."""
    by_pair: dict[tuple[int, int], list[int]] = {}
    for e in found:
        pair = (min(e.a, e.b), max(e.a, e.b))
        by_pair.setdefault(pair, []).append(max(e.shared - e.free_places, 0))
    total = 0
    for deficits in by_pair.values():
        # a pair with one side not parallel at all has no deficit
        total += min(deficits) if len(deficits) == 2 else 0
    return total


def _plan(problem: Problem, choices: Sequence[Choice], outcome: Outcome) -> Plan:
    activities = outcome.activities
    found = exclusions(problem, activities)
    clash = collisions(problem, activities)
    last_end = tuple(
        (day.index, max((a.end for a in activities if a.day == day.index), default=day.start))
        for day in problem.days
    )
    load_pairs = {(min(e.a, e.b), max(e.a, e.b)): e.shared for e in found}
    pools = [a.size for a in activities if a.kind == "pool"]
    metrics = Metrics(
        last_end=last_end,
        exclusion_load=sum(load_pairs.values()),
        collisions=len(clash),
        shortage=_shortage(found),
        average_pool=round(sum(pools) / len(pools), 3) if pools else 0.0,
    )
    return Plan(
        choices=tuple(choices),
        activities=activities,
        metrics=metrics,
        exclusions=found,
        collisions=clash,
    )


def _criteria(plan: Plan) -> tuple[int, ...]:
    return (
        *(end for _, end in plan.metrics.last_end),
        plan.metrics.exclusion_load,
        plan.metrics.collisions,
    )


def _dominates(x: Plan, y: Plan) -> bool:
    cx, cy = _criteria(x), _criteria(y)
    return all(a <= b for a, b in zip(cx, cy, strict=True)) and cx != cy


def pareto(plans: Sequence[Plan]) -> list[Plan]:
    return [p for p in plans if not any(_dominates(q, p) for q in plans if q is not p)]


def _order(plan: Plan, prefer_larger: bool) -> tuple[float, ...]:
    m = plan.metrics
    total_end = float(sum(end for _, end in m.last_end))
    larger = -m.average_pool if prefer_larger else 0.0
    return (larger, total_end, float(m.exclusion_load), float(m.collisions))


# ------------------------------------------------------------ the entry point


def _feasible(
    problem: Problem,
    *,
    lifted: frozenset[str] = frozenset(),
    ignored_pin: int | None = None,
    stop_at_first: bool = False,
) -> tuple[list[Plan], tuple[int, ...], int]:
    """The feasible plans, the capped disciplines, and the least overrun met."""
    options, capped = _space(problem, ignored_pin)
    plans: list[Plan] = []
    least_overrun = 0
    if any(not choices for choices in options):
        return [], capped, least_overrun
    for combination in itertools.product(*options):
        outcome = schedule(problem, combination, lifted=lifted, ignored_pin=ignored_pin)
        if outcome.broken_pin is not None or outcome.understaffed is not None:
            continue
        if outcome.overrun:
            worst = max(minutes for _, minutes in outcome.overrun)
            least_overrun = worst if least_overrun == 0 else min(least_overrun, worst)
            continue
        plans.append(_plan(problem, combination, outcome))
        if stop_at_first:
            break
    return plans, capped, least_overrun


def evaluate(problem: Problem, choices: Sequence[Choice]) -> Plan | None:
    """One stated variant, scheduled; None where it cannot be held."""
    outcome = schedule(problem, choices)
    if outcome.broken_pin is not None or outcome.understaffed is not None or outcome.overrun:
        return None
    return _plan(problem, choices, outcome)


def plan(problem: Problem) -> Result:
    """Every non-dominated variant, ordered by preference; or why there is none."""
    plans, capped, least_overrun = _feasible(problem)
    if plans:
        kept = sorted(
            pareto(plans), key=lambda p: (*_order(p, problem.params.prefer_larger_pools), p.key)
        )
        return Result(variants=tuple(kept), capped=capped)
    return Result(variants=(), infeasible=_explain(problem, least_overrun), capped=capped)


def _explain(problem: Problem, least_overrun: int) -> Infeasible:
    # a discipline whose structure alone cannot fit is named before any pin
    for discipline in problem.disciplines:
        fmt = discipline.format
        if not pool_counts(discipline.n_pool, fmt.pool_min, fmt.pool_max):
            return Infeasible(
                reason="structure",
                subject=str(discipline.id),
                detail=f"N={discipline.n_pool} {fmt.pool_min}-{fmt.pool_max}",
            )
    for index in range(len(problem.pins)):
        found, _, _ = _feasible(problem, ignored_pin=index, stop_at_first=True)
        if found:
            return Infeasible(reason="pin", subject=str(index))
    for rule in RULES:
        found, _, _ = _feasible(problem, lifted=frozenset({rule}), stop_at_first=True)
        if found:
            return Infeasible(reason="rule", subject=rule)
    return Infeasible(reason="overrun", subject="", minutes=least_overrun)
