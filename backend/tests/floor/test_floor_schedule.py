"""Scheduling (spec floor-planner, Activities are scheduled within days,
pistes and precedence). No database."""

from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from app.floor.engine.model import Activity, Choice, Params, Problem, Referees
from app.floor.engine.schedule import main_warnings, schedule
from app.floor.engine.structure import pool_counts
from app.floor.engine.variants import plan, scheduled
from tests.floor.engine_fixtures import day, discipline, fmt, minutes, problem


def overlapping(a: Activity, b: Activity) -> bool:
    return a.day == b.day and a.start < b.end and b.start < a.end


def check_invariants(problem: Problem, activities: tuple[Activity, ...]) -> None:
    days = {d.index: d for d in problem.days}
    serves = {p.id: p.regular for p in problem.pistes}
    facts = {d.id: d for d in problem.disciplines}
    rest = problem.params.min_rest
    finals = problem.params.finals
    last_day = max(days)
    for i, a in enumerate(activities):
        d = days[a.day]
        assert a.start >= d.start
        for pause in d.breaks:
            assert not (a.start < pause.end and pause.start < a.end), a.id
        # no reserve was opened: every activity is on a piste serving it
        assert a.discipline in serves[a.piste], a.id
        for b in activities[i + 1 :]:
            if a.piste == b.piste:
                assert not overlapping(a, b), (a.id, b.id)
        if a.kind == "pool":
            pause = facts[a.discipline].format.pause
            after = [b for b in activities if b.piste == a.piste and b.day == a.day]
            assert all(b.start >= a.end + pause or b.end <= a.start for b in after if b is not a)
    for d in problem.disciplines:
        mine = [a for a in activities if a.discipline == d.id]
        pools = [a for a in mine if a.round == 0]
        for bout in (a for a in mine if a.round >= 1):
            if bout.round == 1:
                assert bout.start >= max(p.end for p in pools) + rest, bout.id
            elif bout.day == d.day:
                earlier = [a.end for a in mine if a.round == bout.round - 1]
                assert bout.start >= max(earlier), bout.id
    for final in (a for a in activities if a.final):
        if finals == "day":
            others = [a.end for a in activities if a.day == final.day and not a.final]
            assert final.start >= max(others), final.id
        if finals == "tournament":
            assert final.day == last_day, final.id
            others = [a.end for a in activities if a.day == last_day and not a.final]
            assert not others or final.start >= max(others), final.id


@settings(max_examples=20)
@given(
    sizes=st.lists(st.integers(8, 48), min_size=1, max_size=3),
    count=st.integers(2, 6),
    advance=st.sampled_from([None, 8, 16]),
    finals=st.sampled_from(["elimination", "day", "tournament"]),
    two_days=st.booleans(),
)
def test_every_placement_respects_pistes_days_precedence_and_rest(
    sizes, count, advance, finals, two_days
):
    disciplines = tuple(
        discipline(
            i + 1,
            n,
            format=fmt(4, 7, advance=advance, third=True),
            day=i % 2 if two_days else 0,
        )
        for i, n in enumerate(sizes)
    )
    days = (day(0, "09:00", "23:59", ("12:00", "12:30")),)
    if two_days:
        days = (*days, day(1, "09:00", "23:59"))
    prob = problem(
        *disciplines,
        days=days,
        piste_count=count,
        params=Params(finals=finals),
    )
    choices = []
    for d in disciplines:
        ks = pool_counts(d.n_pool, 4, 7)
        if not ks:
            return
        choices.append(Choice(discipline=d.id, k=ks[0], day=d.day))

    outcome = schedule(prob, choices)

    check_invariants(prob, outcome.activities)


@settings(max_examples=20)
@given(
    sizes=st.lists(st.integers(10, 40), min_size=1, max_size=3),
    cap=st.integers(2, 6),
    pool_refs=st.integers(1, 2),
)
def test_concurrency_never_exceeds_the_referees(sizes, cap, pool_refs):
    disciplines = tuple(
        discipline(i + 1, n, format=fmt(referees=(pool_refs, 2))) for i, n in enumerate(sizes)
    )
    prob = problem(
        *disciplines,
        days=(day(0, "08:00", "23:59"),),
        piste_count=6,
        officials=(Referees(0, cap),),
    )
    choices = [
        Choice(discipline=d.id, k=pool_counts(d.n_pool, 5, 7)[0], day=0)
        for d in disciplines
        if pool_counts(d.n_pool, 5, 7)
    ]

    activities = schedule(prob, choices).activities

    for a in activities:
        at_start = [b for b in activities if b.start <= a.start < b.end]
        need = sum(pool_refs if b.kind == "pool" else 2 for b in at_start)
        assert need <= cap


def test_referees_cap_the_pistes():
    # five pistes, four referees, two referees a pool: two pools at a time
    d = discipline(1, 40, format=fmt(referees=(2, 1)))
    prob = problem(d, days=(day(0, "08:00", "23:59"),), piste_count=5, officials=(Referees(0, 4),))

    activities = schedule(prob, [Choice(1, pool_counts(40, 5, 7)[0], 0)]).activities

    for a in (a for a in activities if a.kind == "pool"):
        assert sum(1 for b in activities if b.start <= a.start < b.end) <= 2


def test_finals_within_the_elimination():
    prob = problem(discipline(1, 24, key="LS"), discipline(2, 30, key="SB"), piste_count=4)

    activities = schedule(prob, [Choice(1, 4, 0), Choice(2, 5, 0)]).activities
    others = [a.end for a in activities if not a.final]

    for final in (a for a in activities if a.final):
        semis = [
            a.end
            for a in activities
            if a.discipline == final.discipline and a.round == final.round - 1
        ]
        assert final.start >= max(semis)
    # a final need not wait for the other discipline
    assert min(f.start for f in activities if f.final) < max(others)


def test_finals_at_the_end_of_the_day():
    prob = problem(
        discipline(1, 24, key="LS"),
        discipline(2, 30, key="SB"),
        piste_count=4,
        params=Params(finals="day"),
    )

    activities = schedule(prob, [Choice(1, 4, 0), Choice(2, 5, 0)]).activities

    finals = [a for a in activities if a.final]
    others = [a for a in activities if not a.final]
    assert {f.discipline for f in finals} == {1, 2}
    assert min(f.start for f in finals) >= max(o.end for o in others)


def test_finals_at_the_end_of_the_tournament():
    prob = problem(
        discipline(1, 24, key="SB", format=fmt(third=True)),
        discipline(2, 30, key="LS", day=1),
        days=(day(0), day(1)),
        piste_count=4,
        params=Params(finals="tournament"),
    )

    activities = schedule(prob, [Choice(1, 4, 0), Choice(2, 5, 1)]).activities

    sabre_finals = {a.id for a in activities if a.discipline == 1 and a.final}
    assert "SB:third" in sabre_finals and len(sabre_finals) == 2
    assert all(a.day == 1 for a in activities if a.final)
    sunday = [a.end for a in activities if a.day == 1 and not a.final]
    assert min(a.start for a in activities if a.final) >= max(sunday)


def test_a_day_too_short_states_its_overrun():
    prob = problem(discipline(1, 60), days=(day(0, "09:00", "11:00"),), piste_count=2)

    outcome = schedule(prob, [Choice(1, pool_counts(60, 5, 7)[0], 0)])

    ((overrun_day, minutes_late),) = outcome.overrun
    last = max(a.end for a in outcome.activities)
    assert (overrun_day, minutes_late) == (0, last - minutes("11:00"))


def test_a_reserve_piste_is_held_back_when_regular_ones_suffice():
    prob = problem(discipline(1, 30), piste_count=4, reserve=1)

    outcome = scheduled(prob, [Choice(1, 5, 0)])

    assert 4 not in {a.piste for a in outcome.activities}
    assert outcome.reserve_used == ()


def test_a_reserve_piste_is_used_when_the_day_needs_it():
    prob = problem(discipline(1, 40), days=(day(0, "09:00", "12:30"),), piste_count=3, reserve=2)

    without = schedule(prob, [Choice(1, 6, 0)])
    outcome = scheduled(prob, [Choice(1, 6, 0)])

    assert without.overrun
    assert outcome.reserve_used
    assert set(outcome.reserve_used) <= {2, 3}


def test_a_free_piste_is_never_used():
    base = problem(discipline(1, 30), piste_count=3)
    free = replace(base.pistes[2], regular=frozenset(), reserve=frozenset())
    prob = replace(base, pistes=(*base.pistes[:2], free))

    activities = scheduled(prob, [Choice(1, 5, 0)]).activities

    assert 3 not in {a.piste for a in activities}


def test_a_taken_over_discipline_waits_for_its_source():
    prob = problem(
        discipline(1, 30, key="LS"),
        discipline(2, 12, key="LT", takes_from=1),
        piste_count=4,
        params=Params(min_rest=15),
    )

    activities = schedule(prob, [Choice(1, 5, 0), Choice(2, 0, 0)]).activities

    assert not [a for a in activities if a.discipline == 2 and a.kind == "pool"]
    source_end = max(a.end for a in activities if a.discipline == 1 and a.kind == "pool")
    first = min(a.start for a in activities if a.discipline == 2)
    assert first >= source_end + 15


def test_a_piste_keeps_the_pause_after_a_pool():
    prob = problem(discipline(1, 12, format=fmt(6, 6, pause=10)), piste_count=1)

    activities = schedule(prob, [Choice(1, 2, 0)]).activities

    first, second = sorted((a for a in activities if a.kind == "pool"), key=lambda a: a.start)
    assert second.start - first.end >= 10
    assert first.end - first.start == 15 * 4


def test_rest_between_pools_and_elimination():
    prob = problem(discipline(1, 12), piste_count=2, params=Params(min_rest=25))

    activities = schedule(prob, [Choice(1, 2, 0)]).activities

    pools_end = max(a.end for a in activities if a.round == 0)
    first_bout = min(a.start for a in activities if a.round == 1)
    assert first_bout - pools_end >= 25


@settings(max_examples=20)
@given(mains=st.integers(0, 6), regular=st.integers(4, 8))
def test_main_warnings_never_change_feasibility_or_order(mains, regular):
    base = problem(
        discipline(1, 30), discipline(2, 24), piste_count=5, officials=(Referees(0, regular),)
    )
    with_mains = replace(base, officials=(Referees(0, regular, main=mains),))

    a, b = plan(base), plan(with_mains)

    assert [v.key for v in a.variants] == [v.key for v in b.variants]
    for variant in b.variants:
        for _, _, short in variant.metrics.main_warnings:
            assert short > 0
        assert main_warnings(with_mains, variant.activities) == variant.metrics.main_warnings
