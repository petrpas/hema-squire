"""The public entrant rosters, one per discipline (spec public-entrants).

An individual roster is the discipline's Export tab narrowed to what the
public may read. It comes from the same replay the console and the printed
roster read, so the organizer's corrections and deletions and HEMA Ratings'
nationality and club stand here as they stand there (design
public-entrant-lists D1). A team roster is read from the teams themselves,
since no Export tab carries teams (D3).

Every rule that depends on the tournament is decided here, not by the client:
what the Paid cell says, what is drawn faded, and whether a queue and a line
are shown at all. A client restating the mode rules would be a second place
for them to drift (D4).
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import exporttables, rules, setup, sheet
from app.availability import (
    QUEUE_ORDER,
    live_registration,
)
from app.models import (
    Discipline,
    DisciplineKind,
    ExtraCategory,
    ExtraItem,
    Fencer,
    Registration,
    RegistrationDiscipline,
    RegistrationsKeptBy,
    Team,
    Tournament,
)
from app.rules import Row

Paid = Literal["yes", "no"] | None
RosterKind = Literal["individual", "team", "event"]

# The side events whose attendees are listed: seminars and the organizer's
# other programme. The afterparty is left out by owner decision (2026-10-11) —
# who goes drinking is not the tournament's to publish — and goods are not
# events at all.
# The frontend keeps a copy to offer an event's Entrants tab: `ROSTERED` in
# `frontend/src/TournamentDetail.tsx`.
PUBLIC_EVENT_CATEGORIES = (ExtraCategory.SEMINAR, ExtraCategory.OTHER_ACTION)


@dataclass(frozen=True)
class EntrantRow:
    number: int
    name: str
    nationality: str | None
    club: str | None
    hr_id: int | None
    paid: Paid
    faded: bool
    conditional: bool


@dataclass(frozen=True)
class TeamMemberRow:
    name: str
    nationality: str | None
    club: str | None
    hr_id: int | None


@dataclass(frozen=True)
class TeamRow:
    number: int
    name: str
    paid: Paid
    faded: bool
    members: list[TeamMemberRow]


@dataclass(frozen=True)
class Roster:
    # a discipline's slug, or a side event's item id
    slug: str
    name: str
    kind: RosterKind
    # whether the capacity line is drawn: the queue is public only where
    # Squire keeps it and the tournament has not been held
    line: bool
    seated: list[EntrantRow] | list[TeamRow] = field(default_factory=list)
    queued: list[EntrantRow] | list[TeamRow] = field(default_factory=list)
    # a side event's capacity, stated on its line where one is drawn: with no
    # queue below it, the line alone would read as if the rows above were all
    # the places there are
    capacity: int | None = None


@dataclass(frozen=True)
class _Conduct:
    """What the tournament lets a roster state."""

    # Squire collects the money: payments on, registrations kept by Squire.
    # Only there can an unsettled registration mean money is outstanding
    collects: bool
    # the queue and the capacity line are shown
    queue: bool
    # whether the obligation a seat is held under has fallen due: the seating
    # deadline has passed, or the organizer closed seating early. Asked of the
    # tournament, while the payment window is asked of each registration
    seating_settled: bool
    # registrations of deleted accounts: their rows state no payment and are
    # never faded (spec account-deletion, A deleted account's row states no
    # payment)
    deleted: frozenset[int] = frozenset()


def _conduct(tournament: Tournament, now: datetime) -> _Conduct:
    kept_by_squire = tournament.registrations_kept_by is RegistrationsKeptBy.SQUIRE
    # the boundary that splits the public tournament list (spec day-boundaries):
    # a tournament leaves Open for Past at the moment its queue disappears
    held = tournament.date < now.date()
    return _Conduct(
        collects=tournament.feature_payments and kept_by_squire,
        queue=kept_by_squire and not held,
        seating_settled=setup.seating_has_settled(tournament, now),
    )


def _row_paid(conduct: _Conduct, row: Row) -> tuple[Paid, bool]:
    """A row's Paid cell and fading: `_paid`, unless the row is a deleted
    account's, which states nothing whatever the money says."""
    if row.get("registration_id") in conduct.deleted:
        return None, False
    return _paid(conduct, bool(row.get("paid")), row.get("expires_at") is not None)


def _paid(conduct: _Conduct, settled: bool, window_running: bool) -> tuple[Paid, bool]:
    """A seated entry's Paid cell and whether it is drawn faded.

    Settled reads yes wherever it is settled, whether or not anything was due:
    paying early is not something the roster hides.

    Unsettled reads no, and fades, only where Squire collects *and* that
    registration's money is due — a payment window is running on it, or the
    obligation its seat is held under has fallen due. In reservation mode
    nothing is owed until the seating deadline, and in deposit mode nothing
    beyond a deposit already paid; a roster reading no before then states a
    failure to pay against somebody nobody has asked (spec public-entrants).
    Owing nothing and having paid are different statements, and the cell makes
    neither out of the other.

    The window is the whole of the per-registration question, because
    `_initial_expires_at` has already applied the payment mode to decide
    whether one opened: it opens in immediate mode, in deposit mode until the
    deposit arrives, for items held with no seat at all whatever the stored
    mode says, and never for a seat the tournament holds unbilled. Reading it
    rather than re-deriving the mode here leaves one place where that is
    decided.

    Where Squire does not collect, only the organizer's hand tick is a fact,
    and an unticked entry carries no mark at all — not "no", which would claim
    a failure to pay that nobody has observed. An empty cell therefore has two
    causes, and neither is a claim about a person, which is why they read
    alike."""
    if settled:
        return "yes", False
    if not conduct.collects:
        return None, False
    if window_running or conduct.seating_settled:
        return "no", True
    return None, False


def _live_registration_ids(session: Session, tournament: Tournament) -> set[int]:
    return set(
        session.scalars(
            select(Registration.id).where(
                Registration.tournament_id == tournament.id, live_registration()
            )
        )
    )


def removed_registration_ids(session: Session, tournament: Tournament) -> set[int]:
    """Registrations whose row the organizer has taken out of the table — by
    deleting it, or by a merge absorbing it — as the replay leaves them.

    Read off the rule set alone rather than by replaying the projection: these
    three kinds are the only writers of a row's removal, and the counts that
    ask this are read on every public page, where building the whole
    projection would cost far more than they are worth. A removed row's
    registration still holds its seat (spec public-entrants); what this
    answers is only who the public is shown."""
    removed: set[str] = set()
    for rule in rules.active_rules(session, tournament):
        if rule.kind == "row_delete":
            removed.add(rule.target)
        elif rule.kind == "row_restore":
            removed.discard(rule.target)
        elif rule.kind == "dedup_decision":
            removed.update(rule.payload.get("absorb", []))
    if not removed:
        return set()
    registrations = session.execute(
        select(Registration.id, Registration.source_row_id).where(
            Registration.tournament_id == tournament.id
        )
    ).all()
    return {
        registration_id
        for registration_id, source_row_id in registrations
        if (source_row_id or f"reg:{registration_id}") in removed
    }


def entered(session: Session, discipline: Discipline, removed: set[int]) -> int:
    """How many are entered in a discipline as the public reads it: live
    seated placements — teams, in a team discipline — less the registrations
    the organizer has taken out of the table. The figure a count beside the
    capacity states, so that a reader can tell from it whether places are
    left (spec public-entrants)."""
    if discipline.kind is DisciplineKind.TEAM:
        query = (
            select(func.count())
            .select_from(Team)
            .join(Registration)
            .where(Team.discipline_id == discipline.id, Team.waitlisted.is_(False))
        )
    else:
        query = (
            select(func.count())
            .select_from(RegistrationDiscipline)
            .join(Registration)
            .where(
                RegistrationDiscipline.discipline_id == discipline.id,
                RegistrationDiscipline.is_substitute.is_(False),
            )
        )
    query = query.where(live_registration())
    if removed:
        query = query.where(Registration.id.not_in(removed))
    return session.scalar(query) or 0


def _queue_positions(session: Session, discipline: Discipline) -> dict[int, int]:
    """Each live queued registration's position in the discipline's queue, by
    registration id — the same count `queue_position` makes for the fencer's
    own page, made once for the whole queue (design D2)."""
    ids = session.scalars(
        select(Registration.id)
        .select_from(RegistrationDiscipline)
        .join(Registration)
        .where(
            RegistrationDiscipline.discipline_id == discipline.id,
            RegistrationDiscipline.is_substitute.is_(True),
            live_registration(),
        )
        .order_by(*QUEUE_ORDER)
    ).all()
    return {registration_id: position for position, registration_id in enumerate(ids, start=1)}


def _entrant(row: Row, slug: str, number: int, paid: Paid, faded: bool) -> EntrantRow:
    return EntrantRow(
        number=number,
        name=row["name"],
        nationality=row.get("nationality"),
        club=row.get("club"),
        hr_id=row.get("hr_id"),
        paid=paid,
        faded=faded,
        conditional=slug in (row.get("conditional") or []),
    )


def _individual(
    session: Session,
    discipline: Discipline,
    rows: list[Row],
    live: set[int],
    conduct: _Conduct,
) -> Roster:
    tab = exporttables.Tab(kind=exporttables.DISCIPLINE, key=discipline.slug, label="")
    # rows standing for a live registration only: the replay also holds
    # imported rows not yet issued and expired registrations, which the
    # organizer sees and the public does not (design D1)
    listed = [
        row for row in exporttables.table_rows(rows, tab) if row.get("registration_id") in live
    ]
    seated: list[EntrantRow] = []
    for row in listed:
        if discipline.slug in (row.get("disciplines") or []):
            paid, faded = _row_paid(conduct, row)
            seated.append(_entrant(row, discipline.slug, len(seated) + 1, paid, faded))
    queued: list[EntrantRow] = []
    if conduct.queue:
        positions = _queue_positions(session, discipline)
        for row in listed:
            position = positions.get(row["registration_id"])
            if discipline.slug in (row.get("substitute_for") or []) and position is not None:
                # a queued placement is not priced, and the registration's
                # settled state is about its seats: the cell states nothing
                queued.append(_entrant(row, discipline.slug, position, None, False))
        queued.sort(key=lambda entrant: entrant.number)
    return Roster(
        slug=discipline.slug,
        name=discipline.name,
        kind=discipline.kind.value,
        line=conduct.queue,
        seated=seated,
        queued=queued,
    )


def _team(team: Team, number: int, paid: Paid, faded: bool, rows: dict[str, Row]) -> TeamRow:
    """One team with its roster beneath it.

    A member's identity is read from the projection, as an individual
    entrant's already is: an identifier the organizer has ruled on is the
    tournament's answer, and the public would otherwise see the claim typed
    into the roster where the console knows a different verdict (spec
    public-entrants, A team roster names the team and its members). Where no
    row stands for a member — nothing projects one while the member is not on a
    live roster — the stored claim is what there is.
    """
    members = []
    for member in team.members:
        row = rows.get(f"mem:{member.id}")
        members.append(
            TeamMemberRow(
                name=row["name"] if row else member.name,
                nationality=(row.get("nationality") if row else member.nationality),
                club=row.get("club") if row else member.club,
                hr_id=row.get("hr_id") if row else member.hr_id,
            )
        )
    return TeamRow(number=number, name=team.name, paid=paid, faded=faded, members=members)


def _teams(
    session: Session,
    discipline: Discipline,
    removed: set[int],
    conduct: _Conduct,
    rows: dict[str, Row],
) -> Roster:
    teams = session.scalars(
        select(Team)
        .join(Registration)
        .where(
            Team.discipline_id == discipline.id,
            live_registration(),
            # a team whose entering registration the organizer took out of the
            # table is gone from it, as an individual's row is
            Registration.id.not_in(removed),
        )
        .options(selectinload(Team.members), selectinload(Team.registration))
        .order_by(Team.waitlisted_since, Team.id)
    ).all()
    seated: list[TeamRow] = []
    queued: list[TeamRow] = []
    for team in teams:
        if not team.waitlisted:
            paid, faded = _paid(
                conduct,
                team.registration.settled,
                team.registration.expires_at is not None,
            )
            seated.append(_team(team, len(seated) + 1, paid, faded, rows))
        elif conduct.queue:
            # listed in waitlist order, so the count so far is the position
            # `team_waitlist_position` states
            queued.append(_team(team, len(queued) + 1, None, False, rows))
    return Roster(
        slug=discipline.slug,
        name=discipline.name,
        kind=discipline.kind.value,
        line=conduct.queue,
        seated=seated,
        queued=queued,
    )


def _event(item: ExtraItem, rows: list[Row], live: set[int], conduct: _Conduct) -> Roster:
    """Who has taken a place at one side event: the rows of its category's
    Export tab holding this item, live and not removed, paid first. An item
    keeps no queue (spec item-capacity); a capped one draws the capacity line
    under its last row wherever a discipline's roster would draw its line.
    Its Paid cell follows the registration as a discipline's does."""
    tab = exporttables.Tab(kind=exporttables.CATEGORY, key=item.category.value, label="")
    seated: list[EntrantRow] = []
    for row in exporttables.table_rows(rows, tab):
        if row.get("registration_id") not in live:
            continue
        selections = (row.get("extras") or {}).get(item.category.value) or []
        if not any(selection.get("item_id") == item.id for selection in selections):
            continue
        paid, faded = _row_paid(conduct, row)
        seated.append(
            EntrantRow(
                number=len(seated) + 1,
                name=row["name"],
                nationality=row.get("nationality"),
                club=row.get("club"),
                hr_id=row.get("hr_id"),
                paid=paid,
                faded=faded,
                conditional=False,
            )
        )
    line = conduct.queue and item.capacity is not None
    return Roster(
        slug=str(item.id),
        name=item.name,
        kind="event",
        line=line,
        seated=seated,
        capacity=item.capacity if line else None,
    )


def rosters(session: Session, tournament: Tournament) -> list[Roster]:
    """Every discipline's roster, in the tournament's discipline order, then
    each listed side event's, in the order they were offered."""
    # one instant for the whole page, so a long answer straddling midnight does
    # not have one roster reading the day before and the next the day after
    conduct = replace(
        _conduct(tournament, datetime.now(UTC)),
        deleted=frozenset(
            session.scalars(
                select(Registration.id)
                .join(Fencer, Fencer.id == Registration.fencer_id)
                .where(Registration.tournament_id == tournament.id, Fencer.deleted_at.is_not(None))
            ).all()
        ),
    )
    base = sheet.base_rows(session, tournament)
    replayed, _ = rules.replay(
        base, rules.active_rules(session, tournament), sheet.rating_lookup(session, tournament)
    )
    rows = list(replayed.values())
    live = _live_registration_ids(session, tournament)
    removed = removed_registration_ids(session, tournament)
    disciplines = [
        _individual(session, discipline, rows, live, conduct)
        if discipline.kind is DisciplineKind.INDIVIDUAL
        else _teams(session, discipline, removed, conduct, replayed)
        for discipline in tournament.disciplines
    ]
    events = [
        _event(item, rows, live, conduct)
        for item in sorted(tournament.extra_items, key=lambda item: item.id)
        if item.category in PUBLIC_EVENT_CATEGORIES
    ]
    return disciplines + events
