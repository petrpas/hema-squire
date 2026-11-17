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
    Referees,
)


def fmt(
    lo: int = 5,
    hi: int = 7,
    *,
    advance: int | None = None,
    third: bool = False,
    referees: tuple[int, int] = (1, 1),
    pool_bout: int = 4,
    elim_bout: int = 6,
    pause: int = 5,
    team_match: int | None = None,
) -> Format:
    return Format(
        pool_min=lo,
        pool_max=hi,
        advance=advance,
        third_place=third,
        referees=referees,
        slot_pool_bout=pool_bout,
        slot_elim_bout=elim_bout,
        pause=pause,
        slot_team_match=team_match,
    )


def discipline(
    id: int,
    n: int,
    *,
    key: str | None = None,
    format: Format | None = None,
    day: int = 0,
    takes_from: int | None = None,
) -> DisciplineFacts:
    return DisciplineFacts(
        id=id,
        key=key or f"D{id}",
        kind="individual",
        n_pool=n,
        n_bracket=n,
        format=format or fmt(),
        day=day,
        takes_from=takes_from,
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


def pistes(count: int, serves: tuple[int, ...], *, reserve: int = 0) -> tuple[Piste, ...]:
    """`count` pistes serving every discipline in `serves`; the last
    `reserve` of them serve as reserve only."""
    every = frozenset(serves)
    return tuple(
        Piste(
            id=n,
            ordinal=n,
            regular=frozenset() if n > count - reserve else every,
            reserve=every if n > count - reserve else frozenset(),
        )
        for n in range(1, count + 1)
    )


def problem(
    *disciplines: DisciplineFacts,
    days: tuple[Day, ...] | None = None,
    piste_count: int = 4,
    reserve: int = 0,
    shared: tuple[tuple[int, int, int], ...] = (),
    officials: tuple[Referees, ...] = (),
    pins: tuple[Pin, ...] = (),
    params: Params | None = None,
    schedule: bool = True,
) -> Problem:
    chosen_days = days or (day(),)
    return Problem(
        days=chosen_days,
        pistes=pistes(piste_count, tuple(d.id for d in disciplines), reserve=reserve),
        disciplines=disciplines,
        shared=shared,
        officials=officials,
        pins=pins,
        params=params or Params(),
        schedule=schedule,
    )
