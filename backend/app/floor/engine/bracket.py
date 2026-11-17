"""The elimination's shape (spec floor-bracket; design add-floor-bracket D1, D3).

The standard seeding order, the one the adopted `hema-agent` elimination
templates place seeds in: start from [1, 2] and, to double, replace each
seed s with (s, size + 1 − s). Seeds 1 and 2 meet only in the final.
"""

from collections.abc import Sequence
from dataclasses import dataclass


def seed_order(size: int) -> list[int]:
    """Seeds in first-round slot order for a bracket of `size` (a power of two)."""
    if size < 2 or size & (size - 1):
        raise ValueError("a bracket's size is a power of two of at least 2")
    order = [1, 2]
    while len(order) < size:
        doubled = len(order) * 2
        order = [seed for s in order for seed in (s, doubled + 1 - s)]
    return order


@dataclass(frozen=True)
class Slot:
    position: int
    # None where the slot is a bye
    seed: int | None


def first_round(size: int, advancing: int) -> list[Slot]:
    """The first round's slots: seeds above `advancing` are byes, so the top
    size − advancing seeds meet nobody and go through."""
    return [
        Slot(position=i, seed=s if s <= advancing else None) for i, s in enumerate(seed_order(size))
    ]


def rounds(size: int) -> int:
    return size.bit_length() - 1


def feeds(match: int) -> int:
    """The next round's bout a match's winner fences in: match m's winner
    takes slot m of the next round, which bout m // 2 holds."""
    return match // 2


@dataclass(frozen=True)
class TeamFigure:
    key: str
    # the average place of the best k members; lower seeds higher
    figure: float
    best: int


def team_figure(key: str, places: Sequence[int], k: int) -> TeamFigure | None:
    """A team's seeding figure from its members' overall pool places (owner
    decision 2026-11-16): the average of its best k. A team with fewer than k
    placed members has none."""
    best = sorted(places)[:k]
    if len(best) < k or k < 1:
        return None
    return TeamFigure(key=key, figure=sum(best) / k, best=best[0])


def seed_teams(figures: Sequence[TeamFigure]) -> list[str]:
    """Teams in seed order: the lower figure first, the best single member
    place breaking a tie, the key keeping it deterministic."""
    return [f.key for f in sorted(figures, key=lambda f: (f.figure, f.best, f.key))]
