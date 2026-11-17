"""The draw and the pool statistics, ported from hema-agent (spec floor-draw;
design add-floor-pools D1). The fixtures were recorded by running the
originals offline on NaDuel 2026 Sabre (names replaced) and on seeded
synthetic sets; the ports must reproduce them exactly. No database."""

import itertools
import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from app.floor.engine import pool_order
from app.floor.engine.draw import PoolConfig, PoolFencer, Weights, seed_tier, solve
from app.floor.engine.hungarian import assign
from app.floor.engine.pool_stats import BoutResult, check, compute

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "hema_agent_draws.json").read_text())


def fencer(raw: dict) -> PoolFencer:
    return PoolFencer(
        key=raw["name"],
        seed=raw["seed"],
        nationality=raw["nationality"],
        club=raw["club"],
        other_disciplines=tuple(raw["other_disciplines"]),
    )


def test_the_draw_reproduces_every_recorded_case():
    for case in FIXTURES["draw"]:
        config = PoolConfig(
            num_pools=case["config"]["num_pools"],
            wave_sizes=tuple(case["config"]["wave_sizes"]),
            parallel_waves=tuple(case["config"]["parallel_waves"]),
        )
        pools, score = solve(
            [fencer(f) for f in case["fencers"]], config, Weights(**case["weights"])
        )

        assert [[f.key for f in pool] for pool in pools] == case["assignment"], case["name"]
        assert round(score.total, 9) == round(sum(case["score"].values()), 9), case["name"]


def test_the_stats_reproduce_every_recorded_case():
    for case in FIXTURES["stats"]:
        bouts = [
            BoutResult(
                a=b["Fencer1"],
                b=b["Fencer2"],
                score_a=b["Score1"],
                score_b=b["Score2"],
                outcome_a="win",
                outcome_b="loss",
            )
            for b in case["bouts"]
        ]
        got = [
            {"name": s.key, "v": s.v, "m": s.m, "ts": s.ts, "tr": s.tr, "ind": s.ind, "vm": s.vm}
            for s in compute(case["names"], bouts)
        ]
        assert got == case["result"]


@given(st.lists(st.lists(st.integers(0, 30), min_size=6, max_size=6), min_size=1, max_size=6))
def test_the_assignment_costs_no_more_than_brute_force(rows):
    cost = [[float(c) for c in row] for row in rows]
    columns = assign(cost)
    best = min(
        sum(cost[r][c] for r, c in enumerate(perm))
        for perm in itertools.permutations(range(6), len(cost))
    )
    assert len(set(columns)) == len(cost)
    assert sum(cost[r][c] for r, c in enumerate(columns)) == best


def test_pool_heads_stay_in_the_first_row():
    case = FIXTURES["draw"][0]
    config = PoolConfig(
        num_pools=case["config"]["num_pools"], wave_sizes=(case["config"]["num_pools"],)
    )
    pools, _ = solve([fencer(f) for f in case["fencers"]], config, Weights())

    heads = sorted(min(f.seed for f in pool) for pool in pools)
    assert heads == list(range(1, config.num_pools + 1))
    assert all(seed_tier(seed, config.num_pools) == 0 for seed in heads)


def test_other_disciplines_stay_out_of_parallel_waves_when_they_fit():
    fencers = [
        PoolFencer(
            key=f"F{i}",
            seed=i,
            nationality="CZ",
            club=None,
            other_disciplines=("X",) if i % 5 == 0 else (),
        )
        for i in range(1, 25)
    ]
    config = PoolConfig(num_pools=4, wave_sizes=(2, 2), parallel_waves=(1,))

    pools, score = solve(fencers, config, Weights())

    assert score.wave == 0
    assert not any(f.other_disciplines for pool in pools[2:] for f in pool)


def test_every_size_has_a_full_bout_order():
    for size in range(3, 11):
        bouts = pool_order.order(size)
        assert len(bouts) == size * (size - 1) // 2
        assert {frozenset(b) for b in bouts} == {
            frozenset(p) for p in itertools.combinations(range(1, size + 1), 2)
        }


def test_the_checks_name_missing_bouts_and_asymmetric_touches():
    bouts = [BoutResult("a", "b", 5, 3, "win", "loss"), BoutResult("a", "c", 2, 5, "loss", "win")]

    found = check([(1, ["a", "b", "c"])], bouts)

    assert [(w.code, w.subject) for w in found] == [("bouts_missing", "b"), ("bouts_missing", "c")]
