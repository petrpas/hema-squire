"""Fighters-index access for HR binding.

The real implementation (hemaratings.com download, cache, refresh) is task 1.4;
until it lands the app runs on StubHRIndex. The FastAPI dependency `get_hr_index`
is the single swap point.
"""

import unicodedata
from typing import Protocol

from pydantic import BaseModel


class HRProfile(BaseModel):
    hr_id: int
    name: str
    nationality: str | None
    club: str | None


class HRIndex(Protocol):
    def search(self, query: str) -> list[HRProfile]: ...

    def get(self, hr_id: int) -> HRProfile | None: ...


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


class StubHRIndex:
    """Diacritics-insensitive substring search over a fixture dataset."""

    def __init__(self, profiles: list[HRProfile]):
        self._profiles = profiles

    def search(self, query: str) -> list[HRProfile]:
        needle = _fold(query.strip())
        if len(needle) < 3:
            return []
        return [p for p in self._profiles if needle in _fold(p.name)][:20]

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


def get_hr_index() -> HRIndex:
    return _stub
