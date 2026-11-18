"""Response models for the floor's endpoints, mirroring `app.floor.roster`."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


class FloorDisciplineOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: Literal["individual", "team"]
    weapon: str = ""
    team_min: int | None = None
    team_max: int | None = None


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
    # each member's (rating, rank), parallel to `members`
    ratings: list[tuple[float | None, int | None]] = []


class FloorRosterOut(BaseModel):
    date: date
    timezone: str
    disciplines: list[FloorDisciplineOut]
    persons: list[FloorPersonOut]
    individuals: list[FloorIndividualEntryOut]
    teams: list[FloorTeamEntryOut]


# A stored row's id in a path: bounded, so an out-of-range number answers 422
# rather than overflowing SQLite's integer (as `app.fieldtypes.RowId`, which the
# floor boundary keeps out of reach).
RowId = Annotated[int, Field(ge=1, le=2**63 - 1)]


# ------------------------------------------------------------ floor Setup
# (spec floor-setup). Times are wall-clock "HH:MM" in the tournament's zone.


def _clock(value: str) -> str:
    hours, _, mins = value.partition(":")
    if not (hours.isdigit() and mins.isdigit() and int(hours) < 24 and int(mins) < 60):
        raise ValueError("invalid_time")
    return value


# "HH:MM", checked by the validator rather than a pattern: the contract
# fuzzer filters a pattern-bound field too often to fill a list of days
Clock = Annotated[str, StringConstraints(min_length=5, max_length=5), AfterValidator(_clock)]
Minutes = Annotated[int, Field(ge=1, le=600)]
Points = Annotated[int, Field(ge=1, le=99)]
Referees = Annotated[int, Field(ge=1, le=9)]


class ScopeIO(BaseModel):
    """What the floor plans (spec floor-setup, Scope decides what is planned)."""

    model_config = ConfigDict(extra="forbid")

    plan_schedule: bool = True
    multi_day: bool = False
    plan_officials: bool = False


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
    # the disciplines held that day; each belongs to exactly one day
    discipline_ids: list[int] = []


class DaysOut(BaseModel):
    # False where nothing is stored and `days` is the offered default
    stored: bool
    days: list[DayIO]


class ServesIO(BaseModel):
    """A piste or an official serves a discipline, as regular or as reserve."""

    model_config = ConfigDict(extra="forbid")

    discipline_id: int
    reserve: bool = False


class PisteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # absent for a piste added in this save
    id: int | None = None
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    serves: list[ServesIO] = []


class PisteOut(PisteIn):
    pass


class FormatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discipline_id: int
    pool_min: Annotated[int, Field(ge=3, le=10)]
    pool_max: Annotated[int, Field(ge=3, le=10)]
    # None is "all"
    advance: Annotated[int, Field(ge=2)] | None
    third_place: bool = True
    referees_pool: Referees = 1
    referees_elim: Referees = 1
    slot_pool_bout: Minutes
    slot_elim_bout: Minutes
    pause_between_pools: Minutes = 10
    slot_team_match: Minutes | None = None
    points_pool: Points | None = None
    points_elim: Points | None = None
    points_final: Points | None = None
    points_team_bout: Points | None = None
    points_team_final: Points | None = None
    # the discipline whose pool results this one takes over
    takes_pools_from: int | None = None


class FormatOut(FormatIn):
    stored: bool
    # what Setup names missing for this discipline: "format", "take_over"
    missing: list[str]


class OfficialIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    # with a person link the person's name is used, whatever is sent
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    person_key: Annotated[str, StringConstraints(max_length=80)] | None = None
    main: bool = True
    serves: list[ServesIO] = []
    days: list[date] = []


class OfficialOut(OfficialIn):
    # the link names a person no longer on the floor roster
    link_lost: bool


Finals = Literal["elimination", "day", "tournament"]


class ParamsIO(BaseModel):
    """Setup's parameters (spec floor-setup, Parameters have a default and one
    editor). Unknown keys are refused; an absent key reads as its default."""

    model_config = ConfigDict(extra="forbid")

    finals: Finals = "elimination"
    min_rest_minutes: Annotated[int, Field(ge=0, le=240)] = 10


class PreferencesIO(BaseModel):
    """The plan's preferences, edited on the `plan` tab (spec floor-plan, The
    plan's preferences are edited on the Plan tab)."""

    model_config = ConfigDict(extra="forbid")

    pool_size: Literal["larger", "smaller"] = "larger"
    club_weight: Annotated[int, Field(ge=0, le=100)] = 10
    nationality_weight: Annotated[int, Field(ge=0, le=100)] = 3


class FloorSetupDisciplineOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: Literal["individual", "team"]
    weapon: str = ""
    team_min: int | None = None


class FloorPersonRefOut(BaseModel):
    key: str
    name: str


class FloorSetupOut(BaseModel):
    disciplines: list[FloorSetupDisciplineOut]
    # who an official may be linked to
    persons: list[FloorPersonRefOut]
    scope: ScopeIO
    days: DaysOut
    pistes: list[PisteOut]
    formats: list[FormatOut]
    officials: list[OfficialOut]
    params: ParamsIO
    preferences: PreferencesIO


class FloorSummaryOut(BaseModel):
    """What the console's rail needs: which tabs wait, whether a plan is
    published, and whether a schedule is planned at all (design
    add-floor-console D6, rework-floor-setup D1)."""

    plan_published: bool
    badges: dict[str, bool]
    # Setup's waiting conditions, named: "days", "day:<discipline id>",
    # "piste:<discipline id>", "format:<discipline id>", "take_over:<discipline id>"
    setup_missing: list[str]
    plan_schedule: bool = True


# ------------------------------------------------------------ the plan
# (spec floor-plan). Dates are "YYYY-MM-DD", times "HH:MM" in the tournament's zone.


class PlanChoiceOut(BaseModel):
    discipline_id: int
    # 0 for a discipline that takes over: it has no pools
    k: int
    # None in a plan made without a schedule
    day: date | None
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


class MainWarningOut(BaseModel):
    day: date
    at: str
    # pistes running beyond the day's main referees
    short: int


class PlanMetricsOut(BaseModel):
    last_end: dict[str, str]
    exclusion_load: int
    collisions: int
    shortage: int
    average_pool: float
    reserve_used: list[int] = []
    main_warnings: list[MainWarningOut] = []


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
    """A decision to fix. `value` by kind: k {"k"}, place {"piste", "day",
    "start"}, sequence {"day", "disciplines"}. A discipline's day is Setup's,
    not a pin (spec floor-plan, Decisions are pinned and unpinned)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["k", "place", "sequence"]
    target: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    value: dict[str, object]


class PinOut(BaseModel):
    id: int
    # "n" is check-in's own pin: a closed discipline's N, added by its gate
    kind: Literal["day", "k", "place", "sequence", "n"]
    target: str
    value: dict[str, object]
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


# ------------------------------------------------------------ check-in and today
# (specs floor-checkin, floor-today)


class DeskEntryOut(BaseModel):
    entry_key: str
    discipline_id: int
    # the team's name where this is a team's entry
    team: str | None
    paid: bool
    withdrawn: bool


class DeskPersonOut(BaseModel):
    key: str
    name: str
    club: str | None
    nationality: str | None
    # a floor-only person, named at the desk
    local: bool
    arrived: bool
    entries: list[DeskEntryOut]


class DeskDisciplineOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: Literal["individual", "team"]
    team_min: int | None
    team_max: int | None
    closed: bool
    closed_at: datetime | None
    entered: int
    present: int
    n: int | None


class DeskTeamOut(BaseModel):
    key: str
    discipline_id: int
    name: str
    members: list[str]
    lineup: list[str]
    present: bool
    short_by: int
    withdrawn: bool


class DeskOut(BaseModel):
    persons: list[DeskPersonOut]
    disciplines: list[DeskDisciplineOut]
    teams: list[DeskTeamOut]


class PersonKeyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_key: Annotated[str, StringConstraints(min_length=1, max_length=80)]


class EntryKeyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_key: Annotated[str, StringConstraints(min_length=1, max_length=120)]


class LineupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_keys: list[Annotated[str, StringConstraints(min_length=1, max_length=80)]]


class LocalPersonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    club: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    nationality: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = (
        None
    )


class LocalPersonOut(BaseModel):
    key: str


class CloseImpactOut(BaseModel):
    n: int
    n_pool: int
    feasible: bool
    k: int | None = None
    sizes: list[int] = []
    published_k: int | None = None
    # the format's range, where no k fits the new N
    range: list[int] | None = None
    day: str | None = None
    # minutes; negative is earlier; None without a published plan to compare
    end_change: int | None = None


class ReopenPreviewOut(BaseModel):
    invalidated: list[str]
    refusals: list[str]


class TodayRowOut(BaseModel):
    discipline_id: int
    slug: str
    name: str
    steps: dict[str, str]
    # minutes behind (positive) or ahead of the published plan; None until progress exists
    slip: int | None
    # the discipline whose pools this one takes over; its Skupiny cell names it
    takes_pools_from: int | None = None


class WaitingOut(BaseModel):
    tab: str
    discipline: str | None
    code: str


class TodayOut(BaseModel):
    rows: list[TodayRowOut]
    waiting: list[WaitingOut]
