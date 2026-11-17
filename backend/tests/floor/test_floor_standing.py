"""The final standing (spec floor-results). No database."""

from hypothesis import given
from hypothesis import strategies as st

from app.floor.engine.bracket import seed_order
from app.floor.engine.standing import EliminationBout, standing


def play(size: int, entrants: list[str], winner_of) -> list[EliminationBout]:
    """A whole bracket, each bout won as `winner_of(a, b)` says."""
    order = seed_order(size)
    slots = [entrants[s - 1] if s <= len(entrants) else None for s in order]
    bouts: list[EliminationBout] = []
    round_ = 0
    while len(slots) > 1:
        next_slots = []
        for position in range(len(slots) // 2):
            a, b = slots[2 * position], slots[2 * position + 1]
            if a is None or b is None:
                next_slots.append(a or b)
                continue
            w = winner_of(a, b)
            bouts.append(EliminationBout(round_, position, a, b, w))
            next_slots.append(w)
        slots = next_slots
        round_ += 1
    return bouts


def test_quarterfinal_losers_by_pool_ranking():
    keys = [f"p{n}" for n in range(1, 17)]
    seeds = {k: i + 1 for i, k in enumerate(keys)}
    # the better seed always wins, so the quarterfinal losers are seeds 5–8
    bouts = play(16, keys, lambda a, b: a if seeds[a] < seeds[b] else b)

    places = standing(bouts, 4, seeds, keys, third_place=False)

    assert [(p.key, p.place) for p in places[:8]] == [
        ("p1", 1),
        ("p2", 2),
        ("p3", 3),
        ("p4", 3),
        ("p5", 5),
        ("p6", 6),
        ("p7", 7),
        ("p8", 8),
    ]


def test_a_third_place_bout_splits_third_and_fourth():
    keys = ["a", "b", "c", "d"]
    seeds = {k: i + 1 for i, k in enumerate(keys)}
    bouts = play(4, keys, lambda a, b: a if seeds[a] < seeds[b] else b)
    bouts.append(EliminationBout(1, 1, "c", "d", "d"))

    places = standing(bouts, 2, seeds, keys, third_place=True)

    assert [(p.key, p.place) for p in places] == [("a", 1), ("b", 2), ("d", 3), ("c", 4)]


@given(
    n=st.integers(2, 40),
    advancing=st.integers(2, 40),
    flips=st.lists(st.booleans(), min_size=64, max_size=64),
)
def test_every_entrant_is_placed_once_and_places_never_go_down(n, advancing, flips):
    keys = [f"f{i}" for i in range(n)]
    count = min(advancing, n)
    size = 2
    while size < count:
        size *= 2
    seeds = {k: i + 1 for i, k in enumerate(keys[:count])}
    toss = iter(flips * 4)
    bouts = play(size, keys[:count], lambda a, b: a if next(toss) else b)

    places = standing(bouts, size.bit_length() - 1, seeds, keys, third_place=False)

    assert sorted(p.key for p in places) == sorted(keys)
    assert [p.place for p in places] == sorted(p.place for p in places)
    assert places[0].place == 1
