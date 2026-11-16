"""Variants, explanations, the draw handover and sensitivity (spec
floor-planner). No database."""

from dataclasses import replace

from app.floor.engine.model import DayPin, KPin, Params
from app.floor.engine.sensitivity import sensitivity
from app.floor.engine.variants import plan
from tests.floor.engine_fixtures import day, discipline, fmt, problem


def test_determinism():
    prob = problem(discipline(1, 29), discipline(2, 41), days=(day(0), day(1)), piste_count=4)

    first, second = plan(prob), plan(prob)

    assert [v.key for v in first.variants] == [v.key for v in second.variants]
    assert first.variants == second.variants


def test_a_plan_made_ahead_counts_registrations():
    result = plan(problem(discipline(1, 31)))

    pools = [a for a in result.variants[0].activities if a.kind == "pool"]
    assert sum(a.size for a in pools) == 31


def test_a_pinned_day_holds():
    prob = problem(
        discipline(1, 29), discipline(2, 20), days=(day(0), day(1)), pins=(DayPin(1, 1),)
    )

    result = plan(prob)

    assert result.variants
    for variant in result.variants:
        assert next(c.day for c in variant.choices if c.discipline == 1) == 1


def test_a_pin_is_named_as_the_obstacle():
    # Saturday is too short for Sabre with Longsword pinned there too
    prob = problem(
        discipline(1, 24, key="LS"),
        discipline(2, 24, key="SB"),
        days=(day(0, "09:00", "11:00"), day(1, "09:00", "11:00")),
        piste_count=4,
        pins=(DayPin(1, 0), DayPin(2, 0)),
    )

    result = plan(prob)

    assert result.variants == ()
    assert result.infeasible is not None
    assert result.infeasible.reason == "pin"
    assert result.infeasible.subject in {"0", "1"}


def test_preferences_order_and_do_not_remove():
    # 30 in 5–6: k = 5 (sizes 6) or k = 6 (sizes 5); both finish by evening
    prob = problem(discipline(1, 30, format=fmt(5, 6)), piste_count=6)

    larger = plan(prob)
    smaller = plan(replace(prob, params=Params(prefer_larger_pools=False)))

    ks = {c.k for v in larger.variants for c in v.choices}
    assert ks <= {5, 6} and len(larger.variants) == len(smaller.variants)
    if len(larger.variants) == 2:
        assert larger.variants[0].choices[0].k == 5


def test_a_pinned_k_outside_the_range_names_the_pin():
    result = plan(problem(discipline(1, 29), pins=(KPin(1, 4),)))

    assert result.infeasible is not None
    assert (result.infeasible.reason, result.infeasible.subject) == ("pin", "0")


def test_shared_fencers_are_kept_out_of_the_parallel_wave():
    # Longsword runs two waves on three pistes; Sabre's pools run beside the second
    prob = problem(
        discipline(1, 36, key="LS"),
        discipline(2, 12, key="SB", format=fmt(6, 6)),
        piste_count=4,
        shared=((1, 2, 6),),
        pins=(KPin(1, 6), KPin(2, 2)),
    )

    variant = plan(prob).variants[0]

    longsword = [e for e in variant.exclusions if e.a == 1]
    assert longsword, variant.exclusions
    assert longsword[0].shared == 6
    assert variant.metrics.exclusion_load == 6


def test_a_shortage_is_reported():
    # everything runs at once: neither side has a wave outside the overlap
    prob = problem(
        discipline(1, 12, key="LS", format=fmt(6, 6)),
        discipline(2, 12, key="SB", format=fmt(6, 6)),
        piste_count=4,
        shared=((1, 2, 8),),
    )

    variant = plan(prob).variants[0]

    assert variant.metrics.shortage == 8


def test_the_officials_limit_is_named():
    # one referee a piste; four referees: the fifth piste and beyond change nothing
    d = discipline(1, 60, format=fmt(5, 6))
    prob = problem(
        d, days=(day(0, "08:00", "23:59"),), piste_count=3, officials=((0, "referee", 4),)
    )
    variant = plan(prob).variants[0]

    effect = sensitivity(prob, variant).days[0]

    assert effect.one_more is not None and effect.one_more < 0
    assert effect.two_more == effect.one_more
    assert effect.limit == "officials"


def test_structure_thresholds():
    prob = problem(discipline(1, 29))
    variant = plan(prob).variants[0]

    (threshold,) = sensitivity(prob, variant).thresholds

    # 29 → only k = 5; 28 adds k = 4 (7, 7, 7, 7); 30 adds k = 6 (5 × 6)
    assert (threshold.below, threshold.above) == (28, 30)
