"""The public aggregates a tournament list entry states beside its disciplines:
how many fencers are seated and from how many clubs (spec public-browsing, A
list entry states its public aggregates).

Computed for a whole list in one query rather than per entry. The figures are
sums over what the public rosters already state, so they disclose nothing the
rosters do not."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.availability import live_registration
from app.hr_index import fold
from app.models import (
    Discipline,
    DisciplineKind,
    Fencer,
    Registration,
    RegistrationDiscipline,
    Tournament,
)


def normalize_club(club: str | None) -> str | None:
    """A club as compared, not as shown: case and diacritics folded, whitespace
    collapsed and trimmed. Clubs are free text, so this is the best identity
    there is — `SK Brno` and `Šermířský klub Brno` stay two clubs. Empty is
    none."""
    if club is None:
        return None
    normalized = " ".join(fold(club).split())
    return normalized or None


@dataclass(frozen=True)
class SeatedEntrant:
    """One fencer seated in at least one of a tournament's individual
    disciplines, as the public rosters list them."""

    registration_id: int
    fencer_id: int
    name: str
    club: str | None
    nationality: str | None
    hr_id: int | None


def seated_entrants(
    session: Session,
    tournaments: Sequence[Tournament],
    removed: Mapping[int, set[int]],
) -> dict[int, list[SeatedEntrant]]:
    """Each tournament's seated individual placements, one per fencer: live,
    not queued, and not taken off the public table (`removed`, by tournament
    id). A fencer seated in two disciplines is one registration and appears
    once. Team disciplines are left out: a team member has no account to be
    told apart by, and the team rosters state teams, not fencers. One query
    for the whole list."""
    ids = [tournament.id for tournament in tournaments]
    seated: dict[int, list[SeatedEntrant]] = {tid: [] for tid in ids}
    if not ids:
        return seated
    rows = session.execute(
        select(
            Registration.tournament_id,
            Registration.id,
            Fencer.id,
            Fencer.display_name,
            Fencer.club,
            Fencer.nationality,
            Fencer.hr_id,
        )
        .join(RegistrationDiscipline, RegistrationDiscipline.registration_id == Registration.id)
        .join(Discipline, Discipline.id == RegistrationDiscipline.discipline_id)
        .join(Fencer, Fencer.id == Registration.fencer_id)
        .where(
            Registration.tournament_id.in_(ids),
            Discipline.kind == DisciplineKind.INDIVIDUAL,
            RegistrationDiscipline.is_substitute.is_(False),
            live_registration(),
        )
        .distinct()
        .order_by(Registration.id)
    ).all()
    for tournament_id, registration_id, fencer_id, name, club, nationality, hr_id in rows:
        if registration_id in removed.get(tournament_id, set()):
            continue
        seated[tournament_id].append(
            SeatedEntrant(registration_id, fencer_id, name, club, nationality, hr_id)
        )
    return seated


def entrant_counts(seated: Mapping[int, list[SeatedEntrant]]) -> dict[int, tuple[int, int]]:
    """`(fencers, clubs)` per tournament id over its seated entrants, clubs
    compared after normalization and an empty club counting as none."""
    counts: dict[int, tuple[int, int]] = {}
    for tournament_id, entrants in seated.items():
        clubs: set[str] = set()
        for entrant in entrants:
            normalized = normalize_club(entrant.club)
            if normalized is not None:
                clubs.add(normalized)
        counts[tournament_id] = (len(entrants), len(clubs))
    return counts
