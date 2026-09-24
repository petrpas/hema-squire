"""Periodic payment lifecycle processing: Fio polling, reminders, expiries.

The processing functions are pure sync logic over a session; the background
loop (started from the app lifespan) and the organizer endpoint both call them.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import bank, emails, matching, pricing
from app.availability import queue_position, team_waitlist_position
from app.config import settings
from app.db import SessionLocal
from app.mail import Mailer, get_mailer
from app.models import (
    PaymentEvent,
    PaymentMode,
    Registration,
    RegistrationDiscipline,
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
            # a settled registration owes nothing and is chased for nothing.
            # Stated because the reserved state no longer says it: whether a
            # registration has been paid for left the enum and is the
            # derivation beside it (design derive-balances-from-credits D5)
            ~Registration.settled,
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

    **A lapsed promotion takes back only what it seated** (design
    demotion-hardening D6b). Placements and teams a promotion seated carry
    `promoted_unpaid` until the registration reads paid; they go back to the
    end of the queue first, the registration is repriced, and whatever it had
    already paid for keeps its seat. Only where it still owes, still holds a
    seat, and what it owes was due within the window that lapsed does the
    ordinary outcome below apply to the rest.

    Once seating has settled the ordinary outcome changes: a lapsed window
    returns the registration to the queue instead of expiring it (design
    Decision 8). The only registrations under a window then are ones the
    organizer promoted deliberately, and EXPIRED would discard them.

    A registration still holding a substitute placement is demoted rather than
    expired whether or not seating has settled (design place-substitutes-per-
    discipline D5). Its queue place was never what the money was for: expiring
    it would make an unpaid seat cost a queue position the fencer owed nothing
    for.

    Every demotion goes to the end of the queue and is mailed after the commit
    (spec registration, Demotion is announced). Returns how many registrations
    were expired — and, once seating has settled, how many lapsed promotions
    were returned to the queue, that being what a lapse then does in place of
    expiring. A registration demoted before settlement is not counted, because
    it still exists and nothing it held was a promotion."""
    now = _now()
    overdue = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
            # a settled registration does not expire for non-payment, which the
            # reserved state used to say on its own
            ~Registration.settled,
            Registration.expires_at.is_not(None),
            Registration.expires_at <= now,
        )
    ).all()
    # Stated rather than left to follow from expires_at being NULL: a dormant
    # registration never expires for non-payment whatever else is written on it
    # (design unify-lifecycle-dormancy D1)
    overdue = [r for r in overdue if clocks_run(tournament, r)]
    settled_seating = seating_has_settled(tournament, now)
    announced: list[tuple[Registration, Demotion]] = []
    expired = 0
    for registration in overdue:
        demotion = Demotion()
        if _carries_promotion_marks(registration):
            demotion = _demote(registration, tournament, now, marked_only=True)
            _record(session, tournament, registration, "promotion_lapsed", demotion)
            if not _still_owed_under_window(tournament, registration, settled_seating):
                # the window was the promotion's, and it is over
                registration.expires_at = None
                if demotion:
                    announced.append((registration, demotion))
                    if settled_seating:
                        expired += 1
                continue
        if settled_seating or registration.holds_queued_placement:
            # After settlement a lapsed promotion returns to the queue; before
            # it, the seat it did not pay for is given up and the queue place
            # it never owed for is kept. A distinct kind for the second: the
            # cause is an unpaid seat, not an unpaid promotion.
            kind = "promotion_lapsed" if settled_seating else "seat_lapsed_to_queue"
            rest = _demote(registration, tournament, now)
            registration.expires_at = None
            _record(session, tournament, registration, kind, rest)
            demotion = demotion.merged(rest)
            if demotion:
                announced.append((registration, demotion))
                if settled_seating:
                    expired += 1
            continue
        registration.state = RegistrationState.EXPIRED
        expired += 1
        # correct under the widened counter: money an organizer recorded by
        # hand is as real and this reservation is as expired, so it belongs in
        # the expired-holding queue on the same terms (spec payments-console).
        # A waiver credits nothing and so never lands here, which is right —
        # there is nothing to give back
        holding_payment = (
            registration.credited_in("local") > 0 or registration.credited_in("eur") > 0
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
    _announce(session, tournament, mailer, announced)
    return expired


@dataclass
class Demotion:
    """What one demotion moved below the line. Falsy when it moved nothing,
    which is what keeps a registration already wholly in the queue from being
    counted, audited or mailed a second time."""

    entries: list[RegistrationDiscipline] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.entries or self.teams)

    def merged(self, other: Demotion) -> Demotion:
        return Demotion(self.entries + other.entries, self.teams + other.teams)

    @property
    def detail(self) -> str:
        return ", ".join(
            [entry.discipline.slug for entry in self.entries]
            + [f"{team.name} ({team.discipline.slug})" for team in self.teams]
        )


def _demote(
    registration: Registration,
    tournament: Tournament,
    now: datetime,
    *,
    marked_only: bool = False,
) -> Demotion:
    """Move one registration below the line for non-payment, in place: every
    seated entry becomes a substitute placement and every team is waitlisted —
    or, with `marked_only`, only those a promotion seated and nobody has paid
    for yet. The registration stays RESERVED and keeps its VS — it is queued,
    not expired.

    What it moves joins the **end** of the queue: its queue moment becomes
    `now`, so a fencer who held a seat and did not pay for it never takes
    precedence over one who waited from the start (spec registration, Seating
    settlement at the deadline). A placement already in the queue keeps its
    moment. The stored totals are recomputed, exactly as the organizer's
    return-to-queue does, so the registration no longer states the price of a
    seat it does not hold; and where nothing is left seated no payment window
    may keep running, because the queue holds no money (design D5)."""
    entries = [
        entry
        for entry in registration.entries
        if not entry.is_substitute and (entry.promoted_unpaid or not marked_only)
    ]
    teams = [
        team
        for team in registration.teams
        if not team.waitlisted and (team.promoted_unpaid or not marked_only)
    ]
    for entry in entries:
        entry.is_substitute = True
        entry.queued_since = now
        entry.promoted_unpaid = False
    for team in teams:
        team.waitlisted = True
        team.waitlisted_since = now
        team.promoted_unpaid = False
    if entries or teams:
        pricing.reprice(registration, tournament)
    if registration.fully_queued:
        registration.expires_at = None
    return Demotion(entries, teams)


def _carries_promotion_marks(registration: Registration) -> bool:
    return any(entry.promoted_unpaid for entry in registration.entries) or any(
        team.promoted_unpaid for team in registration.teams
    )


def _still_owed_under_window(
    tournament: Tournament, registration: Registration, settled_seating: bool
) -> bool:
    """Whether, once a lapsed promotion has taken back what it seated, the
    registration still owes money that was due within the window that lapsed —
    which is when the ordinary outcome of a lapsed window applies to the rest.

    Owing nothing, or holding no seat, it is left where it is. Before seating
    settles, a seat whose own money was not due yet is left too: a
    `reservation`-mode seat owes by the seating deadline, and a `deposit`-mode
    one whose deposit is in owes its balance by then; neither was ever under
    the window that lapsed, and taking it would lose a seat to a promotion the
    fencer was offered and declined (spec seating-queue)."""
    if registration.settled or registration.fully_queued:
        return False
    if settled_seating:
        return True
    if tournament.payment_mode is PaymentMode.RESERVATION:
        return False
    if tournament.payment_mode is PaymentMode.DEPOSIT:
        return not _deposit_reached(tournament, registration)
    return True


def _deposit_reached(tournament: Tournament, registration: Registration) -> bool:
    """The same threshold `matching._apply_deposit_threshold` closes a window
    on, asked of each lane against its own figure."""
    local, eur = tournament.deposit_amount, tournament.deposit_amount_eur
    return (local is not None and registration.credited_in("local") >= local * 100) or (
        eur is not None and registration.credited_in("eur") >= eur * 100
    )


def _record(
    session: Session,
    tournament: Tournament,
    registration: Registration,
    kind: str,
    demotion: Demotion,
) -> None:
    """The audit line a demotion leaves, naming what it moved. Nothing where it
    moved nothing."""
    if not demotion:
        return
    session.add(
        PaymentEvent(
            tournament_id=tournament.id,
            registration_id=registration.id,
            kind=kind,
            detail=f"{registration.audit_label}: {demotion.detail}",
        )
    )


def _announce(
    session: Session,
    tournament: Tournament,
    mailer: Mailer,
    announced: list[tuple[Registration, Demotion]],
) -> None:
    """Mail every committed demotion, once each, and record the notice beside
    it (spec registration, Demotion is announced).

    After the commit and not before: the tick commits per tournament, a mail
    must never announce a demotion that was rolled back, and the queue
    positions it states are read from what was committed, so they are the ones
    the fencer then sees in the app."""
    if not announced:
        return
    for registration, demotion in announced:
        moved = [
            (entry.discipline.name, queue_position(session, entry)) for entry in demotion.entries
        ]
        moved_teams = [
            (team.name, team.discipline.name, team_waitlist_position(session, team))
            for team in demotion.teams
        ]
        sent = emails.send_demoted(
            mailer, tournament, registration.fencer, registration, moved, moved_teams
        )
        if sent:
            session.add(
                PaymentEvent(
                    tournament_id=tournament.id,
                    registration_id=registration.id,
                    kind="demotion_notified",
                    detail=f"{registration.audit_label}: {demotion.detail}",
                )
            )
    session.commit()


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
            # "still reserved — that is, still owing money" is two conditions
            # now that the paid state has left the enum
            ~Registration.settled,
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


@dataclass(frozen=True)
class PendingSettlement:
    """What settling seating now would move: the registrations, and the seated
    teams among them that would be waitlisted with them."""

    registrations: int
    teams: int


def pending_settlement(session: Session, tournament: Tournament) -> PendingSettlement:
    """What `settle_seating` would move right now — what the console states
    before asking the organizer to confirm an irreversible settlement. Both
    figures are read off the one `_demotable` selection settlement acts on, so
    the confirmation cannot promise a team the settlement then leaves seated
    (spec seating-queue, Organizer-triggered seating settlement)."""
    demotable = _demotable(session, tournament)
    return PendingSettlement(
        registrations=len(demotable),
        teams=sum(
            1 for registration in demotable for team in registration.teams if not team.waitlisted
        ),
    )


def pending_demotions(session: Session, tournament: Tournament) -> int:
    """How many registrations `settle_seating` would move below the line."""
    return pending_settlement(session, tournament).registrations


def settle_seating(session: Session, tournament: Tournament, mailer: Mailer) -> int:
    """Close the tournament's seating: every registration still owing money —
    that is, still RESERVED and not dormant — is moved to the substitute queue
    in place, and the tournament is stamped as settled. Returns how many were
    demoted.

    A pure pass with no trigger condition of its own, so the deadline tick and
    the organizer's settle-early action are literally the same operation
    (design D6); the caller decides when. Every placement it moves takes the
    moment of settlement as its queue moment and so joins the end of the queue;
    registrations moved together share that moment and rank among themselves by
    registration time (`availability.QUEUE_ORDER`). Each is mailed once the
    settlement is committed.

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
    now = _now()
    announced: list[tuple[Registration, Demotion]] = []
    for registration in _demotable(session, tournament):
        demotion = _demote(registration, tournament, now)
        if not demotion:
            continue
        registration.expires_at = None
        _record(session, tournament, registration, "seating_demoted", demotion)
        announced.append((registration, demotion))
    tournament.seating_settled_at = now
    session.commit()
    _announce(session, tournament, mailer, announced)
    return len(announced)


def settle_seating_if_due(
    session: Session, tournament: Tournament, now: datetime, mailer: Mailer
) -> int:
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
    return settle_seating(session, tournament, mailer)


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
            Registration.state == RegistrationState.RESERVED,
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
        emails.send_composition_reminder(
            mailer, tournament, fencer, teams[0].registration, teams, deadline
        )
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
    result["seating_demoted"] = settle_seating_if_due(session, tournament, _now(), mailer)
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
