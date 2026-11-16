"""The planner's model (spec floor-planner; design add-floor-planner D1).

Frozen dataclasses only. Times are whole minutes since midnight of a day, and
days are referred to by index: the service converts to and from wall-clock
time in the tournament's zone, so the engine knows no date and no timezone.
"""

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["individual", "team"]
ActivityKind = Literal["pool", "bout"]
Role = Literal["referee", "judge", "table"]


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
    id: int
    ordinal: int
    # day indexes it is available on
    days: frozenset[int]
    reserve: bool = False


@dataclass(frozen=True)
class Format:
    pool_min: int
    pool_max: int
    # None is "all"
    advance: int | None
    third_place: bool
    # officials one piste needs while this discipline runs, by role
    staffing: tuple[tuple[Role, int], ...]
    slot_pool_bout: int
    slot_elim_bout: int
    slot_pool_overhead: int
    slot_team_match: int | None = None


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


@dataclass(frozen=True)
class Params:
    finals_last: bool = True
    prefer_larger_pools: bool = True
    min_rest: int = 10


@dataclass(frozen=True)
class DayPin:
    discipline: int
    day: int


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


Pin = DayPin | KPin | PlacePin | SequencePin


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
    # (day, role, officials available); empty means officials are not counted
    officials: tuple[tuple[int, Role, int], ...] = ()
    pins: tuple[Pin, ...] = ()
    params: Params = field(default_factory=Params)
    # activities that have started, kept where they stand
    frozen: tuple[Activity, ...] = ()
    # re-planning may use reserve pistes; a first plan may not
    use_reserve: bool = False


@dataclass(frozen=True)
class Choice:
    """One discipline's free decisions in a variant."""

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
