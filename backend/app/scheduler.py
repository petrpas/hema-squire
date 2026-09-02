"""Periodic payment lifecycle processing: Fio polling, reminders, expiries.

The processing functions are pure sync logic over a session; the background
loop (started from the app lifespan) and the organizer endpoint both call them.
"""

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import bank, emails, matching
from app.config import settings
from app.db import SessionLocal
from app.mail import Mailer, get_mailer
from app.models import PaymentEvent, Registration, RegistrationState, Team, Tournament
from app.setup import seating_deadline_for, seating_has_settled

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
    deadline = seating_deadline_for(tournament)
    return now.date() >= deadline - timedelta(days=tournament.reminder_day)


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
            # an issued registration is never reminded: its clocks are dormant
            # by origin, and _reminder_due would otherwise anchor it to the
            # seating deadline and mail a roster that registered a season ago
            # (spec imported-registrations)
            Registration.clocks_dormant.is_(False),
        )
    ).all()
    due = [
        registration
        for registration in candidates
        if not registration.fully_queued and _reminder_due(tournament, registration, now)
    ]
    for registration in due:
        registration.reminded_at = _now()
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="reminder_sent",
                detail=f"VS {registration.vs}",
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
            # stated rather than left to follow from expires_at being NULL: an
            # issued registration never expires for non-payment whatever else
            # is written on it (spec imported-registrations)
            Registration.clocks_dormant.is_(False),
        )
    ).all()
    if seating_has_settled(tournament, _now().date()):
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
                    detail=f"VS {registration.vs}",
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
                    detail=f"VS {registration.vs}",
                )
            )
            continue
        registration.state = RegistrationState.EXPIRED
        expired += 1
        holding_payment = (
            registration.amount_paid_cents > 0 or (registration.amount_paid_eur_cents or 0) > 0
        )
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="expired_holding_payment" if holding_payment else "reservation_expired",
                detail=f"VS {registration.vs}",
            )
        )
        emails.send_reservation_expired(
            mailer, tournament, registration.fencer, registration,
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


def pending_demotions(session: Session, tournament: Tournament) -> int:
    """How many registrations `settle_seating` would move below the line right
    now — what the console states before asking the organizer to confirm an
    irreversible settlement."""
    reserved = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            # an issued registration stays seated. The seating deadline is the
            # second of the two clocks, and it is dormant for the same reason
            # the first is: the row it came from stated who was competing, and
            # demoting them for money the organizer never asked for would take
            # a seat nobody was owed (spec imported-registrations). This
            # predicate is shared with `pending_demotions`, which states the
            # count the organizer confirms — the two must select alike
            Registration.clocks_dormant.is_(False),
        )
    ).all()
    return sum(
        1
        for registration in reserved
        if any(not entry.is_substitute for entry in registration.entries)
        or any(not team.waitlisted for team in registration.teams)
    )


def settle_seating(session: Session, tournament: Tournament) -> int:
    """Close the tournament's seating: every registration still owing money —
    that is, still RESERVED — is moved to the substitute queue in place, and
    the tournament is stamped as settled. Returns how many were demoted.

    A pure pass with no trigger condition of its own, so the deadline tick and
    the organizer's settle-early action are literally the same operation
    (design D6); the caller decides when. `queue_position` ranks by
    `Registration.registered_at`, so demotion places each registration in the
    queue in registration order with no sorting here.

    The stamp is what makes settlement one-shot. Its demotion predicate is
    "reserved and seated", which is exactly what `admit_substitute` produces,
    so without the stamp every later tick would silently unwind the
    organizer's promotions."""
    reserved = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            # an issued registration stays seated. The seating deadline is the
            # second of the two clocks, and it is dormant for the same reason
            # the first is: the row it came from stated who was competing, and
            # demoting them for money the organizer never asked for would take
            # a seat nobody was owed (spec imported-registrations). This
            # predicate is shared with `pending_demotions`, which states the
            # count the organizer confirms — the two must select alike
            Registration.clocks_dormant.is_(False),
        )
    ).all()
    demoted = 0
    for registration in reserved:
        if not _demote(registration):
            continue
        demoted += 1
        session.add(
            PaymentEvent(
                tournament_id=tournament.id,
                registration_id=registration.id,
                kind="seating_demoted",
                detail=f"VS {registration.vs}",
            )
        )
    tournament.seating_settled_at = _now()
    session.commit()
    return demoted


def settle_seating_if_due(session: Session, tournament: Tournament) -> int:
    """Run the settlement pass if the deadline has passed and it has not run
    yet. The one place that decides *when* seating settles by itself — the
    organizer's settle-early action deliberately does not go through it, and
    every lifecycle pass does, so a manual `process` run and a scheduler tick
    can never disagree about whether seating has closed."""
    if tournament.seating_settled_at is not None:
        return 0
    if date.today() <= seating_deadline_for(tournament):
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
    if tournament.team_composition_deadline is None:
        return 0
    today = _now().date()
    window_start = tournament.team_composition_deadline - timedelta(days=tournament.reminder_day)
    if not (window_start <= today <= tournament.team_composition_deadline):
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
        if len(team.members) >= team.discipline.team_min:
            continue
        by_fencer.setdefault(team.registration.fencer_id, []).append(team)

    sent = 0
    for teams in by_fencer.values():
        fencer = teams[0].registration.fencer
        emails.send_composition_reminder(mailer, tournament, fencer, teams)
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
        today = date.today()
        transactions = fio_client.fetch(
            tournament.fio_token, today - timedelta(days=14), today
        )
        ingested = bank.ingest(session, tournament, "fio_api", transactions)
        matched = matching.match_new_transactions(session, tournament, mailer)
        matching.apply_payment_links(session, tournament, mailer)
        result |= {"polled_new": ingested.new, "matched": matched.matched}
    # Settle before expiring, and the order is load-bearing (design Decision
    # 1): in deposit mode a registration can be under both clocks at once, and
    # without a fixed order whether an unpaid deposit expiring on the deadline
    # date is queued or expired would come down to tick timing. Settling first
    # makes it uniform — everything still reserved at the deadline is queued.
    result["seating_demoted"] = settle_seating_if_due(session, tournament)
    # Reminders and expiry are the money passes, so they do not run at all
    # while the payments feature is off (design tournament-modes D5) — nothing
    # is owed, so there is nothing to remind about and no window to lapse.
    # Seating settlement and composition reminders keep running above and
    # below: they are about seats and rosters, which every tournament has.
    if tournament.feature_payments:
        # Expire second: a reservation past its window must not receive a reminder.
        result["expired"] = process_expiries(session, tournament, mailer)
        result["reminders"] = process_reminders(session, tournament, mailer)
    else:
        result["expired"] = 0
        result["reminders"] = 0
    result["composition_reminders"] = process_composition_reminders(session, tournament, mailer)
    return result


def run_tick() -> None:
    """One scheduler pass over all current tournaments, with real dependencies."""
    mailer = get_mailer()
    fio_client = bank.get_fio_client()
    with SessionLocal() as session:
        tournaments = session.scalars(
            select(Tournament).where(Tournament.date >= date.today())
        ).all()
        for tournament in tournaments:
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
