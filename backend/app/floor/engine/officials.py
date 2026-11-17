"""Officials on blocks (spec floor-officials; design add-floor-officials D1).

A block is one piste's run of one discipline's consecutive activities. Each
block's staffing template is filled role by role: pins first, then the
lowest-penalty feasible official in block start order, then pairwise swaps
while they lower the total. Hard constraints are never broken; a role that
cannot be filled stays empty and is stated.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.floor.engine.model import Activity, Role

CLUB = 100
PISTE_CHANGE = 10
MAX_SWAPS = 200


@dataclass(frozen=True)
class Block:
    key: str
    discipline: int
    piste: int
    day: int
    start: int
    end: int
    # (role, how many)
    needs: tuple[tuple[Role, int], ...]
    activities: tuple[str, ...]
    # clubs of the fencers in the block's pools, once the draw is announced
    clubs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Official:
    id: int
    roles: frozenset[str]
    disciplines: frozenset[int]
    days: frozenset[int]
    club: str | None = None
    # (day, start, end) the official fences
    blocked: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True)
class Pin:
    block: str
    role: Role
    slot: int
    official: int


@dataclass(frozen=True)
class Seat:
    block: str
    role: Role
    slot: int
    official: int | None
    pinned: bool = False


@dataclass(frozen=True)
class Result:
    seats: tuple[Seat, ...]
    # (official, block) where the official shares a club with a fencer of the block
    conflicts: tuple[tuple[int, str], ...] = field(default_factory=tuple)

    @property
    def unfilled(self) -> tuple[Seat, ...]:
        return tuple(s for s in self.seats if s.official is None)


def blocks(
    activities: Sequence[Activity],
    overhead: dict[int, int],
    needs: dict[int, tuple[tuple[Role, int], ...]],
) -> list[Block]:
    """One piste's consecutive activities of one discipline, a gap of at most
    the discipline's per-pool overhead between them."""
    out: list[Block] = []
    ordered = sorted(activities, key=lambda a: (a.day, a.piste, a.start, a.id))
    current: list[Activity] = []

    def flush() -> None:
        if not current:
            return
        first = current[0]
        out.append(
            Block(
                key=f"{first.piste}:{first.id}",
                discipline=first.discipline,
                piste=first.piste,
                day=first.day,
                start=first.start,
                end=max(a.end for a in current),
                needs=needs.get(first.discipline, ()),
                activities=tuple(a.id for a in current),
            )
        )
        current.clear()

    for activity in ordered:
        if current:
            last = current[-1]
            same = (
                last.day == activity.day
                and last.piste == activity.piste
                and last.discipline == activity.discipline
                and activity.start - max(a.end for a in current)
                <= overhead.get(activity.discipline, 0)
            )
            if not same:
                flush()
        current.append(activity)
    flush()
    return sorted(out, key=lambda b: (b.day, b.start, b.piste, b.key))


def _overlap(a: Block, day: int, start: int, end: int) -> bool:
    return a.day == day and a.start < end and start < a.end


def hard_ok(
    official: Official,
    block: Block,
    role: str,
    taken: Sequence[Block],
) -> str | None:
    """None where the official may sit there; otherwise the broken rule."""
    if block.day not in official.days:
        return "unavailable"
    if block.discipline not in official.disciplines:
        return "not_qualified"
    if role not in official.roles:
        return "wrong_role"
    if any(
        _overlap(other, block.day, block.start, block.end)
        for other in taken
        if other.key != block.key
    ):
        return "double_booked"
    if any(_overlap(block, day, start, end) for day, start, end in official.blocked):
        return "fencing"
    return None


def _penalty(official: Official, block: Block, taken: Sequence[Block]) -> int:
    club = CLUB if official.club and official.club in block.clubs else 0
    load = sum(b.end - b.start for b in taken)
    same_day = [b for b in taken if b.day == block.day and b.end <= block.start]
    previous = max(same_day, key=lambda b: b.end, default=None)
    change = PISTE_CHANGE if previous is not None and previous.piste != block.piste else 0
    return club + change + load


def assign(
    block_list: Sequence[Block], officials: Sequence[Official], pins: Sequence[Pin]
) -> Result:
    by_key = {b.key: b for b in block_list}
    people = {o.id: o for o in officials}
    taken: dict[int, list[Block]] = {o.id: [] for o in officials}
    seats: dict[tuple[str, str, int], Seat] = {}

    for pin in pins:
        block = by_key.get(pin.block)
        official = people.get(pin.official)
        if block is None or official is None:
            continue
        if hard_ok(official, block, pin.role, taken[official.id]) is not None:
            continue
        seats[(pin.block, pin.role, pin.slot)] = Seat(
            pin.block, pin.role, pin.slot, pin.official, True
        )
        taken[official.id].append(block)

    for block in block_list:
        for role, count in block.needs:
            for slot in range(count):
                if (block.key, role, slot) in seats:
                    continue
                candidates = [
                    (_penalty(o, block, taken[o.id]), o.id)
                    for o in officials
                    if hard_ok(o, block, role, taken[o.id]) is None and block not in taken[o.id]
                ]
                if not candidates:
                    seats[(block.key, role, slot)] = Seat(block.key, role, slot, None)
                    continue
                _, chosen = min(candidates)
                seats[(block.key, role, slot)] = Seat(block.key, role, slot, chosen)
                taken[chosen].append(block)

    _improve(seats, by_key, people, taken)
    ordered = sorted(
        seats.values(),
        key=lambda s: (
            by_key[s.block].day,
            by_key[s.block].start,
            by_key[s.block].piste,
            s.role,
            s.slot,
        ),
    )
    conflicts = tuple(
        (s.official, s.block)
        for s in ordered
        if s.official is not None
        and people[s.official].club
        and people[s.official].club in by_key[s.block].clubs
    )
    return Result(seats=tuple(ordered), conflicts=conflicts)


def _total(
    seats: dict[tuple[str, str, int], Seat], by_key: dict[str, Block], people: dict[int, Official]
) -> int:
    total = 0
    loads: dict[int, int] = {}
    for seat in seats.values():
        if seat.official is None:
            continue
        block = by_key[seat.block]
        official = people[seat.official]
        if official.club and official.club in block.clubs:
            total += CLUB
        loads[seat.official] = loads.get(seat.official, 0) + block.end - block.start
    # an even load: the sum of squares grows with imbalance
    total += sum(minutes * minutes for minutes in loads.values()) // 60
    return total


def _improve(
    seats: dict[tuple[str, str, int], Seat],
    by_key: dict[str, Block],
    people: dict[int, Official],
    taken: dict[int, list[Block]],
) -> None:
    """Swap two officials' seats while the total penalty drops."""
    for _ in range(MAX_SWAPS):
        best: tuple[int, tuple[str, str, int], tuple[str, str, int]] | None = None
        current = _total(seats, by_key, people)
        keys = sorted(k for k, s in seats.items() if s.official is not None and not s.pinned)
        for i, ka in enumerate(keys):
            for kb in keys[i + 1 :]:
                a, b = seats[ka], seats[kb]
                if a.official is None or b.official is None or a.official == b.official:
                    continue
                if not _swappable(a, b, by_key, people, taken):
                    continue
                trial = dict(seats)
                trial[ka] = Seat(a.block, a.role, a.slot, b.official)
                trial[kb] = Seat(b.block, b.role, b.slot, a.official)
                gain = current - _total(trial, by_key, people)
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, ka, kb)
        if best is None:
            return
        _, ka, kb = best
        a, b = seats[ka], seats[kb]
        if a.official is None or b.official is None:
            return
        taken[a.official].remove(by_key[a.block])
        taken[b.official].remove(by_key[b.block])
        taken[a.official].append(by_key[b.block])
        taken[b.official].append(by_key[a.block])
        seats[ka] = Seat(a.block, a.role, a.slot, b.official)
        seats[kb] = Seat(b.block, b.role, b.slot, a.official)


def _swappable(
    a: Seat,
    b: Seat,
    by_key: dict[str, Block],
    people: dict[int, Official],
    taken: dict[int, list[Block]],
) -> bool:
    if a.official is None or b.official is None:
        return False
    oa, ob = people[a.official], people[b.official]
    block_a, block_b = by_key[a.block], by_key[b.block]
    rest_a = [x for x in taken[oa.id] if x.key != block_a.key]
    rest_b = [x for x in taken[ob.id] if x.key != block_b.key]
    return (
        hard_ok(oa, block_b, b.role, rest_a) is None
        and hard_ok(ob, block_a, a.role, rest_b) is None
        and block_b not in rest_a
        and block_a not in rest_b
    )
