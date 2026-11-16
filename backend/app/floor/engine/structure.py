"""Pool counts and the bracket (spec floor-planner, Pool structure follows the
format and the hard rule; design add-floor-planner D2)."""

from dataclasses import dataclass


def pool_counts(n: int, lo: int, hi: int) -> tuple[int, ...]:
    """Every k whose pools, sized ⌊n/k⌋ and ⌈n/k⌉, all lie within lo..hi,
    smallest k first. Empty where none does."""
    if n <= 0 or lo > hi:
        return ()
    return tuple(k for k in range(1, n + 1) if lo <= n // k and -(-n // k) <= hi)


def pool_sizes(n: int, k: int) -> tuple[int, ...]:
    """The k pool sizes, the larger ones first; they differ by at most one."""
    small, extra = divmod(n, k)
    return tuple(small + 1 if i < extra else small for i in range(k))


def pool_bouts(size: int) -> int:
    return size * (size - 1) // 2


@dataclass(frozen=True)
class Bracket:
    size: int
    byes: int
    # bouts per round, first round first; the last is the final's round
    rounds: tuple[int, ...]


def bracket(advancing: int) -> Bracket:
    """The bracket holding `advancing` seeds: the least power of two at least
    that, the top seeds taking the byes. Fewer than two seeds fence no bracket."""
    if advancing < 2:
        return Bracket(size=max(advancing, 0), byes=0, rounds=())
    size = 1
    while size < advancing:
        size *= 2
    byes = size - advancing
    rounds: list[int] = []
    # the first round's bouts are the seeds who did not draw a bye, in pairs
    rounds.append((size - 2 * byes) // 2 if byes else size // 2)
    remaining = size // 2
    while remaining > 1:
        rounds.append(remaining // 2)
        remaining //= 2
    return Bracket(size=size, byes=byes, rounds=tuple(rounds))


def advancing(n_bracket: int, advance: int | None) -> int:
    """A: the format's number, capped at who there is, or everyone."""
    return n_bracket if advance is None else min(advance, n_bracket)
