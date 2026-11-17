"""The final standing (spec floor-results; design add-floor-results D1).

1 and 2 from the final; 3 and 4 from the third-place bout, or both
semifinal losers share 3; each earlier round's losers, from the
quarterfinals back, ordered among themselves by their seed (the closed pool
ranking); then those who did not advance, by the pool ranking. Shared places
carry one number and the next skips: 1, 2, 3, 3, 5.
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EliminationBout:
    round: int
    position: int
    a: str
    b: str
    winner: str


@dataclass(frozen=True)
class Place:
    key: str
    place: int


def standing(
    bouts: Sequence[EliminationBout],
    rounds: int,
    seeds: dict[str, int],
    ranking: Sequence[str],
    *,
    third_place: bool,
) -> list[Place]:
    """`rounds` the bracket's round count; `seeds` each bracket entrant's seed;
    `ranking` the pool ranking, best first, for those who did not advance."""
    last = rounds - 1
    by_slot = {(b.round, b.position): b for b in bouts}
    out: list[Place] = []

    def loser(bout: EliminationBout) -> str:
        return bout.b if bout.winner == bout.a else bout.a

    final = by_slot.get((last, 0))
    if final is None:
        return []
    out.append(Place(final.winner, 1))
    out.append(Place(loser(final), 2))
    next_place = 3
    if rounds >= 2:
        third = by_slot.get((last, 1)) if third_place else None
        semis = [b for b in bouts if b.round == last - 1]
        if third is not None:
            out.append(Place(third.winner, 3))
            out.append(Place(loser(third), 4))
        else:
            for key in sorted((loser(b) for b in semis), key=lambda k: seeds.get(k, 10**6)):
                out.append(Place(key, 3))
        next_place = 3 + len(semis)
    for round_ in range(last - 2, -1, -1):
        losers = sorted(
            (loser(b) for b in bouts if b.round == round_), key=lambda k: seeds.get(k, 10**6)
        )
        for offset, key in enumerate(losers):
            out.append(Place(key, next_place + offset))
        next_place += len(losers)
    placed = {p.key for p in out}
    for key in ranking:
        if key not in placed:
            out.append(Place(key, next_place))
            next_place += 1
            placed.add(key)
    return out
