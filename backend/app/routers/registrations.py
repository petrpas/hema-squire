import base64
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from app import emails, pricing, setup, spayd
from app.auth import require_console_access
from app.availability import queue_length, taken_seats, taken_team_slots, team_queue_length
from app.mail import Mailer, get_mailer
from app.models import (
    Discipline,
    DisciplineKind,
    ExtraItem,
    PaymentEvent,
    RefundState,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationState,
    Team,
    TeamMember,
    Tournament,
    UnpaidListTreatment,
)
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import (
    AvailabilityOut,
    DiscountBreakdownOut,
    ParticipantOut,
    PaymentInstructionsOut,
    PricePreviewIn,
    PricePreviewOut,
    RegisterIn,
    RegistrationOut,
    RosterMemberOut,
    RosterUpdateIn,
    TeamEntryIn,
    TeamEntryOut,
)
from app.taxonomy import WEAPONS

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["registrations"])

MailerDep = Annotated[Mailer, Depends(get_mailer)]

# marks where the legacy sequential range began; no longer allocated from,
# kept only so the gap between it and the structured range (design proposal
# "Risk of collision") stays documented in code
VS_START = 1000001


def _now() -> datetime:
    return datetime.now(UTC)


def queue_position(session, entry: RegistrationDiscipline) -> int:
    earlier = session.scalar(
        select(func.count())
        .select_from(RegistrationDiscipline)
        .join(Registration)
        .where(
            RegistrationDiscipline.discipline_id == entry.discipline_id,
            RegistrationDiscipline.is_substitute.is_(True),
            Registration.state == RegistrationState.RESERVED,
            Registration.registered_at < entry.registration.registered_at,
        )
    )
    return (earlier or 0) + 1


def next_vs(session, tournament: Tournament) -> int:
    """Allocates the next structured VS for `tournament`: YYNNnnn from its
    series prefix and an atomically incremented per-tournament sequence
    (design Decision 3). The counter bump is committed on its own here,
    independent of whatever the caller does next, so a later rollback of the
    registration insert (a retry after a `Registration.vs` collision) cannot
    also undo the bump and hand out the same number twice."""
    seq = (
        session.execute(
            update(Tournament)
            .where(Tournament.id == tournament.id)
            .values(vs_next_seq=Tournament.vs_next_seq + 1)
            .returning(Tournament.vs_next_seq)
        ).scalar_one()
        - 1
    )
    session.commit()
    if seq > 999:
        raise HTTPException(
            status_code=409, detail=f"vs_sequence_exhausted: {tournament.slug}"
        )
    return tournament.vs_prefix * 1000 + seq


def _cents_to_amount(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _team_out(team: Team, tournament: Tournament, at) -> dict:
    prefill = None
    if not team.members:
        # a UI convenience only while the roster is still empty; never
        # persisted as a role (design team-disciplines D5, task 4.6)
        fencer = team.registration.fencer
        prefill = {
            "name": fencer.display_name,
            "hr_id": fencer.hr_id,
            "club": fencer.club,
            "nationality": fencer.nationality,
        }
    return {
        "id": team.id,
        "code": team.discipline.code,
        "name": team.name,
        "waitlisted": team.waitlisted,
        "fee": pricing.discipline_fee(tournament, team.discipline, at, "local"),
        "fee_eur": (
            pricing.discipline_fee(tournament, team.discipline, at, "eur")
            if tournament.shows_eur
            else None
        ),
        "team_min": team.discipline.team_min,
        "team_max": team.discipline.team_max,
        "members": [
            {
                "name": m.name,
                "hr_id": m.hr_id,
                "club": m.club,
                "nationality": m.nationality,
            }
            for m in team.members
        ],
        "prefill": prefill,
    }


def registration_out(session, registration: Registration, tournament: Tournament) -> dict:
    outstanding_eur_cents = registration.outstanding_eur_cents
    at = registration.registered_at.date()
    return {
        "state": registration.state,
        "vs": registration.vs,
        "total_amount": registration.total_amount,
        "outstanding_amount": _cents_to_amount(registration.outstanding_cents),
        "total_eur": registration.total_eur,
        "outstanding_eur_amount": (
            _cents_to_amount(outstanding_eur_cents) if outstanding_eur_cents is not None else None
        ),
        "expires_at": registration.expires_at,
        "registered_at": registration.registered_at,
        "paid_at": registration.paid_at,
        "weapon_rentals": registration.weapon_rentals,
        "afterparty": registration.afterparty,
        "aftersparring": registration.aftersparring,
        "accommodation": registration.accommodation,
        "notes": registration.notes,
        "refundable": registration.refundable,
        "refund_state": registration.refund_state,
        "extras": [
            {
                "extra_item_id": selection.extra_item_id,
                "name": selection.item.name,
                "category": selection.item.category,
                "qty": selection.qty,
                "option_label": selection.item.option_label,
                "option_value": selection.option_value,
            }
            for selection in registration.extra_selections
        ],
        "entries": [
            {
                "code": entry.discipline.code,
                "is_substitute": entry.is_substitute,
                "queue_position": queue_position(session, entry)
                if entry.is_substitute
                else None,
            }
            for entry in registration.entries
        ],
        "teams": [_team_out(team, tournament, at) for team in registration.teams],
    }


@router.get("/availability", response_model=list[AvailabilityOut])
def availability(tournament: TournamentDep, session: SessionDep):
    result = []
    for discipline in tournament.disciplines:
        if discipline.kind == DisciplineKind.TEAM:
            taken = taken_team_slots(session, discipline)
            result.append(
                AvailabilityOut(
                    code=discipline.code,
                    kind=discipline.kind,
                    capacity=discipline.capacity,
                    taken=taken,
                    free=max(discipline.capacity - taken, 0),
                    queue_length=team_queue_length(session, discipline),
                    team_min=discipline.team_min,
                    team_max=discipline.team_max,
                )
            )
        else:
            taken = taken_seats(session, discipline)
            result.append(
                AvailabilityOut(
                    code=discipline.code,
                    kind=discipline.kind,
                    capacity=discipline.capacity,
                    taken=taken,
                    free=max(discipline.capacity - taken, 0),
                    queue_length=queue_length(session, discipline),
                )
            )
    return result


@router.get("/participants", response_model=list[ParticipantOut])
def participants(tournament: TournamentDep, session: SessionDep):
    """Public list: paid registrations as confirmed; unpaid reservations hidden
    or greyed as unconfirmed per the tournament setting. Never as confirmed."""
    show_unpaid = tournament.unpaid_list_treatment == UnpaidListTreatment.GREYED
    rows = session.scalars(
        select(Registration)
        .where(
            Registration.tournament_id == tournament.id,
            (Registration.state == RegistrationState.PAID)
            | (
                (Registration.state == RegistrationState.RESERVED)
                & ((Registration.expires_at.is_(None)) | (Registration.expires_at > _now()))
            ),
        )
        .order_by(Registration.registered_at)
    ).all()

    result = []
    for registration in rows:
        active_codes = [
            e.discipline.code for e in registration.entries if not e.is_substitute
        ]
        if not active_codes:
            continue  # fully-queued substitutes are not participants
        confirmed = registration.state == RegistrationState.PAID
        if not confirmed and not show_unpaid:
            continue
        result.append(
            ParticipantOut(
                name=registration.fencer.display_name,
                club=registration.fencer.club,
                nationality=registration.fencer.nationality,
                disciplines=active_codes,
                status="confirmed" if confirmed else "unconfirmed",
            )
        )
    return result


def _resolve_selection(tournament: Tournament, data) -> tuple[list, list[tuple]]:
    """Validate the billable subset of RegisterIn/PricePreviewIn against the
    tournament's disciplines/extras; shared by register() and price_preview()
    so both reject the same selections the same way."""
    by_code = {d.code: d for d in tournament.disciplines}
    unknown = [c for c in data.disciplines if c not in by_code]
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_disciplines": unknown})
    wrong_kind = [c for c in data.disciplines if by_code[c].kind != DisciplineKind.INDIVIDUAL]
    if wrong_kind:
        # a team discipline is entered through `teams`, not `disciplines`
        raise HTTPException(status_code=422, detail={"team_discipline_not_individual": wrong_kind})
    invalid_rentals = [w for w in data.weapon_rentals if w not in WEAPONS]
    if invalid_rentals:
        raise HTTPException(status_code=422, detail={"unknown_weapons": invalid_rentals})

    extras_by_id = {item.id: item for item in tournament.extra_items}
    unknown_extras = [e.extra_item_id for e in data.extras if e.extra_item_id not in extras_by_id]
    if unknown_extras:
        raise HTTPException(status_code=422, detail={"unknown_extras": unknown_extras})
    over_limit = [
        e.extra_item_id for e in data.extras if e.qty > extras_by_id[e.extra_item_id].max_qty
    ]
    if over_limit:
        raise HTTPException(status_code=422, detail={"extras_over_limit": over_limit})

    selected = [by_code[c] for c in data.disciplines]
    extras = [(extras_by_id[e.extra_item_id], e.qty) for e in data.extras]
    return selected, extras


def _resolve_teams(tournament: Tournament, entries) -> list[tuple[Discipline, object]]:
    """Validate team entries (RegisterIn/PricePreviewIn's `teams`) against the
    tournament's team disciplines. Works for both `TeamEntryIn` (register/
    amend, carries `id`/`name`) and `PreviewTeamIn` (preview, carries only
    `code`) — nothing here reads more than `.code`."""
    by_code = {d.code: d for d in tournament.disciplines}
    unknown = [e.code for e in entries if e.code not in by_code]
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_disciplines": unknown})
    wrong_kind = [e.code for e in entries if by_code[e.code].kind != DisciplineKind.TEAM]
    if wrong_kind:
        raise HTTPException(status_code=422, detail={"discipline_not_team_kind": wrong_kind})
    return [(by_code[e.code], e) for e in entries]


def _team_waitlist_flags(
    session, team_entries: list[tuple[Discipline, object]], *, exclude_registration_id: int | None = None
) -> list[bool]:
    """One waitlisted flag per team entry, in submission order, assigning
    remaining capacity sequentially so two teams entered into the same
    discipline in one submission are not both charged into the same last-open
    slot. `exclude_registration_id` excludes a registration's own current
    teams from the count, so recomputing on amendment does not count a team
    against itself (design team-disciplines 4.3)."""
    counts: dict[int, int] = {}
    flags = []
    for discipline, _ in team_entries:
        if discipline.id not in counts:
            counts[discipline.id] = taken_team_slots(
                session, discipline, exclude_registration_id=exclude_registration_id
            )
        taken = counts[discipline.id]
        waitlisted = taken >= discipline.capacity
        counts[discipline.id] = taken if waitlisted else taken + 1
        flags.append(waitlisted)
    return flags


def _validate_options(selections, extras_by_id: dict[int, ExtraItem]) -> None:
    """An item that declares an option must be answered, and one that declares
    none must not be. A half-filled t-shirt row is a support ticket, so the
    answer is required at submit time rather than defaulted.

    Enforced on registration only, never on the price preview: options do not
    affect price, and refusing to price an unanswered row would make the running
    total read zero while the fencer is still filling the form in."""
    missing: list[int] = []
    invalid: list[int] = []
    unexpected: list[int] = []
    for selection in selections:
        item = extras_by_id[selection.extra_item_id]
        value = (selection.option_value or "").strip()
        if not item.takes_option:
            if value:
                unexpected.append(item.id)
            continue
        if not value:
            missing.append(item.id)
        elif item.option_choices and value not in item.option_choices:
            invalid.append(item.id)
    if missing:
        raise HTTPException(status_code=422, detail={"option_required": missing})
    if invalid:
        raise HTTPException(status_code=422, detail={"option_not_a_choice": invalid})
    if unexpected:
        raise HTTPException(status_code=422, detail={"option_not_accepted": unexpected})


@router.post("/price-preview", response_model=PricePreviewOut)
def price_preview(data: PricePreviewIn, tournament: TournamentDep):
    selected, extras = _resolve_selection(tournament, data)
    team_entries = _resolve_teams(tournament, data.teams)
    team_disciplines = [d for d, _ in team_entries]
    at = _now().date()
    totals = pricing.selection_totals(
        tournament,
        disciplines=selected,
        extras=extras,
        weapon_rentals=data.weapon_rentals,
        afterparty=data.afterparty,
        at=at,
        team_disciplines=team_disciplines,
    )
    discounts = pricing.selection_discounts(
        tournament, disciplines=selected, extras=extras, at=at, team_disciplines=team_disciplines
    )
    return PricePreviewOut(
        total=totals.local,
        currency=tournament.local_currency,
        eur_total=totals.eur,
        discounts=[
            DiscountBreakdownOut(
                name=d.name,
                effect=d.effect,
                applied=d.applied,
                deducted=d.deducted,
                deducted_eur=d.deducted_eur,
            )
            for d in discounts
        ],
    )


@router.post("/register", response_model=RegistrationOut, status_code=201)
def register(
    data: RegisterIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    reason = setup.registration_availability(tournament, _now().date())
    if reason is not None:
        raise HTTPException(status_code=403, detail={"reason": reason})

    existing = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == fencer.id,
        )
    )
    reusable_states = (RegistrationState.CANCELLED, RegistrationState.EXPIRED)
    if existing is not None and existing.state not in reusable_states:
        raise HTTPException(status_code=409, detail="already_registered")

    selected, extras = _resolve_selection(tournament, data)
    if not selected and not data.teams:
        # a team-only registration is valid (spec: "Registration consisting
        # only of a team"), but a registration must carry something
        raise HTTPException(status_code=422, detail="no_disciplines_or_teams")
    team_entries = _resolve_teams(tournament, data.teams)
    _validate_options(data.extras, {item.id: item for item in tournament.extra_items})
    full = [d.code for d in selected if taken_seats(session, d) >= d.capacity]

    if full and not data.wait_for_all:
        # The fencer chooses: trim the selection to open disciplines, or resubmit
        # with wait_for_all to queue the whole registration (Decision 7).
        raise HTTPException(status_code=409, detail={"full_disciplines": full})

    as_substitute = bool(full)

    # `next_vs` durably commits its own counter bump, so a rollback below
    # (retrying after a `Registration.vs` collision) cannot also undo the
    # allocation and hand out the same number twice. Each attempt therefore
    # starts from a session with nothing else pending (design Decision 3).
    for attempt in range(3):
        vs = next_vs(session, tournament)

        if existing is not None:
            # Re-registering after a cancellation or an expiry: the
            # (tournament_id, fencer_id) unique constraint forbids a second
            # row, so the existing one is reused in place rather than
            # inserting a new registration.
            session.execute(
                delete(RegistrationDiscipline).where(
                    RegistrationDiscipline.registration_id == existing.id
                )
            )
            session.execute(
                delete(RegistrationExtra).where(
                    RegistrationExtra.registration_id == existing.id
                )
            )
            # a previous cycle's teams (and their rosters) do not carry
            # forward into a fresh registration cycle, exactly as its
            # disciplines and extras do not
            stale_team_ids = session.scalars(
                select(Team.id).where(Team.registration_id == existing.id)
            ).all()
            if stale_team_ids:
                session.execute(delete(TeamMember).where(TeamMember.team_id.in_(stale_team_ids)))
                session.execute(delete(Team).where(Team.id.in_(stale_team_ids)))
            registration = existing
            registration.state = RegistrationState.RESERVED
            registration.cancelled_at = None
            registration.refundable = None
            registration.refund_state = RefundState.NOT_APPLICABLE
            registration.paid_at = None
            # a new cycle starts from a clean balance; any payment credited to
            # the previous cycle was already flagged for refund by the
            # matcher rather than carried forward
            registration.amount_paid_cents = 0
        else:
            registration = Registration(tournament=tournament, fencer=fencer)
            session.add(registration)

        registration.registered_at = _now()
        # a fresh VS every cycle, deliberately not reused: the previous
        # cycle's VS may still be quoted on a payment in flight, and reusing
        # it would credit an old instruction against a new selection at a new
        # price
        registration.vs = vs
        registration.weapon_rentals = data.weapon_rentals
        registration.afterparty = data.afterparty
        registration.aftersparring = data.aftersparring
        registration.accommodation = data.accommodation
        registration.notes = data.notes
        for discipline in selected:
            registration.entries.append(
                RegistrationDiscipline(discipline=discipline, is_substitute=as_substitute)
            )
        for selection in data.extras:
            value = (selection.option_value or "").strip()
            registration.extra_selections.append(
                RegistrationExtra(
                    extra_item_id=selection.extra_item_id,
                    qty=selection.qty,
                    option_value=value or None,
                )
            )
        # every team entry is fresh on an initial registration — a team's `id`
        # (if the client sent one) is meaningless here and ignored (design
        # team-disciplines 4.2); waitlisting is decided per team, in entry
        # order, never rejecting the submission (spec: "Team entered into a
        # full team discipline")
        team_flags = _team_waitlist_flags(session, team_entries)
        for (discipline, team_in), waitlisted in zip(team_entries, team_flags):
            registration.teams.append(
                Team(tournament_id=tournament.id, discipline=discipline, name=team_in.name, waitlisted=waitlisted)
            )
        try:
            session.flush()
            break
        except IntegrityError:
            session.rollback()
    else:
        raise HTTPException(status_code=409, detail="vs_allocation_failed")

    totals = pricing.registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    registration.expires_at = (
        None
        if as_substitute
        else registration.registered_at + timedelta(days=tournament.reservation_validity_days)
    )
    session.commit()
    emails.send_registration_confirmation(mailer, tournament, fencer, registration)
    return registration_out(session, registration, tournament)


def get_my_registration(session, tournament: Tournament, fencer) -> Registration:
    registration = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == fencer.id,
            Registration.state != RegistrationState.CANCELLED,
        )
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="not_registered")
    return registration


@router.get("/my-registration", response_model=RegistrationOut)
def my_registration(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    return registration_out(session, get_my_registration(session, tournament, fencer), tournament)


@router.post("/my-registration/amend", response_model=RegistrationOut)
def amend_registration(
    data: RegisterIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    reason = setup.amendment_availability(tournament, _now().date())
    if reason is not None:
        raise HTTPException(status_code=403, detail={"reason": reason})

    registration = get_my_registration(session, tournament, fencer)
    if registration.state not in (RegistrationState.RESERVED, RegistrationState.PAID):
        # expired or cancelled registrations return through re-registration
        # instead, a different operation with a different VS (Decision 3)
        raise HTTPException(status_code=409, detail="amend_not_allowed")

    selected, extras = _resolve_selection(tournament, data)
    if not selected and not data.teams:
        raise HTTPException(status_code=422, detail="no_disciplines_or_teams")
    team_entries = _resolve_teams(tournament, data.teams)
    _validate_options(data.extras, {item.id: item for item in tournament.extra_items})

    was_paid = registration.state == RegistrationState.PAID
    previous_total = registration.total_amount

    # drop the current selection before checking capacity, so the fencer's own
    # existing seats are not counted as taken against themselves
    session.execute(
        delete(RegistrationDiscipline).where(
            RegistrationDiscipline.registration_id == registration.id
        )
    )
    session.execute(
        delete(RegistrationExtra).where(RegistrationExtra.registration_id == registration.id)
    )

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
        # `existing_teams`), so the ORM does not know to drop the deleted rows
        # from its cached collection on its own — same reasoning as
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
    full = {d.code for d in selected if taken_seats(session, d) >= d.capacity}
    team_flags = _team_waitlist_flags(
        session, team_entries, exclude_registration_id=registration.id
    )

    registration.weapon_rentals = data.weapon_rentals
    registration.afterparty = data.afterparty
    registration.aftersparring = data.aftersparring
    registration.accommodation = data.accommodation
    registration.notes = data.notes
    for discipline in selected:
        registration.entries.append(
            RegistrationDiscipline(
                discipline=discipline, is_substitute=discipline.code in full
            )
        )
    for selection in data.extras:
        value = (selection.option_value or "").strip()
        registration.extra_selections.append(
            RegistrationExtra(
                extra_item_id=selection.extra_item_id,
                qty=selection.qty,
                option_value=value or None,
            )
        )
    for (discipline, team_in), waitlisted in zip(team_entries, team_flags):
        if team_in.id is not None and team_in.id in keep_ids:
            team = existing_teams[team_in.id]
            team.discipline = discipline
            team.name = team_in.name
            team.waitlisted = waitlisted
        else:
            registration.teams.append(
                Team(tournament_id=tournament.id, discipline=discipline, name=team_in.name, waitlisted=waitlisted)
            )
    session.flush()

    # vs and expires_at are read-only through this path: amending must not
    # renew the hold or reissue the QR (Decision 3, the load-bearing guarantee)
    totals = pricing.registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    overpaid = registration.outstanding_cents < 0 or (registration.outstanding_eur_cents or 0) < 0
    if was_paid and overpaid:
        registration.refund_state = RefundState.PENDING

    session.add(
        PaymentEvent(
            tournament_id=tournament.id,
            registration_id=registration.id,
            kind="registration_amended",
            detail=f"VS {registration.vs}: {previous_total} -> {registration.total_amount}",
        )
    )
    session.commit()

    underpaid = registration.outstanding_cents > 0 or (registration.outstanding_eur_cents or 0) > 0
    if was_paid:
        if underpaid:
            emails.send_surcharge_due(mailer, tournament, fencer, registration)
    else:
        emails.send_amendment_confirmation(mailer, tournament, fencer, registration)
    return registration_out(session, registration, tournament)


@router.get("/my-registration/payment", response_model=PaymentInstructionsOut)
def my_registration_payment(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Same content as the confirmation email (design D3): owner-only, and
    only for a reservation that actually owes money right now."""
    registration = get_my_registration(session, tournament, fencer)
    if registration.state != RegistrationState.RESERVED:
        raise HTTPException(status_code=409, detail="not_unpaid")
    # nothing owed when every individual entry is queued and every team is
    # waitlisted — vacuously true on whichever axis carries nothing, so a
    # team-only registration is judged on its teams alone (design
    # team-disciplines: a team-only registration is priced like any other)
    if all(e.is_substitute for e in registration.entries) and all(
        t.waitlisted for t in registration.teams
    ):
        raise HTTPException(status_code=409, detail="no_payment_due")
    if not tournament.bank_account:
        raise HTTPException(status_code=404, detail="no_bank_account")

    # built by the same helpers the confirmation email uses, so the two can
    # never drift apart
    message = emails.payment_message(tournament, registration)
    primary, eur = emails.payment_spayd(tournament, registration)
    return PaymentInstructionsOut(
        amount=registration.total_amount,
        currency=tournament.local_currency,
        iban=tournament.bank_account,
        vs=registration.vs,
        message=message,
        expires_at=registration.expires_at,
        spayd=primary,
        qr_png_base64=base64.b64encode(spayd.qr_png(primary)).decode(),
        eur_amount=registration.total_eur,
        eur_spayd=eur,
        eur_qr_png_base64=(
            base64.b64encode(spayd.qr_png(eur)).decode() if eur else None
        ),
    )


@router.post("/my-registration/cancel", response_model=RegistrationOut)
def cancel_registration(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    registration = get_my_registration(session, tournament, fencer)
    was_paid = registration.state == RegistrationState.PAID
    registration.cancelled_at = _now()
    registration.state = RegistrationState.CANCELLED
    if was_paid:
        refundable = (
            tournament.refundable_until is not None
            and registration.cancelled_at.date() <= tournament.refundable_until
        )
        registration.refundable = refundable
        registration.refund_state = (
            RefundState.PENDING if refundable else RefundState.NOT_APPLICABLE
        )
    session.commit()
    return registration_out(session, registration, tournament)


@router.post("/registrations/{registration_id}/admit/{code}", response_model=RegistrationOut)
def admit_substitute(
    registration_id: int,
    code: str,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    require_console_access(session, tournament, fencer)
    registration = session.get(Registration, registration_id)
    if registration is None or registration.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="registration_not_found")
    entry = next(
        (e for e in registration.entries if e.discipline.code == code and e.is_substitute),
        None,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="no_substitute_entry")
    if registration.state != RegistrationState.RESERVED:
        raise HTTPException(status_code=409, detail="registration_not_active")
    if taken_seats(session, entry.discipline) >= entry.discipline.capacity:
        raise HTTPException(status_code=409, detail="discipline_full")

    entry.is_substitute = False
    # Fees are frozen to the original registration date; admission bills the
    # admitted discipline (plus extras on first admission) and opens a fresh window.
    totals = pricing.registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    registration.expires_at = _now() + timedelta(days=tournament.reservation_validity_days)
    session.commit()
    # Admission opens the payment window: send the payment instructions now.
    emails.send_registration_confirmation(mailer, tournament, registration.fencer, registration)
    return registration_out(session, registration, tournament)


def _team_for_roster_edit(session, tournament: Tournament, fencer, team_id: int) -> Team:
    """The entering fencer's own team, on a registration that may still be
    edited — never gated by amendment_availability (design team-disciplines
    D6): refused only on a cancelled or expired registration."""
    team = session.get(Team, team_id)
    if team is None or team.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="team_not_found")
    registration = team.registration
    if registration.fencer_id != fencer.id:
        raise HTTPException(status_code=404, detail="team_not_found")
    if registration.state in (RegistrationState.CANCELLED, RegistrationState.EXPIRED):
        raise HTTPException(status_code=409, detail="registration_not_active")
    return team


@router.put(
    "/my-registration/teams/{team_id}/roster", response_model=TeamEntryOut
)
def update_roster(
    team_id: int,
    data: RosterUpdateIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    """Whole-roster replace: add, remove, rename, rebind, and reorder are all
    expressed as a new member list, persisted as `ordinal` (spec: "The roster
    is an ordered list without roles"). Deliberately untouched here: price,
    VS, email, refund state, and capacity (design D6) — this endpoint does not
    import pricing, emails, or availability, and does not consult
    `setup.amendment_availability`, so a roster save succeeds even after the
    amendment window has closed (design team-disciplines 4.4/4.5)."""
    team = _team_for_roster_edit(session, tournament, fencer, team_id)
    if len(data.members) > team.discipline.team_max:
        raise HTTPException(
            status_code=422,
            detail={"roster_over_maximum": team.discipline.team_max},
        )
    session.execute(delete(TeamMember).where(TeamMember.team_id == team.id))
    session.flush()
    for ordinal, member in enumerate(data.members):
        session.add(
            TeamMember(
                team_id=team.id,
                ordinal=ordinal,
                name=member.name,
                hr_id=member.hr_id,
                club=member.club,
                nationality=member.nationality,
            )
        )
    session.commit()
    session.refresh(team)
    return _team_out(team, tournament, team.registration.registered_at.date())
