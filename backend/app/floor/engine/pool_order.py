"""The bout order of a pool sheet (design add-floor-pools D4).

Sizes 4–8 are the orders the adopted `hema-agent` templates print
(`app/typst/templates/pool_table_<n>.typ`), as (left, right) positions from 1.
The templates have no sheet for 3, 9 or 10, which a format's range still
allows; those are a round-robin by the circle method, deterministic, each
pair once (my decision, recorded in the design for the owner's review).
"""

TEMPLATES: dict[int, tuple[tuple[int, int], ...]] = {
    4: ((4, 1), (3, 2), (4, 2), (1, 3), (3, 4), (2, 1)),
    5: ((1, 4), (5, 2), (3, 4), (5, 1), (2, 3), (4, 5), (3, 1), (4, 2), (3, 5), (1, 2)),
    6: (
        (1, 4), (2, 5), (6, 3), (5, 1), (6, 4), (2, 3), (5, 6), (3, 1),
        (4, 2), (3, 5), (6, 1), (4, 5), (2, 6), (3, 4), (1, 2),
    ),
    7: (
        (1, 4), (2, 5), (3, 6), (7, 1), (5, 4), (2, 3), (6, 7), (1, 5), (4, 3), (2, 6), (7, 3),
        (4, 2), (5, 6), (1, 3), (4, 7), (3, 5), (2, 7), (6, 1), (7, 5), (6, 4), (1, 2),
    ),
    8: (
        (8, 1), (7, 2), (6, 3), (5, 4), (8, 2), (1, 3), (7, 4), (6, 5), (8, 3), (2, 4),
        (1, 5), (7, 6), (8, 4), (3, 5), (2, 6), (1, 7), (8, 5), (4, 6), (3, 7), (2, 1),
        (8, 6), (5, 7), (4, 1), (3, 2), (8, 7), (6, 1), (5, 2), (4, 3),
    ),
}  # fmt: skip


def _circle(size: int) -> tuple[tuple[int, int], ...]:
    """A round-robin by the circle method: position 1 fixed, the rest rotating."""
    players = list(range(1, size + 1)) + ([0] if size % 2 else [])
    count = len(players)
    out: list[tuple[int, int]] = []
    for _ in range(count - 1):
        for i in range(count // 2):
            a, b = players[i], players[count - 1 - i]
            if a and b:
                out.append((a, b))
        players = [players[0], players[-1], *players[1:-1]]
    return tuple(out)


def order(size: int) -> tuple[tuple[int, int], ...]:
    """The bouts of a pool of `size`, in sheet order."""
    if size in TEMPLATES:
        return TEMPLATES[size]
    if 2 <= size <= 10:
        return _circle(size)
    raise ValueError(f"no bout order for a pool of {size}")
