"""The public aggregates a tournament list entry states beside its disciplines:
how many fencers are seated and from how many clubs (spec public-browsing, A
list entry states its public aggregates).

Computed for a whole list in one query rather than per entry. The figures are
sums over what the public rosters already state, so they disclose nothing the
rosters do not."""

from collections import defaultdict
from collections.abc import Mapping, Sequence

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


def entrant_counts(
    session: Session,
    tournaments: Sequence[Tournament],
    removed: Mapping[int, set[int]],
) -> dict[int, tuple[int, int]]:
    """`(fencers, clubs)` per tournament id, over its seated individual
    placements: live, not queued, and not taken off the public table
    (`removed`, by tournament id). A fencer seated in two disciplines is one
    registration and counts once. Team disciplines are not counted: a team
    member has no account to be told apart by, and the team rosters state
    teams, not fencers."""
    ids = [tournament.id for tournament in tournaments]
    if not ids:
        return {}
    rows = session.execute(
        select(Registration.tournament_id, Registration.id, Fencer.club)
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
    ).all()
    fencers: dict[int, set[int]] = defaultdict(set)
    clubs: dict[int, set[str]] = defaultdict(set)
    for tournament_id, registration_id, club in rows:
        if registration_id in removed.get(tournament_id, set()):
            continue
        fencers[tournament_id].add(registration_id)
        normalized = normalize_club(club)
        if normalized is not None:
            clubs[tournament_id].add(normalized)
    return {tid: (len(fencers[tid]), len(clubs[tid])) for tid in ids}
