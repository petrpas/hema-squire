"""Response models for the floor's endpoints, mirroring `app.floor.roster`."""

from datetime import date
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
