"""Fighters-index access for HR binding, matching, and search.

The index is DB-backed (task 1.4): populated by hr_sync.refresh_fighters,
auto-populated in the background when empty at startup, manually refreshable.
StubHRIndex remains the fixture implementation tests override with. The
FastAPI dependency `get_hr_index` is the single swap point.
"""

import unicodedata
from typing import Annotated, Protocol

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import HRFighter


class HRProfile(BaseModel):
    hr_id: int
    name: str
    nationality: str | None
    club: str | None


class HRRating(BaseModel):
    rating: float | None
    rank: int | None


class HRIndex(Protocol):
    def search(self, query: str) -> list[HRProfile]: ...

    def get(self, hr_id: int) -> HRProfile | None: ...


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _profile(fighter: HRFighter) -> HRProfile:
    return HRProfile(
        hr_id=fighter.hr_id,
        name=fighter.name,
        nationality=fighter.nationality or None,
        club=fighter.club or None,
    )


class DbHRIndex:
    """Diacritics-insensitive substring search over the hr_fighters table."""

    def __init__(self, session: Session):
        self._session = session

    def search(self, query: str) -> list[HRProfile]:
        needle = fold(query.strip())
        if len(needle) < 3:
            return []
        fighters = self._session.scalars(
            select(HRFighter)
            .where(HRFighter.name_folded.contains(needle))
            .order_by(HRFighter.name)
            .limit(20)
        )
        return [_profile(f) for f in fighters]

    def get(self, hr_id: int) -> HRProfile | None:
        fighter = self._session.get(HRFighter, hr_id)
        return _profile(fighter) if fighter else None

    def count(self) -> int:
        return self._session.scalar(select(func.count(HRFighter.hr_id))) or 0


class StubHRIndex:
    """Fixture implementation for tests."""

    def __init__(self, profiles: list[HRProfile]):
        self._profiles = profiles

    def search(self, query: str) -> list[HRProfile]:
        needle = fold(query.strip())
        if len(needle) < 3:
            return []
        return [p for p in self._profiles if needle in fold(p.name)][:20]

    def get(self, hr_id: int) -> HRProfile | None:
        return next((p for p in self._profiles if p.hr_id == hr_id), None)


STUB_PROFILES = [
    HRProfile(hr_id=10234, name="Jan Novák", nationality="CZE", club="Prague HEMA"),
    HRProfile(hr_id=8821, name="Lukas Mueller", nationality="DEU", club="Berlin Schwert"),
    HRProfile(hr_id=5567, name="Petr Svoboda", nationality="CZE", club="Brno Sword Club"),
    HRProfile(hr_id=3340, name="Anna Kowalska", nationality="POL", club="Krakow HEMA"),
    HRProfile(hr_id=7012, name="Tom Andersen", nationality="DNK", club="Koge Fencing"),
]

_stub = StubHRIndex(STUB_PROFILES)


def stub_index() -> HRIndex:
    return _stub


def get_hr_index(session: Annotated[Session, Depends(get_session)]) -> HRIndex:
    return DbHRIndex(session)
