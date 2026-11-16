"""Sensitivity of the chosen variant (spec floor-planner, Sensitivity is
reported with the chosen variant)."""

from dataclasses import dataclass, replace
from typing import Literal

from app.floor.engine.model import Plan, Problem
from app.floor.engine.schedule import schedule
from app.floor.engine.structure import pool_counts

# how far from N the structure thresholds are looked for
REACH = 64


@dataclass(frozen=True)
class Threshold:
    discipline: int
    # the nearest entrant counts below and above N at which the feasible pool
    # counts change; None where none lies within reach
    below: int | None
    above: int | None


@dataclass(frozen=True)
class DayEffect:
    day: int
    # change of the day's last end, in minutes (negative is earlier); None
    # where the change leaves the day unplannable
    one_fewer: int | None
    one_more: int | None
    two_more: int | None
    limit: Literal["pistes", "officials", "none"]


@dataclass(frozen=True)
class Sensitivity:
    thresholds: tuple[Threshold, ...]
    days: tuple[DayEffect, ...]


def _last_ends(
    problem: Problem, plan: Plan, *, extra: int = 0, fewer: int = 0
) -> dict[int, int] | None:
    outcome = schedule(problem, plan.choices, extra_pistes=extra, fewer_pistes=fewer)
    if outcome.broken_pin is not None or outcome.understaffed is not None:
        return None
    return {
        day.index: max((a.end for a in outcome.activities if a.day == day.index), default=day.start)
        for day in problem.days
    }


def sensitivity(problem: Problem, plan: Plan) -> Sensitivity:
    thresholds: list[Threshold] = []
    for discipline in problem.disciplines:
        fmt = discipline.format
        n = discipline.n_pool
        here = pool_counts(n, fmt.pool_min, fmt.pool_max)
        below = next(
            (
                m
                for m in range(n - 1, max(n - REACH, 0), -1)
                if pool_counts(m, fmt.pool_min, fmt.pool_max) != here
            ),
            None,
        )
        above = next(
            (
                m
                for m in range(n + 1, n + REACH)
                if pool_counts(m, fmt.pool_min, fmt.pool_max) != here
            ),
            None,
        )
        thresholds.append(Threshold(discipline=discipline.id, below=below, above=above))

    base = {day: end for day, end in plan.metrics.last_end}
    fewer = _last_ends(problem, plan, fewer=1)
    more = _last_ends(problem, plan, extra=1)
    two = _last_ends(problem, plan, extra=2)
    # two extra pistes with officials not counted: what pistes alone would give
    unstaffed = _last_ends(replace(problem, officials=()), plan, extra=2)

    def delta(ends: dict[int, int] | None, day: int) -> int | None:
        return None if ends is None else ends[day] - base[day]

    effects: list[DayEffect] = []
    for day in problem.days:
        if not any(a.day == day.index for a in plan.activities):
            continue
        gain = delta(more, day.index)
        second = delta(two, day.index)
        free_second = delta(unstaffed, day.index)
        # what stops the piste after the next one from helping: still pistes
        # where it helps, the officials where only uncounted officials let it
        if gain is not None and second is not None and second < gain:
            limit: Literal["pistes", "officials", "none"] = "pistes"
        elif second is not None and free_second is not None and free_second < second:
            limit = "officials"
        else:
            limit = "none"
        effects.append(
            DayEffect(
                day=day.index,
                one_fewer=delta(fewer, day.index),
                one_more=gain,
                two_more=second,
                limit=limit,
            )
        )
    return Sensitivity(thresholds=tuple(thresholds), days=tuple(effects))
