"""The amendment itself, reached from two sides.

`routers/registrations.amend_registration` holds the HTTP concerns — the
amendment window, the fencer's own registration, the response model. What it
does once those are settled is here, so the organizer's discipline correction
from the console (`discipline-amendment`) cannot drift away from the fencer's
own amendment. A second copy of "drop the selection, re-place, re-price, record
the event, write to the fencer" is where the drift would start, and a
correction that priced differently from the fencer's own amendment would be a
defect neither side could see alone.

What differs between the two callers is passed in rather than sniffed at:
whether a full discipline seats or queues, and which notice goes out.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import emails, pricing
from app.availability import full_disciplines, team_waitlist_flags
from app.mail import Mailer
from app.models import (
    DisciplineKind,
    PaymentEvent,
    RefundState,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationState,
    Team,
    TeamMember,
    Tournament,
)

# Which notice the amendment sends.
#
# FENCER is the fencer amending their own entry: they expect an acknowledgement,
# so an amendment that leaves them owing writes a surcharge demand and one that
# does not writes a confirmation.
#
# SURCHARGE_ONLY is the organizer correcting the roster: a letter per corrected
# row would make the correction cost more than the error, while the surcharge
# notice carries information the fencer cannot get any other way (design
# edit-issued-disciplines Decision 3).
FENCER = "fencer"
SURCHARGE_ONLY = "surcharge_only"


def apply_amendment(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    selected: list,
    mailer: Mailer,
    *,
    seat_all: bool,
    notice: str,
    extras: list | None = None,
    team_entries: list | None = None,
    fields: dict | None = None,
) -> None:
    """Replace a registration's selection, re-price it and tell whoever is owed
    telling. Commits.

    `selected` is the individual disciplines the registration is to hold, in
    full: an amendment states the selection rather than a difference from it.
    `extras`, `team_entries` and `fields` are the parts of a submission only the
    fencer's own path sends; `None` leaves each of them as it stands, which is
    what a discipline correction from the console means by not mentioning them.

    `seat_all` decides how a newly named discipline that is full is placed
    (design Decision 2): an issued registration's every discipline seats,
    because a substitute placement is not billed and queueing a correction to an
    imported roster would make that fencer free.
    """
    was_paid = registration.state == RegistrationState.PAID
    previous_total = registration.total_amount

    # drop the current selection before checking capacity, so the registration's
    # own existing seats are not counted as taken against itself
    session.execute(
        delete(RegistrationDiscipline).where(
            RegistrationDiscipline.registration_id == registration.id
        )
    )
    if extras is not None:
        session.execute(
            delete(RegistrationExtra).where(RegistrationExtra.registration_id == registration.id)
        )

    existing_teams: dict[int, Team] = {}
    keep_ids: set[int] = set()
    if team_entries is not None:
        # teams are replaced too, but selectively: a team whose id the client
        # resubmits keeps its roster (and row); one it does not is dropped with
        # its roster (design team-disciplines D6, task 4.3 — "editing the names
        # inside a team is not [an amendment]" but adding/removing a team is)
        existing_teams = {t.id: t for t in registration.teams}
        keep_ids = {e.id for _, e in team_entries if e.id is not None and e.id in existing_teams}
        remove_ids = [tid for tid in existing_teams if tid not in keep_ids]
        if remove_ids:
            session.execute(delete(TeamMember).where(TeamMember.team_id.in_(remove_ids)))
            session.execute(delete(Team).where(Team.id.in_(remove_ids)))
            # `registration.teams` was already loaded above (to build
            # `existing_teams`), so the ORM does not know to drop the deleted
            # rows from its cached collection on its own — same reasoning as
            # tournaments.delete_discipline's `tournament.disciplines.remove(...)`
            for tid in remove_ids:
                registration.teams.remove(existing_teams[tid])
    session.flush()

    # unlike register(), amendment never rejects for fullness: a discipline
    # that is full joins as a substitute placement in place, and every other
    # selected discipline is unaffected by it (design Decision 3 — rejecting
    # the whole submission would discard the parts that were fine). Teams
    # follow the same never-reject rule: a full team discipline waitlists the
    # team instead (design team-disciplines, spec "Team capacity and the team
    # waitlist"). `exclude_registration_id` keeps this registration's own
    # (soon-to-be-replaced) teams out of the capacity count, so a kept team is
    # not counted against itself.
    full: set[str] = set() if seat_all else full_disciplines(session, selected)
    team_flags = (
        team_waitlist_flags(session, team_entries, exclude_registration_id=registration.id)
        if team_entries is not None
        else []
    )

    if fields is not None:
        for name, value in fields.items():
            setattr(registration, name, value)
    for discipline in selected:
        registration.entries.append(
            RegistrationDiscipline(discipline=discipline, is_substitute=discipline.slug in full)
        )
    for selection in extras or []:
        value = (selection.option_value or "").strip()
        registration.extra_selections.append(
            RegistrationExtra(
                extra_item_id=selection.extra_item_id,
                qty=selection.qty,
                option_value=value or None,
            )
        )
    for (discipline, team_in), waitlisted in zip(team_entries or [], team_flags, strict=True):
        if team_in.id is not None and team_in.id in keep_ids:
            team = existing_teams[team_in.id]
            team.discipline = discipline
            team.name = team_in.name
            team.waitlisted = waitlisted
        else:
            registration.teams.append(
                Team(
                    tournament_id=tournament.id,
                    discipline=discipline,
                    name=team_in.name,
                    waitlisted=waitlisted,
                )
            )
    session.flush()

    # vs and expires_at are read-only through this path: amending must not
    # renew the hold or reissue the QR (Decision 3, the load-bearing guarantee).
    # `registration_total` prices at `registered_at`, so a correction made after
    # an early-bird deadline is still priced at the fees that applied when the
    # fencer registered (spec imported-registrations, What an issued
    # registration is worth).
    totals = pricing.registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    overpaid = registration.balance_cents(tournament)[0] < 0
    if was_paid and overpaid:
        registration.refund_state = RefundState.PENDING

    session.add(
        PaymentEvent(
            tournament_id=tournament.id,
            registration_id=registration.id,
            kind="registration_amended",
            detail=f"{registration.audit_label}: {previous_total} -> {registration.total_amount}",
        )
    )
    session.commit()

    # asked of the one balance, not of both lanes: the uncredited lane always
    # holds its full price, so an `or` across the two made every amendment of
    # a paid registration send a surcharge demand for money nobody owed
    underpaid = registration.balance_cents(tournament)[0] > 0
    fencer = registration.fencer
    if notice == FENCER:
        if was_paid:
            if underpaid:
                emails.send_surcharge_due(mailer, tournament, fencer, registration)
        else:
            emails.send_amendment_confirmation(mailer, tournament, fencer, registration)
    elif notice == SURCHARGE_ONLY:
        # only where the correction costs the fencer: the total went up *and*
        # there is money outstanding to ask for. The second half matters —
        # a settled-by-hand registration owes nothing however its total moves,
        # and a demand for money nobody owes is the defect the fencer's own
        # path already guards against
        if underpaid and registration.total_amount > previous_total:
            emails.send_surcharge_due(mailer, tournament, fencer, registration)


def dormant_by_origin(registration: Registration) -> bool:
    """Whether this registration was issued rather than made in the application.

    Read from the registration's own dormancy flag rather than through
    `setup.dormancy_cause`, which also answers for tournament-wide causes that
    say nothing about where this registration came from (design Decision 2)."""
    return registration.clocks_dormant


def is_live(registration: Registration) -> bool:
    """Whether the registration still describes a competitor. One that has
    expired or been cancelled returns through re-registration with a new
    symbol, not through a cell."""
    return registration.state in (RegistrationState.RESERVED, RegistrationState.PAID)


def registration_for_row(
    session: Session, tournament: Tournament, target: str
) -> Registration | None:
    """The registration standing behind a fencer-list row, where one does.

    Addressed the way the sheet addresses it: an issued registration takes its
    source row's id, so the row is found by `source_row_id` first and only a
    registration with no row of its own answers to `reg:<id>` (`sheet.py`)."""
    registration = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.source_row_id == target,
            Registration.state != RegistrationState.CANCELLED,
        )
    )
    if registration is not None:
        return registration
    if target.startswith("reg:"):
        try:
            registration_id = int(target[len("reg:") :])
        except ValueError:
            return None
        registration = session.get(Registration, registration_id)
        if (
            registration is not None
            and registration.tournament_id == tournament.id
            and registration.state != RegistrationState.CANCELLED
        ):
            return registration
    return None


def resolve_slugs(tournament: Tournament, slugs: list[str]) -> list:
    """The tournament's individual disciplines named by a rule's slugs, in the
    order the rule names them. Unknown slugs are the caller's to have refused
    when the rule was created."""
    by_slug = {
        discipline.slug: discipline
        for discipline in tournament.disciplines
        if discipline.kind is DisciplineKind.INDIVIDUAL
    }
    return [by_slug[slug] for slug in slugs if slug in by_slug]


def reapply_amendments(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    amendments: list[list[str]],
    base: list[str],
    mailer: Mailer,
) -> None:
    """Put the registration into the state the amendments that remain produce.

    Not an inverse of the operation just undone. Withdrawal is a replay, as it
    is for every other rule kind (spec edit-rules, Rule lifecycle): the
    disciplines the registration was issued with, with the remaining amendments
    applied over them in order. Each amendment states the whole selection, so
    the last one standing is the answer — and where none stands, the issued
    selection is.

    Priced and placed on the same terms the amendment itself was, and silent
    unless the result leaves the fencer owing more."""
    slugs = amendments[-1] if amendments else base
    apply_amendment(
        session,
        tournament,
        registration,
        resolve_slugs(tournament, slugs),
        mailer,
        seat_all=dormant_by_origin(registration),
        notice=SURCHARGE_ONLY,
    )
