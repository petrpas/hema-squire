"""The public aggregates a tournament list entry states beside its disciplines:
how many fencers are seated and from how many clubs, and on an event the fill
of its capped program items (spec public-browsing, A list entry states its
public aggregates).

A tournament's fencers include the members of its seated teams, as its team
rosters name them; one person entered both alone and on a team, or on two
teams, is one fencer (`same_person`).

An event has no discipline to be seated in, so its fencers are those its
side-event rosters list: the people holding a place at a seminar or other
program item (spec public-entrants).

Computed for a whole list in a fixed number of queries rather than per entry. The figures are
sums over what the public rosters already state, so they disclose nothing the
rosters do not."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.availability import live_registration
from app.entrants import PUBLIC_EVENT_CATEGORIES
from app.hr_index import fold
from app.models import (
    Discipline,
    DisciplineKind,
    ExtraItem,
    Fencer,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    Team,
    TeamMember,
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


def _folded_name(name: str) -> str:
    return " ".join(fold(name).split())


class _Listed:
    """Who a tournament already lists, as a team member is told apart from
    them: one person where both are bound to the same hemaratings profile,
    and where either is bound to none, by name (folded, whitespace
    collapsed). A team member has no account, so this is the best identity a
    roster offers. Two profiles that differ are two people whatever their
    names."""

    def __init__(self) -> None:
        self._hr_ids: set[int] = set()
        # folded name → whether some entrant of that name has no profile
        self._names: dict[str, bool] = {}

    def add(self, name: str, hr_id: int | None) -> None:
        if hr_id is not None:
            self._hr_ids.add(hr_id)
        key = _folded_name(name)
        self._names[key] = self._names.get(key, False) or hr_id is None

    def holds(self, name: str, hr_id: int | None) -> bool:
        if hr_id is not None and hr_id in self._hr_ids:
            return True
        unbound = self._names.get(_folded_name(name))
        return unbound is not None and (hr_id is None or unbound)


def same_person(a_name: str, a_hr_id: int | None, b_name: str, b_hr_id: int | None) -> bool:
    """`_Listed`'s identity for one pair."""
    if a_hr_id is not None and b_hr_id is not None:
        return a_hr_id == b_hr_id
    return _folded_name(a_name) == _folded_name(b_name)


@dataclass(frozen=True)
class SeatedEntrant:
    """One fencer seated in a tournament, as the public rosters list them: in
    an individual discipline, or on a seated team's roster. A team member has
    no account, so its `fencer_id` is None."""

    registration_id: int
    fencer_id: int | None
    name: str
    club: str | None
    nationality: str | None
    hr_id: int | None


# tournament id, registration id, fencer id, name, club, nationality, HR id
_EntrantRow = tuple[int, int, int | None, str, str | None, str | None, int | None]


def seated_entrants(
    session: Session,
    tournaments: Sequence[Tournament],
    removed: Mapping[int, set[int]],
) -> dict[int, list[SeatedEntrant]]:
    """Each tournament's seated fencers: live, not queued, and not taken off
    the public table (`removed`, by tournament id). A fencer seated in two
    disciplines is one registration and appears once. The members of a seated
    team follow the individual entrants, each left out where they are already
    listed (`same_person`) — the team's own fencer seated alone, a member on
    two teams.

    An event's entrants are instead the registrations holding a place at one
    of its publicly rostered items, once each however many they hold. One
    query each for the tournaments' individuals, their team members, and the
    list's events."""
    seated: dict[int, list[SeatedEntrant]] = {tournament.id: [] for tournament in tournaments}
    tournament_ids = [t.id for t in tournaments if not t.is_event]
    event_ids = [t.id for t in tournaments if t.is_event]
    rows: list[_EntrantRow] = []
    if tournament_ids:
        rows.extend(_discipline_entrants(session, tournament_ids))
    if event_ids:
        rows.extend(_program_entrants(session, event_ids))
    for tournament_id, registration_id, fencer_id, name, club, nationality, hr_id in rows:
        if registration_id in removed.get(tournament_id, set()):
            continue
        seated[tournament_id].append(
            SeatedEntrant(registration_id, fencer_id, name, club, nationality, hr_id)
        )
    if tournament_ids:
        listed: dict[int, _Listed] = {}
        for tournament_id in tournament_ids:
            listed[tournament_id] = _Listed()
            for entrant in seated[tournament_id]:
                listed[tournament_id].add(entrant.name, entrant.hr_id)
        for tournament_id, registration_id, _, name, club, nationality, hr_id in _team_members(
            session, tournament_ids
        ):
            if registration_id in removed.get(tournament_id, set()):
                continue
            known = listed[tournament_id]
            if known.holds(name, hr_id):
                continue
            known.add(name, hr_id)
            seated[tournament_id].append(
                SeatedEntrant(registration_id, None, name, club, nationality, hr_id)
            )
    return seated


def _discipline_entrants(session: Session, ids: list[int]) -> Sequence[_EntrantRow]:
    return (
        session.execute(
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
        )
        .tuples()
        .all()
    )


def _team_members(session: Session, ids: list[int]) -> Sequence[_EntrantRow]:
    """The live members of the seated teams, as stored on their rosters, in
    entry order."""
    return (
        session.execute(
            select(
                Registration.tournament_id,
                Registration.id,
                Registration.fencer_id,
                TeamMember.name,
                TeamMember.club,
                TeamMember.nationality,
                TeamMember.hr_id,
            )
            .join(Team, Team.registration_id == Registration.id)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(
                Registration.tournament_id.in_(ids),
                Team.waitlisted.is_(False),
                TeamMember.removed_at.is_(None),
                live_registration(),
            )
            .order_by(Team.id, TeamMember.ordinal)
        )
        .tuples()
        .all()
    )


def _program_entrants(session: Session, ids: list[int]) -> Sequence[_EntrantRow]:
    return (
        session.execute(
            select(
                Registration.tournament_id,
                Registration.id,
                Fencer.id,
                Fencer.display_name,
                Fencer.club,
                Fencer.nationality,
                Fencer.hr_id,
            )
            .join(RegistrationExtra, RegistrationExtra.registration_id == Registration.id)
            .join(ExtraItem, ExtraItem.id == RegistrationExtra.extra_item_id)
            .join(Fencer, Fencer.id == Registration.fencer_id)
            .where(
                Registration.tournament_id.in_(ids),
                ExtraItem.category.in_(PUBLIC_EVENT_CATEGORIES),
                live_registration(),
            )
            .distinct()
            .order_by(Registration.id)
        )
        .tuples()
        .all()
    )


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


@dataclass(frozen=True)
class ProgramMeter:
    """One capped program item's fill on an event's card: the people its
    roster lists against its capacity."""

    item_id: int
    name: str
    entered: int
    capacity: int


def program_meters(
    session: Session,
    tournaments: Sequence[Tournament],
    removed: Mapping[int, set[int]],
) -> dict[int, list[ProgramMeter]]:
    """Per event id, a meter for each publicly rostered item that has a
    capacity, in the order the items were offered; uncapped items have none,
    and a tournament has none at all (its card meters its disciplines).

    `entered` counts what the item's roster lists — live registrations whose
    row the organizer has not taken off the public table — not what holds a
    piece of the capacity, as a discipline's card figure does (spec
    public-entrants, A count states who is shown above the line). Program
    items take one piece per registration, so registrations are pieces. Two
    queries for the whole list."""
    event_ids = [t.id for t in tournaments if t.is_event]
    meters: dict[int, list[ProgramMeter]] = {event_id: [] for event_id in event_ids}
    if not event_ids:
        return meters
    items = session.scalars(
        select(ExtraItem)
        .where(
            ExtraItem.tournament_id.in_(event_ids),
            ExtraItem.category.in_(PUBLIC_EVENT_CATEGORIES),
            ExtraItem.capacity.is_not(None),
        )
        .order_by(ExtraItem.id)
    ).all()
    if not items:
        return meters
    holders: dict[int, set[int]] = {item.id: set() for item in items}
    for tournament_id, item_id, registration_id in session.execute(
        select(Registration.tournament_id, RegistrationExtra.extra_item_id, Registration.id)
        .join(RegistrationExtra, RegistrationExtra.registration_id == Registration.id)
        .where(RegistrationExtra.extra_item_id.in_(holders), live_registration())
    ).tuples():
        if registration_id not in removed.get(tournament_id, set()):
            holders[item_id].add(registration_id)
    for item in items:
        # the query asked for capped items only; narrowed here for the checker
        if item.capacity is not None:
            meters[item.tournament_id].append(
                ProgramMeter(item.id, item.name, len(holders[item.id]), item.capacity)
            )
    return meters
