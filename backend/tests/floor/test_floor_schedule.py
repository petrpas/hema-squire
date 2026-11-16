"""Scheduling (spec floor-planner, Activities are scheduled within days,
pistes and precedence). No database."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.floor.engine.model import Activity, Choice, Params, Problem
from app.floor.engine.schedule import schedule
from app.floor.engine.structure import pool_counts
from tests.floor.engine_fixtures import day, discipline, fmt, minutes, pistes, problem


def overlapping(a: Activity, b: Activity) -> bool:
    return a.day == b.day and a.start < b.end and b.start < a.end


def check_invariants(problem: Problem, activities: tuple[Activity, ...]) -> None:
    days = {d.index: d for d in problem.days}
    reserve = {p.id for p in problem.pistes if p.reserve}
    rest = problem.params.min_rest
    for i, a in enumerate(activities):
        d = days[a.day]
        assert a.start >= d.start
        for pause in d.breaks:
            assert not (a.start < pause.end and pause.start < a.end), a.id
        assert a.piste not in reserve, a.id
        for b in activities[i + 1 :]:
            if a.piste == b.piste:
                assert not overlapping(a, b), (a.id, b.id)
    for d in problem.disciplines:
        mine = [a for a in activities if a.discipline == d.id]
        pools = [a for a in mine if a.round == 0]
        for bout in (a for a in mine if a.round >= 1):
            if bout.round == 1:
                assert bout.start >= max(p.end for p in pools) + rest, bout.id
            else:
                earlier = [a.end for a in mine if a.round == bout.round - 1]
                assert bout.start >= max(earlier), bout.id
    if problem.params.finals_last:
        for final in (a for a in activities if a.final):
            others = [a.end for a in activities if a.day == final.day and not a.final]
            assert final.start >= max(others), final.id


@settings(max_examples=20)
@given(
    sizes=st.lists(st.integers(8, 48), min_size=1, max_size=3),
    count=st.integers(2, 6),
    advance=st.sampled_from([None, 8, 16]),
)
def test_every_placement_respects_pistes_days_precedence_and_rest(sizes, count, advance):
    disciplines = tuple(
        discipline(i + 1, n, format=fmt(4, 7, advance=advance, third=True))
        for i, n in enumerate(sizes)
    )
    prob = problem(
        *disciplines, days=(day(0, "09:00", "23:59", ("12:00", "12:30")),), piste_count=count
    )
    choices = []
    for d in disciplines:
        ks = pool_counts(d.n_pool, 4, 7)
        if not ks:
            return
        choices.append(Choice(discipline=d.id, k=ks[0], day=0))

    outcome = schedule(prob, choices)

    check_invariants(prob, outcome.activities)


@settings(max_examples=20)
@given(sizes=st.lists(st.integers(10, 40), min_size=1, max_size=3), cap=st.integers(1, 4))
def test_concurrency_never_exceeds_the_officials_cap(sizes, cap):
    disciplines = tuple(discipline(i + 1, n) for i, n in enumerate(sizes))
    # one referee and two judges a piste; 3·cap referees and judges to spare
    staffed = tuple(
        discipline(d.id, d.n_pool, format=fmt(staffing=(("referee", 1), ("judge", 2))))
        for d in disciplines
    )
    prob = problem(
        *staffed,
        days=(day(0, "08:00", "23:59"),),
        piste_count=6,
        officials=((0, "referee", cap), (0, "judge", 2 * cap + 1)),
    )
    choices = [
        Choice(discipline=d.id, k=pool_counts(d.n_pool, 5, 7)[0], day=0)
        for d in staffed
        if pool_counts(d.n_pool, 5, 7)
    ]

    activities = schedule(prob, choices).activities

    for a in activities:
        running = [b for b in activities if overlapping(a, b) or b is a]
        at_start = [b for b in running if b.start <= a.start < b.end]
        assert len(at_start) <= cap


def test_officials_cap_the_pistes():
    # five pistes, seven officials, one referee and two judges a piste: two at a time
    d = discipline(1, 40, format=fmt(staffing=(("referee", 1), ("judge", 2))))
    prob = problem(
        d,
        days=(day(0, "08:00", "23:59"),),
        piste_count=5,
        officials=((0, "referee", 3), (0, "judge", 4)),
    )

    activities = schedule(prob, [Choice(1, pool_counts(40, 5, 7)[0], 0)]).activities

    for a in activities:
        assert sum(1 for b in activities if b.start <= a.start < b.end) <= 2


def test_finals_go_last():
    prob = problem(discipline(1, 24, key="LS"), discipline(2, 30, key="SB"), piste_count=4)

    activities = schedule(prob, [Choice(1, 4, 0), Choice(2, 5, 0)]).activities

    finals = [a for a in activities if a.final]
    others = [a for a in activities if not a.final]
    assert {f.discipline for f in finals} == {1, 2}
    assert min(f.start for f in finals) >= max(o.end for o in others)


def test_a_day_too_short_states_its_overrun():
    prob = problem(discipline(1, 60), days=(day(0, "09:00", "11:00"),), piste_count=2)

    outcome = schedule(prob, [Choice(1, pool_counts(60, 5, 7)[0], 0)])

    ((overrun_day, minutes_late),) = outcome.overrun
    last = max(a.end for a in outcome.activities)
    assert (overrun_day, minutes_late) == (0, last - minutes("11:00"))


def test_reserve_pistes_are_unused_in_a_first_plan_and_used_when_replanning():
    base = problem(discipline(1, 30), piste_count=3)
    prob = Problem(**{**base.__dict__, "pistes": pistes(3, reserve=1)})

    first = schedule(prob, [Choice(1, 5, 0)]).activities
    replan = schedule(Problem(**{**prob.__dict__, "use_reserve": True}), [Choice(1, 5, 0)])

    assert 3 not in {a.piste for a in first}
    assert 3 in {a.piste for a in replan.activities}


def test_rest_between_pools_and_elimination():
    prob = problem(discipline(1, 12), piste_count=2, params=Params(min_rest=25))

    activities = schedule(prob, [Choice(1, 2, 0)]).activities

    pools_end = max(a.end for a in activities if a.round == 0)
    first_bout = min(a.start for a in activities if a.round == 1)
    assert first_bout - pools_end >= 25
