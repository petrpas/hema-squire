"""The Data sheet's HTTP surface (spec floor-data; design floor-data-sheet D6).

Every write is the floor's own: nothing here reaches the office.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.auth import require_console_access, require_published
from app.errors import FieldValidationError
from app.floor import datasheet, sheetview
from app.floor.adapters.office import (
    FencerDep,
    HRFetcher,
    SessionDep,
    TournamentDep,
    get_hr_fetcher,
    has_floor,
)
from app.floor.datasheet import NewPerson
from app.floor.schemas import RowId

router = APIRouter(prefix="/api/tournaments", tags=["floor"])

FetcherDep = Annotated[HRFetcher, Depends(get_hr_fetcher)]
Key = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Club = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Nationality = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]
HrId = Annotated[int, Field(ge=1, le=2**31 - 1)]


class SheetPersonOut(BaseModel):
    person: str
    entry_key: str
    name: str
    club: str | None
    nationality: str | None
    hr_id: int | None
    rating: float | None
    rank: int | None
    local: bool
    edited: list[str]


class SheetRowOut(SheetPersonOut):
    paid: bool | None
    withdrawn: bool
    added: bool


class SheetTeamOut(BaseModel):
    key: str
    name: str
    paid: bool | None
    withdrawn: bool
    added: bool
    members: list[SheetPersonOut]


class SheetDisciplineOut(BaseModel):
    id: int
    slug: str
    name: str
    kind: str
    team_min: int | None
    team_max: int | None


class SheetPersonRefOut(BaseModel):
    key: str
    name: str
    club: str | None


class SheetOut(BaseModel):
    discipline: SheetDisciplineOut
    closed_at: datetime | None
    fetched_at: datetime | None
    missing: int
    count: int
    rows: list[SheetRowOut]
    teams: list[SheetTeamOut]
    persons: list[SheetPersonRefOut]


class CellIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: Key
    field: Annotated[str, StringConstraints(min_length=1, max_length=16)]
    # a string for a person's text cell, a number for hr_id, rating and rank;
    # null or "" returns the cell to what lies beneath it
    value: str | float | int | None = None


class NewPersonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    club: Club | None = None
    nationality: Nationality | None = None
    hr_id: HrId | None = None


class EntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_key: Key | None = None
    person: NewPersonIn | None = None


class MemberIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_key: Key | None = None
    person: NewPersonIn | None = None


class TeamIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    members: Annotated[list[MemberIn], Field(max_length=20)]


class AddedOut(BaseModel):
    key: str


class RefreshOut(BaseModel):
    ratings: int
    fencers: int


_NOT_FOUND = {"discipline_not_found", "subject_not_found", "person_not_found", "not_added"}


def _refused(error: datasheet.Refused) -> Exception:
    if error.code in _NOT_FOUND:
        return HTTPException(status_code=404, detail=error.code)
    if error.code == "invalid_team" and isinstance(error.detail, list):
        return FieldValidationError(error.detail)
    if error.code in ("invalid", "required", "unknown_field"):
        return FieldValidationError([{"field": "value", "code": error.code, "params": {}}])
    if error.code == "fetch_failed":
        return HTTPException(status_code=502, detail=error.code)
    return HTTPException(status_code=409, detail=error.code)


def _writable(tournament: TournamentDep) -> None:
    if not has_floor(tournament):
        raise HTTPException(status_code=404, detail="floor_not_found")
    require_published(tournament)


def _new(person: NewPersonIn) -> NewPerson:
    return NewPerson(
        name=person.name,
        club=person.club or None,
        nationality=person.nationality or None,
        hr_id=person.hr_id,
    )


def _one(person_key: str | None, person: NewPersonIn | None) -> str | NewPerson:
    if person_key is not None and person is None:
        return person_key
    if person is not None and person_key is None:
        return _new(person)
    raise FieldValidationError([{"field": "person_key", "code": "one_of", "params": {}}])


@router.get("/{slug}/floor/sheet/{discipline_id}", response_model=SheetOut)
def sheet(
    discipline_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> SheetOut:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    found = datasheet.roster(session, tournament)
    discipline = next((d for d in found.disciplines if d.id == discipline_id), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    return SheetOut.model_validate(sheetview.view(session, tournament.id, found, discipline))


@router.put("/{slug}/floor/sheet/cells", status_code=204)
def set_cell(
    data: CellIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    try:
        datasheet.set_cell(
            session,
            tournament.id,
            datasheet.roster(session, tournament),
            data.subject,
            data.field,
            data.value,
            fencer.id,
            datetime.now(UTC),
        )
    except datasheet.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post(
    "/{slug}/floor/sheet/{discipline_id}/entries", response_model=AddedOut, status_code=201
)
def add_entry(
    discipline_id: RowId,
    data: EntryIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> AddedOut:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    try:
        key = datasheet.add_entry(
            session,
            tournament.id,
            datasheet.roster(session, tournament),
            discipline_id,
            _one(data.person_key, data.person),
            fencer.id,
            datetime.now(UTC),
        )
    except datasheet.Refused as error:
        raise _refused(error) from None
    session.commit()
    return AddedOut(key=key)


@router.delete("/{slug}/floor/sheet/{discipline_id}/entries/{person_key}", status_code=204)
def remove_entry(
    discipline_id: RowId,
    person_key: str,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> None:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    try:
        datasheet.remove_entry(session, tournament.id, discipline_id, person_key)
    except datasheet.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post("/{slug}/floor/sheet/{discipline_id}/teams", response_model=AddedOut, status_code=201)
def add_team(
    discipline_id: RowId,
    data: TeamIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> AddedOut:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    members = [_one(m.person_key, m.person) for m in data.members]
    try:
        key = datasheet.add_team(
            session,
            tournament.id,
            datasheet.roster(session, tournament),
            discipline_id,
            data.name,
            members,
            fencer.id,
            datetime.now(UTC),
        )
    except datasheet.Refused as error:
        session.rollback()
        raise _refused(error) from None
    session.commit()
    return AddedOut(key=key)


@router.delete("/{slug}/floor/sheet/{discipline_id}/teams/{team_key}", status_code=204)
def remove_team(
    discipline_id: RowId,
    team_key: str,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> None:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    try:
        datasheet.remove_team(session, tournament.id, team_key)
    except datasheet.Refused as error:
        raise _refused(error) from None
    session.commit()


@router.post("/{slug}/floor/sheet/{discipline_id}/ratings", response_model=RefreshOut)
def refresh(
    discipline_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    fetcher: FetcherDep,
) -> RefreshOut:
    require_console_access(session, tournament, fencer)
    _writable(tournament)
    try:
        outcome = datasheet.refresh(
            session,
            tournament,
            datasheet.roster(session, tournament),
            discipline_id,
            fetcher,
            datetime.now(UTC),
        )
    except datasheet.Refused as error:
        raise _refused(error) from None
    session.commit()
    return RefreshOut(**outcome)
