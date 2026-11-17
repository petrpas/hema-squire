"""The planner's model (spec floor-planner; design add-floor-planner D1,
design rework-floor-setup D8).

Frozen dataclasses only. Times are whole minutes since midnight of a day, and
days are referred to by index: the service converts to and from wall-clock
time in the tournament's zone, so the engine knows no date and no timezone.
"""

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["individual", "team"]
ActivityKind = Literal["pool", "bout"]
# an activity's stage, which sets its referees per bout
Stage = Literal["pool", "elim"]
Finals = Literal["elimination", "day", "tournament"]


@dataclass(frozen=True)
class Break:
    start: int
    end: int


@dataclass(frozen=True)
class Day:
    index: int
    start: int
    end: int
    breaks: tuple[Break, ...] = ()


@dataclass(frozen=True)
class Piste:
    """A piste and the disciplines it serves. It is usable on any day one of
    them is held; a reserve discipline uses it only where its day cannot be
    planned on the regular pistes."""

    id: int
    ordinal: int
    regular: frozenset[int] = frozenset()
    reserve: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Format:
    pool_min: int
    pool_max: int
    # None is "all"
    advance: int | None
    third_place: bool
    slot_pool_bout: int
    slot_elim_bout: int
    # the pause a piste keeps after each pool
    pause: int = 10
    slot_team_match: int | None = None
    # referees per bout: (pools, elimination)
    referees: tuple[int, int] = (1, 1)

    def referees_for(self, stage: Stage) -> int:
        return self.referees[0] if stage == "pool" else self.referees[1]


@dataclass(frozen=True)
class DisciplineFacts:
    id: int
    # what activity ids are spelled with: the slug
    key: str
    kind: Kind
    # pool participants: entrants, or a team discipline's members
    n_pool: int
    # who enters the bracket's count: entrants, or a team discipline's teams
    n_bracket: int
    format: Format
    # the day it is held on, a fact of Setup (owner decision 2026-11-17)
    day: int = 0
    # the discipline whose pools it takes over; it then has no pools
    takes_from: int | None = None


@dataclass(frozen=True)
class Params:
    finals: Finals = "elimination"
    prefer_larger_pools: bool = True
    min_rest: int = 10


@dataclass(frozen=True)
class Referees:
    """Referees available on a day: those serving one of its disciplines as
    regular, those serving only as reserve, and the main referees among all."""

    day: int
    regular: int
    reserve: int = 0
    main: int = 0


@dataclass(frozen=True)
class KPin:
    discipline: int
    k: int


@dataclass(frozen=True)
class PlacePin:
    activity: str
    piste: int
    day: int
    start: int


@dataclass(frozen=True)
class SequencePin:
    """Disciplines of one day run one after another, in this order."""

    day: int
    disciplines: tuple[int, ...]


Pin = KPin | PlacePin | SequencePin


@dataclass(frozen=True)
class Activity:
    # deterministic: "LS:pool:3", "LS:r2:1", "LS:third"
    id: str
    discipline: int
    kind: ActivityKind
    # pool number, or bout number within its round, from 1
    ordinal: int
    # 0 for a pool; elimination rounds count from 1, the final's is the last
    round: int
    piste: int
    day: int
    start: int
    end: int
    final: bool = False
    # pools only: participants in it
    size: int = 0


@dataclass(frozen=True)
class Problem:
    days: tuple[Day, ...]
    pistes: tuple[Piste, ...]
    disciplines: tuple[DisciplineFacts, ...]
    # (discipline a, discipline b, persons in both), a < b
    shared: tuple[tuple[int, int, int], ...] = ()
    # referees per day; empty means officials are not counted
    officials: tuple[Referees, ...] = ()
    pins: tuple[Pin, ...] = ()
    params: Params = field(default_factory=Params)
    # activities that have started, kept where they stand
    frozen: tuple[Activity, ...] = ()
    # False plans the pool structure only (spec floor-planner, Without a
    # schedule the planner plans pool structure only)
    schedule: bool = True


@dataclass(frozen=True)
class Choice:
    """One discipline's free decision in a variant, its k, with its day as
    Setup states it. A discipline that takes over has k = 0."""

    discipline: int
    k: int
    day: int


@dataclass(frozen=True)
class Exclusion:
    """Discipline `a`'s pool waves that run alongside discipline `b`: the
    `shared` persons of the pair must be drawn into `a`'s other waves."""

    a: int
    b: int
    parallel_waves: tuple[int, ...]
    shared: int
    # places in a's other waves; short where fewer than `shared`
    free_places: int


@dataclass(frozen=True)
class Collision:
    """Two elimination rounds of disciplines sharing persons that overlap."""

    a: int
    round_a: int
    b: int
    round_b: int


@dataclass(frozen=True)
class Metrics:
    # (day, last end) for every day of the problem; an empty day ends at its start
    last_end: tuple[tuple[int, int], ...]
    exclusion_load: int
    collisions: int
    shortage: int
    average_pool: float
    # reserve pistes the variant uses, by id
    reserve_used: tuple[int, ...] = ()
    # (day, minute, pistes beyond the day's main referees): a warning only
    main_warnings: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True)
class Plan:
    choices: tuple[Choice, ...]
    activities: tuple[Activity, ...]
    metrics: Metrics
    exclusions: tuple[Exclusion, ...]
    collisions: tuple[Collision, ...]

    @property
    def key(self) -> str:
        return ";".join(f"{c.discipline}:{c.k}@{c.day}" for c in self.choices)


@dataclass(frozen=True)
class Infeasible:
    """Why no variant exists, in one of four kinds that are never merged:
    a discipline whose structure cannot fit its format, a pin or a hard rule
    without which a variant would exist, or a day too short by `minutes`."""

    reason: Literal["structure", "pin", "rule", "overrun"]
    # a discipline id, a pin's index in `Problem.pins`, a rule name, a day index
    subject: str
    minutes: int = 0
    detail: str = ""


@dataclass(frozen=True)
class Result:
    variants: tuple[Plan, ...]
    infeasible: Infeasible | None = None
    # disciplines whose k the enumeration cap fixed, in the order it fixed them
    capped: tuple[int, ...] = ()
