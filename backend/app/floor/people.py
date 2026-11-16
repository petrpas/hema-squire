"""Who the floor works with (design add-floor-checkin D1, D2).

The one place persons and entrants are read above the roster port:
`persons` merges the port's persons with the floor's own floor-only persons,
and `entrants` answers a discipline's entrants live before its check-in
closes and from its snapshot after. No consumer cares where a person came
from; this is also the seam a second roster adapter will use.
"""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.floor.models import (
    FloorArrival,
    FloorLineup,
    FloorLocalPerson,
    FloorSnapshot,
    FloorSnapshotEntrant,
    FloorWithdrawal,
)
from app.floor.roster import FloorDiscipline, Person, Roster, TeamEntry

LOCAL = "local:"


@dataclass(frozen=True)
class Entrant:
    """One entrant of a discipline: a person, or a team with its members."""

    key: str
    kind: Literal["person", "team"]
    name: str
    club: str | None
    nationality: str | None
    hr_id: int | None
    rating: float | None
    rank: int | None
    paid: bool
    # a team's members, person keys in lineup order
    members: tuple[str, ...] = ()


def entry_key(person: str, discipline: int) -> str:
    return f"{person}@{discipline}"


def persons(session: Session, tid: int, roster: Roster) -> dict[str, Person]:
    found = {person.key: person for person in roster.persons}
    for local in session.scalars(
        select(FloorLocalPerson).where(FloorLocalPerson.tournament_id == tid)
    ):
        key = f"{LOCAL}{local.id}"
        found[key] = Person(
            key=key, name=local.name, club=local.club, nationality=local.nationality, hr_id=None
        )
    return found


def lineups(session: Session, tid: int) -> dict[str, tuple[str, ...]]:
    """Each team's stated lineup; a team absent fields its roster members."""
    out: dict[str, list[str]] = {}
    for row in session.scalars(
        select(FloorLineup).where(FloorLineup.tournament_id == tid).order_by(FloorLineup.ordinal)
    ):
        out.setdefault(row.team_key, []).append(row.person_key)
    return {team: tuple(keys) for team, keys in out.items()}


def lineup_of(team: TeamEntry, stated: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return stated.get(team.key, team.members)


def withdrawn(session: Session, tid: int) -> set[str]:
    return set(
        session.scalars(
            select(FloorWithdrawal.entry_key).where(FloorWithdrawal.tournament_id == tid)
        )
    )


def arrived(session: Session, tid: int) -> set[str]:
    return set(
        session.scalars(select(FloorArrival.person_key).where(FloorArrival.tournament_id == tid))
    )


def snapshot(session: Session, tid: int, discipline: int) -> FloorSnapshot | None:
    return session.scalar(
        select(FloorSnapshot).where(
            FloorSnapshot.tournament_id == tid, FloorSnapshot.discipline_id == discipline
        )
    )


def live(session: Session, tid: int, roster: Roster, discipline: FloorDiscipline) -> list[Entrant]:
    """The discipline's entrants as the roster states them now, less the
    withdrawn; a team with its day's lineup."""
    people = persons(session, tid, roster)
    gone = withdrawn(session, tid)
    if discipline.kind == "team":
        stated = lineups(session, tid)
        return [
            Entrant(
                key=team.key,
                kind="team",
                name=team.name,
                club=None,
                nationality=None,
                hr_id=None,
                rating=None,
                rank=None,
                paid=team.paid,
                members=lineup_of(team, stated),
            )
            for team in roster.teams
            if team.discipline == discipline.slug and team.key not in gone
        ]
    out: list[Entrant] = []
    for entry in roster.individuals:
        if entry.discipline != discipline.slug:
            continue
        if entry_key(entry.person, discipline.id) in gone:
            continue
        person = people[entry.person]
        out.append(
            Entrant(
                key=person.key,
                kind="person",
                name=person.name,
                club=person.club,
                nationality=person.nationality,
                hr_id=person.hr_id,
                rating=entry.rating,
                rank=entry.rank,
                paid=entry.paid,
            )
        )
    return out


def present(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> list[Entrant]:
    """Those who would fence if check-in closed now: arrived and not
    withdrawn; a team with at least its minimum of arrived lineup members,
    fielding the arrived ones."""
    here = arrived(session, tid)
    found = live(session, tid, roster, discipline)
    if discipline.kind != "team":
        return [e for e in found if e.key in here]
    least = discipline.team_min or 1
    out: list[Entrant] = []
    for team in found:
        members = tuple(key for key in team.members if key in here)
        if len(members) >= least:
            out.append(
                Entrant(
                    key=team.key,
                    kind="team",
                    name=team.name,
                    club=None,
                    nationality=None,
                    hr_id=None,
                    rating=None,
                    rank=None,
                    paid=team.paid,
                    members=members,
                )
            )
    return out


def entrants(
    session: Session, tid: int, roster: Roster, discipline: FloorDiscipline
) -> list[Entrant]:
    """The discipline's entrants: live before its check-in closes, its
    snapshot after."""
    closed = snapshot(session, tid, discipline.id)
    if closed is None:
        return live(session, tid, roster, discipline)
    return [
        Entrant(
            key=row.entrant_key,
            kind="team" if row.kind == "team" else "person",
            name=row.name,
            club=row.club,
            nationality=row.nationality,
            hr_id=row.hr_id,
            rating=row.rating,
            rank=row.rank,
            # the snapshot keeps who fences, not who paid
            paid=True,
            members=tuple(row.members),
        )
        for row in session.scalars(
            select(FloorSnapshotEntrant)
            .where(FloorSnapshotEntrant.snapshot_id == closed.id)
            .order_by(FloorSnapshotEntrant.id)
        )
    ]
