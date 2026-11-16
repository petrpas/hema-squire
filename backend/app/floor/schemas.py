"""Response models for the floor's endpoints, mirroring `app.floor.roster`."""

from typing import Literal

from pydantic import BaseModel


class FloorDisciplineOut(BaseModel):
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
    disciplines: list[FloorDisciplineOut]
    persons: list[FloorPersonOut]
    individuals: list[FloorIndividualEntryOut]
    teams: list[FloorTeamEntryOut]
