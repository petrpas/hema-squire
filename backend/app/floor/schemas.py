"""Response models for the floor's endpoints, mirroring `app.floor.roster`."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class FloorDisciplineOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: Literal["individual", "team"]


class FloorPersonOut(BaseModel):
    key: str
    name: str
    club: str | None
    nationality: str | None
    hr_id: int | None


class FloorIndividualEntryOut(BaseModel):
    person: str
    discipline: str
    rating: float | None
    rank: int | None
    paid: bool


class FloorTeamEntryOut(BaseModel):
    key: str
    discipline: str
    name: str
    members: list[str]
    paid: bool


class FloorRosterOut(BaseModel):
    date: date
    timezone: str
    disciplines: list[FloorDisciplineOut]
    persons: list[FloorPersonOut]
    individuals: list[FloorIndividualEntryOut]
    teams: list[FloorTeamEntryOut]


# ------------------------------------------------------------ floor Setup
# (spec floor-setup). Times are wall-clock "HH:MM" in the tournament's zone.

Clock = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
Minutes = Annotated[int, Field(ge=1, le=600)]
Role = Literal["referee", "judge", "table"]


class BreakIO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: Clock
    end: Clock


class DayIO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    start: Clock
    end: Clock
    breaks: list[BreakIO] = []


class DaysOut(BaseModel):
    # False where nothing is stored and `days` is the offered default
    stored: bool
    days: list[DayIO]


class PisteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # absent for a piste added in this save
    id: int | None = None
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    reserve: bool = False
    tag: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    days: list[date]


class PisteOut(PisteIn):
    pass


class Staffing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referee: Annotated[int, Field(ge=0, le=9)] = 1
    judge: Annotated[int, Field(ge=0, le=9)] = 0
    table: Annotated[int, Field(ge=0, le=9)] = 0


class FormatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discipline_id: int
    pool_min: Annotated[int, Field(ge=3, le=10)]
    pool_max: Annotated[int, Field(ge=3, le=10)]
    # None is "all"
    advance: Annotated[int, Field(ge=2)] | None
    third_place: bool
    # None until the organizer states it; the discipline is incomplete till then
    staffing: Staffing | None
    slot_pool_bout: Minutes
    slot_elim_bout: Minutes
    slot_pool_overhead: Minutes
    slot_team_match: Minutes | None = None


class FormatOut(FormatIn):
    stored: bool
    # what Setup names missing for this discipline: "format", "staffing"
    missing: list[str]


class OfficialIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    person_key: Annotated[str, StringConstraints(max_length=80)] | None = None
    roles: list[Role]
    discipline_ids: list[int]
    days: list[date]


class OfficialOut(OfficialIn):
    # the link names a person no longer on the floor roster
    link_lost: bool


class ParamsIO(BaseModel):
    """The organizer's parameters (spec floor-setup, Parameters have a default
    and one editor). Unknown keys are refused; an absent key reads as its
    default."""

    model_config = ConfigDict(extra="forbid")

    finals_last: bool = True
    prefer_larger_pools: bool = True
    club_weight: Annotated[int, Field(ge=0, le=100)] = 10
    nationality_weight: Annotated[int, Field(ge=0, le=100)] = 3
    min_rest_minutes: Annotated[int, Field(ge=0, le=240)] = 10


class FloorSetupDisciplineOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: Literal["individual", "team"]


class FloorPersonRefOut(BaseModel):
    key: str
    name: str


class FloorSetupOut(BaseModel):
    disciplines: list[FloorSetupDisciplineOut]
    # who an official may be linked to
    persons: list[FloorPersonRefOut]
    days: DaysOut
    pistes: list[PisteOut]
    formats: list[FormatOut]
    officials: list[OfficialOut]
    params: ParamsIO


class FloorSummaryOut(BaseModel):
    """What the console's band needs: which tabs wait, and whether a plan is
    published (design add-floor-console D6)."""

    plan_published: bool
    badges: dict[str, bool]
    # Setup's waiting conditions, named: "days", "pistes", "format:<discipline id>",
    # "staffing:<discipline id>"
    setup_missing: list[str]


# ------------------------------------------------------------ the plan
# (spec floor-plan). Dates are "YYYY-MM-DD", times "HH:MM" in the tournament's zone.


class PlanChoiceOut(BaseModel):
    discipline_id: int
    k: int
    day: date
    sizes: list[int]


class PlanActivityOut(BaseModel):
    id: str
    discipline_id: int
    kind: Literal["pool", "bout"]
    ordinal: int
    round: int
    piste_id: int
    day: date
    start: str
    end: str
    final: bool
    size: int


class PlanMetricsOut(BaseModel):
    last_end: dict[str, str]
    exclusion_load: int
    collisions: int
    shortage: int
    average_pool: float


class ExclusionOut(BaseModel):
    a: int
    b: int
    parallel_waves: list[int]
    shared: int
    free_places: int


class CollisionOut(BaseModel):
    a: int
    round_a: int
    b: int
    round_b: int


class VariantOut(BaseModel):
    key: str
    choices: list[PlanChoiceOut]
    metrics: PlanMetricsOut
    exclusions: list[ExclusionOut]
    collisions: list[CollisionOut]
    activities: list[PlanActivityOut]


class InfeasibleOut(BaseModel):
    reason: Literal["structure", "pin", "rule", "overrun"]
    # a discipline id, a rule's name, a day; a pin is stated by what it fixes
    subject: str | dict[str, object]
    minutes: int
    detail: str


class VariantsOut(BaseModel):
    variants: list[VariantOut]
    infeasible: InfeasibleOut | None
    # disciplines whose k the enumeration cap fixed
    capped: list[int]
    # disciplines left out because nobody is entered yet
    empty: list[int]


class ChooseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class StoredPlanOut(BaseModel):
    version: int
    status: Literal["working", "published", "history"]
    created_at: datetime
    choices: list[PlanChoiceOut]
    metrics: PlanMetricsOut
    exclusions: list[ExclusionOut]
    collisions: list[CollisionOut]
    activities: list[PlanActivityOut]


class PinIn(BaseModel):
    """A decision to fix. `value` by kind: day {"day"}, k {"k"}, place
    {"piste", "day", "start"}, sequence {"day", "disciplines"}."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["day", "k", "place", "sequence"]
    target: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    value: dict[str, object]


class PinOut(PinIn):
    id: int
    # the gate that added it; removed only by reopening that gate
    gate: str | None


class ChangeOut(BaseModel):
    activity: str
    kind: Literal["moved", "added", "removed"]
    # (piste id, date, "HH:MM")
    before: tuple[int, str, str] | None
    after: tuple[int, str, str] | None


class ThresholdOut(BaseModel):
    discipline_id: int
    below: int | None
    above: int | None


class DayEffectOut(BaseModel):
    day: date
    one_fewer: int | None
    one_more: int | None
    two_more: int | None
    limit: Literal["pistes", "officials", "none"]


class SensitivityOut(BaseModel):
    thresholds: list[ThresholdOut]
    days: list[DayEffectOut]


class FloorPlanStateOut(BaseModel):
    working: StoredPlanOut | None
    published: StoredPlanOut | None
    history: list[int]
    diff: list[ChangeOut]
    pins: list[PinOut]
    # what stands in the way of publishing the working version
    obstacles: list[str]
    sensitivity: SensitivityOut | None
    # Setup's waiting conditions where the planner cannot run yet
    setup_missing: list[str]
