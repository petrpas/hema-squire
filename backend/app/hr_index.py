"""Fighters-index access for HR binding, matching, and search.

The index is DB-backed (task 1.4): populated by hr_sync.refresh_fighters,
auto-populated in the background when empty at startup, manually refreshable.
StubHRIndex remains the fixture implementation tests override with. The
FastAPI dependency `get_hr_index` is the single swap point.
"""

import unicodedata
from difflib import SequenceMatcher
from typing import Annotated, Protocol

import pycountry
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import HRFighter


class HRProfile(BaseModel):
    hr_id: int
    name: str
    nationality: str | None
    club: str | None
    # true when some account already binds this hr_id (design D1); filled in
    # by the /api/hr/search endpoint, not by HRIndex itself.
    claimed: bool = False


class HRRating(BaseModel):
    rating: float | None
    rank: int | None


class HRIndex(Protocol):
    def search(self, query: str, nationality: str | None = None) -> list[HRProfile]: ...

    def get(self, hr_id: int) -> HRProfile | None: ...

    def by_name_key(self, name: str) -> list[HRProfile]: ...

    def nationalities(self) -> list[str]: ...


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def name_key(text: str) -> tuple[str, ...]:
    """A name reduced to its folded words, order disregarded: "Jan Novák" and
    "Novák Jan" are one person under two conventions and share a key.

    Not a subset test — a word one name carries and the other does not makes
    two keys, so "Jan Petr Novák" and "Jan Novák" do not agree (spec
    table-import, LLM matching to HEMA Ratings).
    """
    return tuple(sorted(word for word in fold(text or "").split() if word))


# The registration and the index name a country in different vocabularies: a
# registration writes an ISO code ("CZ", "DE"), the index writes an English name
# ("Czech Republic", "Germany"). Nothing compares them as strings — "DE" is not a
# prefix of "Germany" — so both sides resolve to a country first.
#
# Names ISO 3166 records differently from the way the index spells them. Kept as
# an explicit list rather than reached for by fuzzy search: a wrongly resolved
# country quietly demotes a good match.
_COUNTRY_ALIASES = {
    "russia": "RU",
    "turkey": "TR",
    "palestine": "PS",
    # ISO 3166 knows one country here and it is GB. The index's own flag code
    # spells it "UK", and a fencer writes whichever of these they think of;
    # none of them may read as a different country from the others.
    "uk": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
}


def country_code(text: str | None) -> str | None:
    """The ISO 3166 alpha-2 of a country named in any vocabulary — either code,
    English name, or official name — or None where the text names no country we
    can identify.

    Two characters, the vocabulary registrations are written in.
    """
    if not text or not text.strip():
        return None
    folded = fold(text).strip()
    for candidate in (text.strip(), folded):
        try:
            return pycountry.countries.lookup(candidate).alpha_2
        except LookupError:
            pass
    return _COUNTRY_ALIASES.get(folded)


def evidence_fields(profile: HRProfile | None) -> dict[str, str | None]:
    """A profile as the evidence register carries it.

    The nationality is stated as its two-letter ISO code rather than in the
    index's own English spelling: the register sits beside a claim written in
    those codes, and a reader comparing "PL" against "Poland" is reading a
    difference that is not there. Where no country can be identified the index's own words stand — a
    spelling we cannot read is still the evidence we have.
    """
    if profile is None:
        return {"hr_name": None, "hr_nationality": None, "hr_club": None}
    return {
        "hr_name": profile.name,
        "hr_nationality": country_code(profile.nationality) or profile.nationality,
        "hr_club": profile.club,
    }


def _similarity(needle: str, name_folded: str) -> float:
    """difflib ratio plus a containment bonus, so a folded substring match
    (e.g. "pascenko" in "petr pascenko") outranks a merely similar name."""
    ratio = SequenceMatcher(None, needle, name_folded).ratio()
    bonus = 0.3 if needle in name_folded else 0.0
    return ratio + bonus


def _profile(fighter: HRFighter) -> HRProfile:
    return HRProfile(
        hr_id=fighter.hr_id,
        name=fighter.name,
        nationality=fighter.nationality or None,
        club=fighter.club or None,
    )


class DbHRIndex:
    """Diacritics-insensitive, nationality-filterable, similarity-ranked
    search over the hr_fighters table."""

    def __init__(self, session: Session):
        self._session = session

    def search(self, query: str, nationality: str | None = None) -> list[HRProfile]:
        needle = fold(query.strip())
        if len(needle) < 3:
            return []
        stmt = select(HRFighter)
        if nationality:
            stmt = stmt.where(HRFighter.nationality == nationality)
        else:
            # unfiltered index can be thousands of rows; narrow to rows
            # sharing a query token before scoring every one (design D4).
            tokens = [t for t in needle.split() if t]
            stmt = stmt.where(or_(*[HRFighter.name_folded.contains(t) for t in tokens]))
        fighters = self._session.scalars(stmt).all()
        ranked = sorted(
            fighters, key=lambda f: _similarity(needle, f.name_folded), reverse=True
        )
        return [_profile(f) for f in ranked[:20]]

    def get(self, hr_id: int) -> HRProfile | None:
        fighter = self._session.get(HRFighter, hr_id)
        return _profile(fighter) if fighter else None

    def by_name_key(self, name: str) -> list[HRProfile]:
        """Every fighter carrying this name key. The substring conditions only
        narrow the scan — a token is a substring of longer names too — and the
        key comparison decides."""
        key = name_key(name)
        if not key:
            return []
        stmt = select(HRFighter)
        for token in key:
            stmt = stmt.where(HRFighter.name_folded.contains(token))
        return [
            _profile(f) for f in self._session.scalars(stmt) if name_key(f.name) == key
        ]

    def nationalities(self) -> list[str]:
        rows = self._session.scalars(
            select(HRFighter.nationality)
            .where(HRFighter.nationality.isnot(None), HRFighter.nationality != "")
            .distinct()
            .order_by(HRFighter.nationality)
        )
        return list(rows)

    def count(self) -> int:
        return self._session.scalar(select(func.count(HRFighter.hr_id))) or 0


class StubHRIndex:
    """Fixture implementation for tests."""

    def __init__(self, profiles: list[HRProfile]):
        self._profiles = profiles

    def search(self, query: str, nationality: str | None = None) -> list[HRProfile]:
        needle = fold(query.strip())
        if len(needle) < 3:
            return []
        candidates = self._profiles
        if nationality:
            candidates = [p for p in candidates if p.nationality == nationality]
        else:
            tokens = [t for t in needle.split() if t]
            candidates = [p for p in candidates if any(t in fold(p.name) for t in tokens)]
        ranked = sorted(
            candidates, key=lambda p: _similarity(needle, fold(p.name)), reverse=True
        )
        return ranked[:20]

    def get(self, hr_id: int) -> HRProfile | None:
        return next((p for p in self._profiles if p.hr_id == hr_id), None)

    def by_name_key(self, name: str) -> list[HRProfile]:
        key = name_key(name)
        return [p for p in self._profiles if key and name_key(p.name) == key]

    def nationalities(self) -> list[str]:
        return sorted({p.nationality for p in self._profiles if p.nationality})


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
