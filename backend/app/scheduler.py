"""Periodic payment lifecycle processing: Fio polling, reminders, expiries.

The processing functions are pure sync logic over a session; the background
loop (started from the app lifespan) and the organizer endpoint both call them.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import bank, emails, matching
from app.config import settings
from app.db import SessionLocal
from app.mail import Mailer, get_mailer
from app.models import (
    PaymentEvent,
    Registration,
    RegistrationsKeptBy,
    RegistrationState,
    Team,
    Tournament,
)
from app.setup import clocks_run, local_date, seating_deadline_for, seating_has_settled

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _reminder_due(tournament: Tournament, registration: Registration, now: datetime) -> bool:
    """Whether this reservation has reached its reminder day.

    A reminder is notice before an obligation falls due, so it is anchored to
    whichever clock the registration is actually under (design Decision 2): the
    payment window where one is running, and the seating deadline where the
    seat is held without one — a `reservation`-mode registration has no private
    clock at all, and the old `expires_at IS NOT NULL` filter would have
    skipped it forever."""
    if registration.expires_at is not None:
        # SQLite drops tzinfo on round-trip even for a DateTime(timezone=True)
        # column; every stored instant is UTC (matching.within_expiry_grace)
        expires_at = registration.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return now >= expires_at - timedelta(days=tournament.reminder_day)
    # the deadline is a date the organizer entered, so the distance to it is
    # measured from the day where the tournament is held, never from the UTC
    # day of `now` (design unify-day-boundary-clocks D1)
    deadline = seating_deadline_for(tournament)
    return local_date(tournament, now) >= deadline - timedelta(days=tournament.reminder_day)


def process_reminders(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Remind unpaid reservations that reached the tournament's reminder day.

    `expires_at IS NOT NULL` used to stand in for "not a substitute"; it no
    longer can, since a seated `reservation`-mode registration has no window
    either. Substitute status is filtered on directly instead — a registration
    sitting entirely in the queue owes nothing and is never reminded, in any
    mode."""
    now = _now()
    candidates = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            Registration.reminded_at.is_(None),
        )
    ).all()
    # Dormancy is asked once, of `setup.clocks_run`, and never spelled as a
    # condition here (design unify-lifecycle-dormancy D1). Without it
    # `_reminder_due` would anchor a dormant registration to the seating
    # deadline and mail a roster that registered a season ago.
    due = [
        registration
        for registration in candidates
        if clocks_run(tournament, registration)
        and not registration.fully_queued
        and _reminder_due(tournament, registration, now)
    ]
    for registration in due:
        registration.reminded_at = _now()
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="reminder_sent",
                detail=registration.audit_label,
            )
        )
        emails.send_payment_reminder(mailer, tournament, registration.fencer, registration)
    session.commit()
    return len(due)


def process_expiries(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Expire unpaid reservations past their window, freeing capacity.

    A partial payment does not extend the window (design harden-payment-
    matching Decision 3) — a reservation holding one expires on schedule like
    any other, but distinctly: a separate audit event and a branched notice,
    since the organizer is left holding money for a reservation that no
    longer exists.

    Once seating has settled the outcome changes: a lapsed window returns the
    registration to the queue instead of expiring it (design Decision 8). The
    only registrations under a window then are ones the organizer promoted
    deliberately, and EXPIRED would discard them along with the registration
    order they would never get back.

    A registration still holding a substitute placement is demoted rather than
    expired whether or not seating has settled (design place-substitutes-per-
    discipline D5). Its queue place was never what the money was for: expiring
    it would make an unpaid seat cost a queue position the fencer owed nothing
    for. Returns how many registrations were expired; a demoted one is not
    among them, because it still exists."""
    overdue = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            Registration.expires_at.is_not(None),
            Registration.expires_at <= _now(),
        )
    ).all()
    # Stated rather than left to follow from expires_at being NULL: a dormant
    # registration never expires for non-payment whatever else is written on it
    # (design unify-lifecycle-dormancy D1)
    overdue = [r for r in overdue if clocks_run(tournament, r)]
    if seating_has_settled(tournament, _now()):
        returned = 0
        for registration in overdue:
            registration.expires_at = None
            if not _demote(registration):
                continue
            returned += 1
            session.add(
                PaymentEvent(
                    tournament_id=tournament.id,
                    registration_id=registration.id,
                    kind="promotion_lapsed",
                    detail=registration.audit_label,
                )
            )
        session.commit()
        return returned
    expired = 0
    for registration in overdue:
        if registration.holds_queued_placement:
            # The seat it did not pay for is given up; the queue place it never
            # owed for is kept, in its original registration order. A distinct
            # kind from `promotion_lapsed`: the cause is an unpaid seat, not an
            # unpaid promotion.
            registration.expires_at = None
            _demote(registration)
            session.add(
                PaymentEvent(
                    tournament_id=tournament.id,
                    registration_id=registration.id,
                    kind="seat_lapsed_to_queue",
                    detail=registration.audit_label,
                )
            )
            continue
        registration.state = RegistrationState.EXPIRED
        expired += 1
        # correct under the widened counter: money an organizer recorded by
        # hand is as real and this reservation is as expired, so it belongs in
        # the expired-holding queue on the same terms (spec payments-console).
        # A waiver credits nothing and so never lands here, which is right —
        # there is nothing to give back
        holding_payment = (
            registration.amount_paid_cents > 0 or (registration.amount_paid_eur_cents or 0) > 0
        )
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="expired_holding_payment" if holding_payment else "reservation_expired",
                detail=registration.audit_label,
            )
        )
        emails.send_reservation_expired(
            mailer,
            tournament,
            registration.fencer,
            registration,
            holding_payment=holding_payment,
        )
    session.commit()
    return expired


def _demote(registration: Registration) -> bool:
    """Move one registration below the line, in place: every seated entry
    becomes a substitute placement, every team is waitlisted, and any payment
    window is closed, because the queue holds no money (design D5). The
    registration stays RESERVED and keeps its VS — it is queued, not expired.

    False when there was nothing above the line to move, so a registration
    already fully queued is neither counted nor audited twice."""
    seated = [entry for entry in registration.entries if not entry.is_substitute]
    seated_teams = [team for team in registration.teams if not team.waitlisted]
    if not seated and not seated_teams:
        return False
    for entry in seated:
        entry.is_substitute = True
    for team in seated_teams:
        team.waitlisted = True
    registration.expires_at = None
    return True


def _demotable(session: Session, tournament: Tournament) -> list[Registration]:
    """The registrations settling seating would move below the line, in
    registration order.

    **One selection, two callers.** `pending_demotions` counts what this
    returns and `settle_seating` acts on it, so the number the console states
    before the organizer confirms an irreversible settlement is the number the
    settlement then delivers. They used to be two queries carrying the same
    `where` and a comment on each asking future editors to keep them aligned;
    the alignment is structural now (design unify-lifecycle-dormancy D5).

    Reserved means "still owes money" only where money was asked for. A dormant
    registration is excluded whatever made it dormant — on a payments-off
    tournament nothing ever leaves RESERVED, so reading the state as a debt
    would select the entire field and take seats nobody was ever billed for
    (design D3).

    Holding something above the line is part of the selection rather than a
    test `settle_seating` makes afterwards: a registration already wholly in the
    queue is neither counted nor audited, because there is nothing to move."""
    reserved = session.scalars(
        select(Registration)
        .where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
        )
        .order_by(Registration.registered_at)
    ).all()
    return [
        registration
        for registration in reserved
        if clocks_run(tournament, registration)
        and (
            any(not entry.is_substitute for entry in registration.entries)
            or any(not team.waitlisted for team in registration.teams)
        )
    ]


def pending_demotions(session: Session, tournament: Tournament) -> int:
    """How many registrations `settle_seating` would move below the line right
    now — what the console states before asking the organizer to confirm an
    irreversible settlement."""
    return len(_demotable(session, tournament))


def settle_seating(session: Session, tournament: Tournament) -> int:
    """Close the tournament's seating: every registration still owing money —
    that is, still RESERVED and not dormant — is moved to the substitute queue
    in place, and the tournament is stamped as settled. Returns how many were
    demoted.

    A pure pass with no trigger condition of its own, so the deadline tick and
    the organizer's settle-early action are literally the same operation
    (design D6); the caller decides when. `queue_position` ranks by
    `Registration.registered_at`, so demotion places each registration in the
    queue in registration order with no sorting here.

    **The stamp is unconditional.** Closing seating and demoting debtors are two
    things this pass does at once, and only the second is about money: seats are
    finite whether or not anyone paid for them, so a tournament with nobody to
    demote still closes and still sends later registrations to the queue (design
    unify-lifecycle-dormancy D3). Immediate mode has always reached that state
    by a different road, demoting nobody because every unpaid reservation
    expired first.

    The stamp is also what makes settlement one-shot. Its demotion predicate is
    "reserved, seated and not dormant", which is exactly what `admit_substitute`
    produces, so without the stamp every later tick would silently unwind the
    organizer's promotions."""
    demoted = 0
    for registration in _demotable(session, tournament):
        if not _demote(registration):
            continue
        demoted += 1
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="seating_demoted",
                detail=registration.audit_label,
            )
        )
    tournament.seating_settled_at = _now()
    session.commit()
    return demoted


def settle_seating_if_due(session: Session, tournament: Tournament, now: datetime) -> int:
    """Run the settlement pass if the deadline has passed and it has not run
    yet. The one place that decides *when* seating settles by itself — the
    organizer's settle-early action deliberately does not go through it, and
    every lifecycle pass does, so a manual `process` run and a scheduler tick
    can never disagree about whether seating has closed.

    Asks `seating_has_settled` rather than comparing a day of its own: the two
    used to read different clocks, which opened a window where seating counted
    as settled while this pass had not run (design unify-day-boundary-clocks
    D1). The stamp is checked first all the same, because settling twice is
    what this guards and `seating_has_settled` answers yes to both reasons."""
    if tournament.seating_settled_at is not None:
        return 0
    if not seating_has_settled(tournament, now):
        return 0
    return settle_seating(session, tournament)


def process_composition_reminders(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Remind the entering fencer, once per team, of a roster still short of
    its discipline's minimum, ahead of the composition deadline (spec:
    "Composition reminder to the entering fencer"). Mirrors the shape of
    `process_reminders` — `reminder_day` days of notice, a stamped timestamp
    so a later tick does not resend (design team-disciplines D7). Skips
    entirely when the tournament has no deadline, is outside the notice
    window, is waitlisted, already reminded, or already at its minimum — none
    of which is a case for a reminder."""
    deadline = tournament.team_composition_deadline
    if deadline is None:
        return 0
    # the notice window is measured from the deadline's own day, which is a
    # date the organizer entered and so belongs to the tournament's zone
    # (design unify-day-boundary-clocks D1)
    today = local_date(tournament, _now())
    window_start = deadline - timedelta(days=tournament.reminder_day)
    if not (window_start <= today <= deadline):
        return 0

    candidates = session.scalars(
        select(Team)
        .join(Registration, Team.registration_id == Registration.id)
        .where(
            Team.tournament_id == tournament.id,
            Team.waitlisted.is_(False),
            Team.composition_reminded_at.is_(None),
            Registration.state.in_([RegistrationState.RESERVED, RegistrationState.PAID]),
        )
    ).all()

    by_fencer: dict[int, list[Team]] = {}
    for team in candidates:
        # a team discipline always carries both bounds (`DisciplineIn` enforces
        # it on write); no minimum recorded means no team is below one
        if len(team.members) >= (team.discipline.team_min or 0):
            continue
        by_fencer.setdefault(team.registration.fencer_id, []).append(team)

    sent = 0
    for teams in by_fencer.values():
        fencer = teams[0].registration.fencer
        emails.send_composition_reminder(mailer, tournament, fencer, teams, deadline)
        for team in teams:
            team.composition_reminded_at = _now()
        sent += len(teams)
    session.commit()
    return sent


def run_tournament_tick(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    fio_client: bank.FioClient | None = None,
) -> dict[str, int]:
    result: dict[str, int] = {}
    if fio_client is not None and tournament.fio_token and tournament.feature_payments:
        # an operational window with nobody's calendar behind it: fourteen days
        # back from the UTC day, so the same deployment answers the same
        # wherever its process runs (design unify-day-boundary-clocks D1)
        today = datetime.now(UTC).date()
        transactions = fio_client.fetch(tournament.fio_token, today - timedelta(days=14), today)
        ingested = bank.ingest(session, tournament, "fio_api", transactions)
        matched = matching.match_new_transactions(session, tournament, mailer)
        matching.apply_payment_links(session, tournament, mailer)
        result |= {"polled_new": ingested.new, "matched": matched.matched}
    # Settle before expiring, and the order is load-bearing (design Decision
    # 1): in deposit mode a registration can be under both clocks at once, and
    # without a fixed order whether an unpaid deposit expiring on the deadline
    # date is queued or expired would come down to tick timing. Settling first
    # makes it uniform — everything still reserved at the deadline is queued.
    result["seating_demoted"] = settle_seating_if_due(session, tournament, _now())
    # Every pass runs on every tournament, and each asks `setup.dormancy_cause`
    # what it may touch. The payments feature used to be tested here as well,
    # skipping these two wholesale — a second decision point that reached two of
    # the four passes and not the other two, which is how a payments-off
    # tournament came to demote its entire field at the seating deadline (design
    # unify-lifecycle-dormancy D4). The cost of dropping it is two indexed
    # selects that return nothing; the gain is that there is one place to be
    # wrong.
    #
    # Expire second: a reservation past its window must not receive a reminder.
    result["expired"] = process_expiries(session, tournament, mailer)
    result["reminders"] = process_reminders(session, tournament, mailer)
    result["composition_reminders"] = process_composition_reminders(session, tournament, mailer)
    return result


def tournaments_to_tick(session: Session) -> list[Tournament]:
    """The tournaments one lifecycle pass considers.

    Three exclusions, and they are different in kind. A tournament already held
    is behind every clock it had. A tournament whose registrations its
    organizer keeps was never under one: Squire does not own its roster, so no
    pass may see it at all. A draft is a tournament being written, and holds
    nobody for a clock to run against — it can hold no participant at all
    (spec tournament-publication, A tournament is a draft until it is
    published).

    The last two are made here, once, rather than as a condition inside each
    pass. That is the difference between a guard and a guarantee — a
    registration created on such a tournament by any path, including one that
    forgets to mark it dormant, is safe because the passes are never reached
    (design add-registrations-kept-by D2). A named function rather than an inline
    select so the exclusion can be asserted directly, without standing up a
    scheduler."""
    return list(
        session.scalars(
            select(Tournament).where(
                Tournament.date >= datetime.now(UTC).date(),
                Tournament.published_at.is_not(None),
                Tournament.registrations_kept_by != RegistrationsKeptBy.ORGANIZER,
            )
        ).all()
    )


def run_tick() -> None:
    """One scheduler pass over all current tournaments, with real dependencies."""
    mailer = get_mailer()
    fio_client = bank.get_fio_client()
    with SessionLocal() as session:
        for tournament in tournaments_to_tick(session):
            try:
                run_tournament_tick(session, tournament, mailer, fio_client)
            except Exception:
                logger.exception("scheduler tick failed for %s", tournament.slug)


async def scheduler_loop() -> None:
    while True:
        await asyncio.sleep(settings.scheduler_interval_seconds)
        try:
            await asyncio.to_thread(run_tick)
        except Exception:
            logger.exception("scheduler tick crashed")
