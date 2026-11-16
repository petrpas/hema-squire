"""What the floor knows about a tournament's entrants (spec floor-roster).

The port: frozen dataclasses and nothing else. It imports nothing from `app`,
so every floor module can depend on it and none of them learns the office's
shape through it. `adapters/office.py` is what fills it.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

DisciplineKind = Literal["individual", "team"]


@dataclass(frozen=True)
class FloorDiscipline:
    # the discipline's stable id: floor tables refer to it, never to the slug,
    # which stays editable until someone enters (design add-floor-console D2)
    id: int
    slug: str
    name: str
    kind: DisciplineKind


@dataclass(frozen=True)
class Person:
    """One human. `key` is the replay row id of the person's anchor row —
    `reg:`, `imp:`, `man:` or `mem:` (design add-floor-boundary D2, D3)."""

    key: str
    name: str
    club: str | None
    nationality: str | None
    hr_id: int | None


@dataclass(frozen=True)
class IndividualEntry:
    # a `Person.key`
    person: str
    # the discipline's slug
    discipline: str
    # as the replay states them for this discipline; None where it states none
    rating: float | None
    rank: int | None
    # the entering registration is settled
    paid: bool


@dataclass(frozen=True)
class TeamEntry:
    # `team:<team id>`: the team's own identity, never its name
    key: str
    discipline: str
    name: str
    # `Person.key`s of the current members, in roster order
    members: tuple[str, ...]
    paid: bool


@dataclass(frozen=True)
class Roster:
    """A tournament's seated entrants. The order of the tuples carries no
    meaning: seeding belongs to the floor."""

    # the tournament's date and IANA timezone, for the day's wall-clock times
    date: date
    timezone: str
    disciplines: tuple[FloorDiscipline, ...]
    persons: tuple[Person, ...]
    individuals: tuple[IndividualEntry, ...]
    teams: tuple[TeamEntry, ...]
