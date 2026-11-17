"""The pool draw, ported from `hema-agent`'s `pool_alch_agent` (spec floor-draw;
design add-floor-pools D1, D2). Behaviour unchanged: the owner adopted it as
it is, fixed seed tiers included.

Two phases:
1. Construction — snake seeding and an optimal assignment within each window
   of k fencers.
2. Improvement — hill-climbing pair swaps within the tier constraints.

Seed tiers (rows of the ideal snake, 1-based):
- row 1 (tier 0): pool heads, locked, never swapped;
- row 2 (tier 1): swapped only within tier 1, penalty = snake distance;
- rows 3–4 (tier 2): swapped within tier 2, penalty = snake distance;
- rows 5+ (tier 3): swapped freely, no snake penalty.

numpy is replaced by the standard library: `hungarian.assign` for scipy's
assignment, and a population standard deviation summed in numpy's pairwise
order, so floating-point ties fall the same way.
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import combinations

from app.floor.engine.hungarian import assign

# rows (0-based) bounding the protected tiers: [0,1), [1,2), [2,4), [4,∞)
TIER_BOUNDARIES = (1, 2, 4)
MAX_ITERATIONS = 500


@dataclass(frozen=True)
class PoolFencer:
    key: str
    # 1 is the strongest; the order the draw seeds by
    seed: int
    nationality: str | None
    club: str | None
    # disciplines this fencer also fences, which keep them out of parallel waves
    other_disciplines: tuple[str, ...] = ()


@dataclass(frozen=True)
class Weights:
    snake_deviation: float = 1.0
    club: float = 10.0
    nationality: float = 3.0
    wave: float = 5.0


@dataclass(frozen=True)
class PoolConfig:
    num_pools: int
    # pools per wave, summing to num_pools
    wave_sizes: tuple[int, ...]
    # 0-based waves where other disciplines run at the same time
    parallel_waves: tuple[int, ...] = field(default_factory=tuple)

    def wave_of_pool(self, pool: int) -> int:
        cumulative = 0
        for wave, size in enumerate(self.wave_sizes):
            cumulative += size
            if pool < cumulative:
                return wave
        return len(self.wave_sizes) - 1

    def is_parallel(self, wave: int) -> bool:
        return wave in self.parallel_waves


@dataclass(frozen=True)
class Score:
    snake_deviation: float
    club: float
    nationality: float
    wave: float

    @property
    def total(self) -> float:
        return self.snake_deviation + self.club + self.nationality + self.wave


Assignment = list[list[PoolFencer]]


# ------------------------------------------------------------ numpy's arithmetic


def _pairwise_sum(values: Sequence[float]) -> float:
    """numpy's pairwise summation, so a sum rounds as numpy's does."""
    n = len(values)
    if n < 8:
        total = 0.0
        for value in values:
            total += value
        return total
    if n <= 128:
        r = list(values[:8])
        i = 8
        while i < n - (n % 8):
            for j in range(8):
                r[j] += values[i + j]
            i += 8
        total = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
        while i < n:
            total += values[i]
            i += 1
        return total
    half = n // 2
    half -= half % 8
    return _pairwise_sum(values[:half]) + _pairwise_sum(values[half:])


def std(values: Sequence[int]) -> float:
    """`numpy.std` of integers: the population standard deviation."""
    n = len(values)
    mean = _pairwise_sum([float(v) for v in values]) / n
    squares = [(v - mean) * (v - mean) for v in values]
    return math.sqrt(_pairwise_sum(squares) / n)


# ------------------------------------------------------------ helpers


def _domestic(fencers: Sequence[PoolFencer]) -> str | None:
    counts: Counter[str] = Counter(f.nationality for f in fencers if f.nationality)
    return counts.most_common(1)[0][0] if counts else None


def _is_foreign(fencer: PoolFencer, domestic: str | None) -> bool:
    return bool(fencer.nationality and fencer.nationality != domestic)


def seed_tier(seed: int, num_pools: int) -> int:
    row = (seed - 1) // num_pools
    if row < TIER_BOUNDARIES[0]:
        return 0
    if row < TIER_BOUNDARIES[1]:
        return 1
    if row < TIER_BOUNDARIES[2]:
        return 2
    return 3


def _snake_pos(pool: int, row: int, num_pools: int) -> int:
    if row % 2 == 0:
        return row * num_pools + pool
    return row * num_pools + (num_pools - 1 - pool)


# ------------------------------------------------------------ scoring


def score(assignment: Assignment, weights: Weights, config: PoolConfig) -> Score:
    n = config.num_pools

    snake_dev = 0.0
    for pool_idx, pool in enumerate(assignment):
        for row, fencer in enumerate(sorted(pool, key=lambda f: f.seed)):
            if seed_tier(fencer.seed, n) == 3:
                continue
            snake_dev += abs(_snake_pos(pool_idx, row, n) - (fencer.seed - 1))
    snake_score = weights.snake_deviation * snake_dev

    club_score = 0.0
    for pool in assignment:
        for count in Counter(f.club for f in pool if f.club).values():
            if count > 1:
                club_score += weights.club * (count * (count - 1) / 2)

    everyone = [f for pool in assignment for f in pool]
    domestic = _domestic(everyone)
    # a foreign fencer has a nationality by definition
    foreign = {f.nationality for f in everyone if f.nationality and _is_foreign(f, domestic)}
    term_weight = weights.nationality / (1 + len(foreign))
    nat_score = 0.0
    nat_score += term_weight * std(
        [sum(1 for f in pool if _is_foreign(f, domestic)) for pool in assignment]
    )
    # sorted: the original iterates a set, whose order varies between runs;
    # the engine's must not
    for nationality in sorted(foreign):
        nat_score += term_weight * std(
            [sum(1 for f in pool if f.nationality == nationality) for pool in assignment]
        )

    violations = 0
    for pool_idx, pool in enumerate(assignment):
        if config.is_parallel(config.wave_of_pool(pool_idx)):
            violations += sum(1 for f in pool if f.other_disciplines)

    return Score(
        snake_deviation=snake_score,
        club=club_score,
        nationality=nat_score,
        wave=weights.wave * violations,
    )


# ------------------------------------------------------------ construction


def _window_cost(
    window: Sequence[PoolFencer],
    pools: Assignment,
    n: int,
    window_idx: int,
    weights: Weights,
    config: PoolConfig,
    domestic: str | None,
    terms: int,
) -> list[list[float]]:
    cost = [[0.0] * n for _ in window]
    use_snake = window_idx < TIER_BOUNDARIES[2]
    nat_weight = weights.nationality / terms if terms else 0.0
    for i, fencer in enumerate(window):
        preferred = i if window_idx % 2 == 0 else (n - 1 - i)
        for j in range(n):
            if use_snake:
                cost[i][j] += weights.snake_deviation * abs(j - preferred)
            if fencer.club:
                cost[i][j] += weights.club * sum(1 for f in pools[j] if f.club == fencer.club)
            if _is_foreign(fencer, domestic):
                cost[i][j] += nat_weight * sum(1 for f in pools[j] if _is_foreign(f, domestic))
                cost[i][j] += nat_weight * sum(
                    1 for f in pools[j] if f.nationality == fencer.nationality
                )
            if fencer.other_disciplines and config.is_parallel(config.wave_of_pool(j)):
                cost[i][j] += 1e6
    return cost


def _repair_waves(pools: Assignment, config: PoolConfig) -> None:
    """Swap fencers of other disciplines out of parallel pools, tiers aside."""
    n = config.num_pools
    for pp in (j for j in range(n) if config.is_parallel(config.wave_of_pool(j))):
        for i, fencer in enumerate(pools[pp]):
            if not fencer.other_disciplines:
                continue
            swapped = False
            for other in range(n):
                if config.is_parallel(config.wave_of_pool(other)):
                    continue
                for k, candidate in enumerate(pools[other]):
                    if not candidate.other_disciplines:
                        pools[pp][i], pools[other][k] = pools[other][k], pools[pp][i]
                        swapped = True
                        break
                if swapped:
                    break


def construct(fencers: Sequence[PoolFencer], config: PoolConfig, weights: Weights) -> Assignment:
    n = config.num_pools
    ordered = sorted(fencers, key=lambda f: f.seed)
    domestic = _domestic(fencers)
    terms = 1 + len({f.nationality for f in fencers if _is_foreign(f, domestic)})
    pools: Assignment = [[] for _ in range(n)]
    for window_idx, start in enumerate(range(0, len(ordered), n)):
        window = ordered[start : start + n]
        cost = _window_cost(window, pools, n, window_idx, weights, config, domestic, terms)
        for row, column in enumerate(assign(cost)):
            pools[column].append(window[row])
    _repair_waves(pools, config)
    return pools


# ------------------------------------------------------------ improvement


def improve(
    assignment: Assignment, weights: Weights, config: PoolConfig
) -> tuple[Assignment, Score]:
    current = [list(pool) for pool in assignment]
    current_score = score(current, weights, config)
    n = config.num_pools
    for _ in range(MAX_ITERATIONS):
        best_delta = 0.0
        best: tuple[int, int, int, int] | None = None
        for pa, pb in combinations(range(len(current)), 2):
            for ia, fa in enumerate(current[pa]):
                tier_a = seed_tier(fa.seed, n)
                if tier_a == 0:
                    continue
                for ib, fb in enumerate(current[pb]):
                    tier_b = seed_tier(fb.seed, n)
                    if tier_b == 0 or tier_a != tier_b:
                        continue
                    if fa.other_disciplines and config.is_parallel(config.wave_of_pool(pb)):
                        continue
                    if fb.other_disciplines and config.is_parallel(config.wave_of_pool(pa)):
                        continue
                    current[pa][ia], current[pb][ib] = current[pb][ib], current[pa][ia]
                    delta = current_score.total - score(current, weights, config).total
                    current[pa][ia], current[pb][ib] = current[pb][ib], current[pa][ia]
                    if delta > best_delta:
                        best_delta = delta
                        best = (pa, ia, pb, ib)
        if best is None:
            break
        pa, ia, pb, ib = best
        current[pa][ia], current[pb][ib] = current[pb][ib], current[pa][ia]
        current_score = score(current, weights, config)
    return current, current_score


def solve(
    fencers: Sequence[PoolFencer], config: PoolConfig, weights: Weights
) -> tuple[Assignment, Score]:
    """Construct, then improve: the adopted draw."""
    return improve(construct(fencers, config, weights), weights, config)
