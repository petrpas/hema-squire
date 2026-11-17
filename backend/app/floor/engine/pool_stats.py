"""Pool statistics and their checks, ported from `hema-agent`'s
`compute_pool_stats` and `calc_pools` (spec floor-pools; design
add-floor-pools D1). Rules unchanged: a victory is the higher score, and the
ranking is V/M, then the index (TS − TR), then TS, all descending.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Outcome = Literal["win", "loss", "draw", "no"]


@dataclass(frozen=True)
class BoutResult:
    a: str
    b: str
    score_a: int
    score_b: int
    outcome_a: Outcome
    outcome_b: Outcome
    note: str | None = None


@dataclass(frozen=True)
class Stats:
    key: str
    v: int
    m: int
    ts: int
    tr: int

    @property
    def ind(self) -> int:
        return self.ts - self.tr

    @property
    def vm(self) -> float:
        return self.v / self.m if self.m > 0 else 0.0


def compute(keys: Sequence[str], bouts: Sequence[BoutResult]) -> list[Stats]:
    """Each fencer's V, M, TS, TR, ranked by (V/M, Ind, TS) descending. A
    bout naming someone not listed counts for the one who is."""
    tally = {key: [0, 0, 0, 0] for key in keys}  # v, m, ts, tr
    for bout in bouts:
        if bout.a in tally:
            row = tally[bout.a]
            row[2] += bout.score_a
            row[3] += bout.score_b
            row[1] += 1
            if bout.score_a > bout.score_b:
                row[0] += 1
        if bout.b in tally:
            row = tally[bout.b]
            row[2] += bout.score_b
            row[3] += bout.score_a
            row[1] += 1
            if bout.score_b > bout.score_a:
                row[0] += 1
    found = [Stats(key=k, v=r[0], m=r[1], ts=r[2], tr=r[3]) for k, r in tally.items()]
    # a stable sort: equal fencers keep the order they were listed in
    found.sort(key=lambda s: (-s.vm, -s.ind, -s.ts))
    return found


@dataclass(frozen=True)
class PoolWarning:
    """A check that failed, as `calc_pools` states it."""

    pool: int | None
    code: Literal["no_results", "bouts_missing", "touches_asymmetric", "unknown_fencer"]
    subject: str = ""
    expected: int = 0
    found: int = 0


def check(
    pools: Sequence[tuple[int, Sequence[str]]], bouts: Sequence[BoutResult]
) -> list[PoolWarning]:
    """`calc_pools`' checks: every fencer has their bouts, each pool's
    touches add up, and no bout names a stranger."""
    everyone = [key for _, keys in pools for key in keys]
    by_key = {s.key: s for s in compute(everyone, bouts)}
    out: list[PoolWarning] = []
    for number, keys in sorted(pools):
        expected = len(keys) - 1
        ts = tr = 0
        for key in keys:
            stats = by_key[key]
            if stats.m == 0:
                out.append(PoolWarning(pool=number, code="no_results", subject=key))
            elif stats.m != expected:
                out.append(
                    PoolWarning(
                        pool=number,
                        code="bouts_missing",
                        subject=key,
                        expected=expected,
                        found=stats.m,
                    )
                )
            ts += stats.ts
            tr += stats.tr
        if ts != tr:
            out.append(PoolWarning(pool=number, code="touches_asymmetric", expected=ts, found=tr))
    known = set(everyone)
    strangers = sorted({k for b in bouts for k in (b.a, b.b) if k not in known})
    out.extend(PoolWarning(pool=None, code="unknown_fencer", subject=key) for key in strangers)
    return out
