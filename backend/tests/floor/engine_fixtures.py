"""Builders for the planner engine's tests: a Problem in a few lines."""

from app.floor.engine.model import (
    Break,
    Day,
    DisciplineFacts,
    Format,
    Params,
    Pin,
    Piste,
    Problem,
    Role,
)


def fmt(
    lo: int = 5,
    hi: int = 7,
    *,
    advance: int | None = None,
    third: bool = False,
    staffing: tuple[tuple[Role, int], ...] = (("referee", 1),),
    pool_bout: int = 4,
    elim_bout: int = 6,
    overhead: int = 5,
    team_match: int | None = None,
) -> Format:
    return Format(
        pool_min=lo,
        pool_max=hi,
        advance=advance,
        third_place=third,
        staffing=staffing,
        slot_pool_bout=pool_bout,
        slot_elim_bout=elim_bout,
        slot_pool_overhead=overhead,
        slot_team_match=team_match,
    )


def discipline(
    id: int, n: int, *, key: str | None = None, format: Format | None = None
) -> DisciplineFacts:
    return DisciplineFacts(
        id=id,
        key=key or f"D{id}",
        kind="individual",
        n_pool=n,
        n_bracket=n,
        format=format or fmt(),
    )


def day(index: int = 0, start: str = "09:00", end: str = "19:00", *breaks: tuple[str, str]) -> Day:
    return Day(
        index=index,
        start=minutes(start),
        end=minutes(end),
        breaks=tuple(Break(minutes(a), minutes(b)) for a, b in breaks),
    )


def minutes(clock: str) -> int:
    hours, mins = clock.split(":")
    return int(hours) * 60 + int(mins)


def pistes(count: int, days: tuple[int, ...] = (0,), *, reserve: int = 0) -> tuple[Piste, ...]:
    return tuple(
        Piste(id=n, ordinal=n, days=frozenset(days), reserve=n > count - reserve)
        for n in range(1, count + 1)
    )


def problem(
    *disciplines: DisciplineFacts,
    days: tuple[Day, ...] | None = None,
    piste_count: int = 4,
    shared: tuple[tuple[int, int, int], ...] = (),
    officials: tuple[tuple[int, Role, int], ...] = (),
    pins: tuple[Pin, ...] = (),
    params: Params | None = None,
) -> Problem:
    chosen_days = days or (day(),)
    return Problem(
        days=chosen_days,
        pistes=pistes(piste_count, tuple(d.index for d in chosen_days)),
        disciplines=disciplines,
        shared=shared,
        officials=officials,
        pins=pins,
        params=params or Params(),
    )
