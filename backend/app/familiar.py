"""Who a signed-in fencer might know at a listed tournament (spec
public-browsing, A signed-in caller is shown familiar entrants): seated
clubmates first, and where there are none, compatriots.

Everything here is already stated by the public rosters; the selection only
brings the few names that matter to one caller onto the list. Computed for a
whole list together, from the rows the list's counts already read."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.hr_index import country_code
from app.list_counts import SeatedEntrant, normalize_club
from app.models import (
    DisciplineKind,
    Fencer,
    HRFighter,
    HRRatingSnapshot,
    HRSnapshotRating,
    Tournament,
)

SHOWN = 3


@dataclass(frozen=True)
class FamiliarPerson:
    initials: str
    label: str


@dataclass(frozen=True)
class Familiar:
    basis: Literal["club", "country"]
    country: str | None
    total: int
    ranked: bool
    people: list[FamiliarPerson]


def _person(name: str) -> FamiliarPerson:
    """`Kateřina Veselá` → initials `KV`, label `Kateřina V.`: the first name
    and the surname's initial, which is what the face carries as its title."""
    parts = name.split()
    if not parts:
        return FamiliarPerson(initials="?", label=name)
    first, last = parts[0], parts[-1] if len(parts) > 1 else None
    if last is None:
        return FamiliarPerson(initials=first[:2].upper(), label=first)
    return FamiliarPerson(initials=(first[0] + last[0]).upper(), label=f"{first} {last[0]}.")


def _caller_identity(session: Session, caller: Fencer) -> tuple[str | None, str | None]:
    """The caller's normalized club and country code: the bound hemaratings
    profile's where it names them, the account's own otherwise."""
    club, nationality = caller.club, caller.nationality
    if caller.hr_id is not None:
        profile = session.get(HRFighter, caller.hr_id)
        if profile is not None:
            club = profile.club or club
            nationality = profile.nationality or nationality
    return normalize_club(club), country_code(nationality)


def _ratings(
    session: Session, tournaments: Sequence[Tournament], hr_ids: set[int]
) -> dict[int, dict[int, float]]:
    """Per tournament with a rating snapshot, each rated fencer's best rating
    across the tournament's individual disciplines. A tournament absent from
    the answer has no snapshot, and its order is by name."""
    ids = [tournament.id for tournament in tournaments]
    latest = dict(
        session.execute(
            select(HRRatingSnapshot.tournament_id, func.max(HRRatingSnapshot.id))
            .where(HRRatingSnapshot.tournament_id.in_(ids))
            .group_by(HRRatingSnapshot.tournament_id)
        )
        .tuples()
        .all()
    )
    if not latest:
        return {}
    by_snapshot: dict[int, list[tuple[int, str, float | None]]] = {}
    if hr_ids:
        for snapshot_id, hr_id, code, rating in session.execute(
            select(
                HRSnapshotRating.snapshot_id,
                HRSnapshotRating.hr_id,
                HRSnapshotRating.discipline_code,
                HRSnapshotRating.rating,
            ).where(
                HRSnapshotRating.snapshot_id.in_(latest.values()),
                HRSnapshotRating.hr_id.in_(hr_ids),
            )
        ).tuples():
            by_snapshot.setdefault(snapshot_id, []).append((hr_id, code, rating))
    ratings: dict[int, dict[int, float]] = {}
    for tournament in tournaments:
        snapshot_id = latest.get(tournament.id)
        if snapshot_id is None:
            continue
        codes = {
            d.taxonomy_code for d in tournament.disciplines if d.kind is DisciplineKind.INDIVIDUAL
        }
        best: dict[int, float] = {}
        for hr_id, code, rating in by_snapshot.get(snapshot_id, []):
            if code in codes and rating is not None:
                best[hr_id] = max(rating, best.get(hr_id, rating))
        ratings[tournament.id] = best
    return ratings


def familiar_entrants(
    session: Session,
    tournaments: Sequence[Tournament],
    seated: Mapping[int, list[SeatedEntrant]],
    caller: Fencer,
) -> dict[int, Familiar]:
    """Per tournament id, the caller's familiar entrants, absent where nobody
    matches. The caller is never their own acquaintance."""
    club, country = _caller_identity(session, caller)
    if club is None and country is None:
        return {}
    hr_ids = {e.hr_id for entrants in seated.values() for e in entrants if e.hr_id is not None}
    ratings = _ratings(session, tournaments, hr_ids)
    answer: dict[int, Familiar] = {}
    for tournament in tournaments:
        others = [e for e in seated.get(tournament.id, []) if e.fencer_id != caller.id]
        basis: Literal["club", "country"] = "club"
        matched = [e for e in others if normalize_club(e.club) == club] if club is not None else []
        if not matched and country is not None:
            basis = "country"
            matched = [e for e in others if country_code(e.nationality) == country]
        if not matched:
            continue
        rated = ratings.get(tournament.id)
        if rated is not None:
            # rated first, highest first; the unrated after them, by name
            def by_rating(
                e: SeatedEntrant, rated: dict[int, float] = rated
            ) -> tuple[bool, float, str]:
                rating = rated.get(e.hr_id) if e.hr_id is not None else None
                return (rating is None, -(rating or 0.0), e.name)

            matched.sort(key=by_rating)
        else:
            matched.sort(key=lambda e: e.name)
        answer[tournament.id] = Familiar(
            basis=basis,
            country=country if basis == "country" else None,
            total=len(matched),
            ranked=rated is not None,
            people=[_person(e.name) for e in matched[:SHOWN]],
        )
    return answer
