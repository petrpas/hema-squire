import base64
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select

from app import emails, pricing, setup, spayd
from app.auth import require_console_access
from app.availability import queue_length, taken_seats
from app.mail import Mailer, get_mailer
from app.models import (
    ExtraItem,
    RefundState,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationState,
    Tournament,
    UnpaidListTreatment,
)
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import (
    AvailabilityOut,
    ParticipantOut,
    PaymentInstructionsOut,
    PricePreviewIn,
    PricePreviewOut,
    RegisterIn,
    RegistrationOut,
)
from app.taxonomy import WEAPONS

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["registrations"])

MailerDep = Annotated[Mailer, Depends(get_mailer)]

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


def next_vs(session) -> int:
    highest = session.scalar(select(func.max(Registration.vs)))
    return (highest or VS_START - 1) + 1


def registration_out(session, registration: Registration) -> dict:
    return {
        "state": registration.state,
        "vs": registration.vs,
        "total_amount": registration.total_amount,
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
    }


@router.get("/availability", response_model=list[AvailabilityOut])
def availability(tournament: TournamentDep, session: SessionDep):
    result = []
    for discipline in tournament.disciplines:
        taken = taken_seats(session, discipline)
        result.append(
            AvailabilityOut(
                code=discipline.code,
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
    total = pricing.selection_total(
        tournament,
        disciplines=selected,
        extras=extras,
        weapon_rentals=data.weapon_rentals,
        afterparty=data.afterparty,
        at=_now().date(),
    )
    return PricePreviewOut(
        total=total,
        currency=tournament.primary_currency,
        eur_total=pricing.to_eur(total, tournament),
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
    if existing is not None and existing.state != RegistrationState.CANCELLED:
        raise HTTPException(status_code=409, detail="already_registered")

    selected, extras = _resolve_selection(tournament, data)
    _validate_options(data.extras, {item.id: item for item in tournament.extra_items})
    full = [d.code for d in selected if taken_seats(session, d) >= d.capacity]

    if full and not data.wait_for_all:
        # The fencer chooses: trim the selection to open disciplines, or resubmit
        # with wait_for_all to queue the whole registration (Decision 7).
        raise HTTPException(status_code=409, detail={"full_disciplines": full})

    as_substitute = bool(full)

    if existing is not None:
        # Re-registering after a cancellation: the (tournament_id, fencer_id)
        # unique constraint forbids a second row, so the cancelled one is
        # reused in place rather than inserting a new registration.
        session.execute(
            delete(RegistrationDiscipline).where(
                RegistrationDiscipline.registration_id == existing.id
            )
        )
        session.execute(
            delete(RegistrationExtra).where(RegistrationExtra.registration_id == existing.id)
        )
        session.flush()
        registration = existing
        registration.state = RegistrationState.RESERVED
        registration.cancelled_at = None
        registration.refundable = None
        registration.refund_state = RefundState.NOT_APPLICABLE
        registration.paid_at = None
    else:
        registration = Registration(tournament=tournament, fencer=fencer)
        session.add(registration)

    registration.registered_at = _now()
    registration.vs = next_vs(session)
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
    session.flush()

    registration.total_amount = pricing.registration_total(registration, tournament)
    registration.expires_at = (
        None
        if as_substitute
        else registration.registered_at + timedelta(days=tournament.reservation_validity_days)
    )
    session.commit()
    emails.send_registration_confirmation(mailer, tournament, fencer, registration)
    return registration_out(session, registration)


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
    return registration_out(session, get_my_registration(session, tournament, fencer))


@router.get("/my-registration/payment", response_model=PaymentInstructionsOut)
def my_registration_payment(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Same content as the confirmation email (design D3): owner-only, and
    only for a reservation that actually owes money right now."""
    registration = get_my_registration(session, tournament, fencer)
    if registration.state != RegistrationState.RESERVED:
        raise HTTPException(status_code=409, detail="not_unpaid")
    if all(e.is_substitute for e in registration.entries):
        raise HTTPException(status_code=409, detail="no_payment_due")
    if not tournament.bank_account:
        raise HTTPException(status_code=404, detail="no_bank_account")

    # built by the same helpers the confirmation email uses, so the two can
    # never drift apart
    message = emails.payment_message(tournament, registration)
    primary, eur = emails.payment_spayd(tournament, registration)
    return PaymentInstructionsOut(
        amount=registration.total_amount,
        currency=tournament.primary_currency,
        iban=tournament.bank_account,
        vs=registration.vs,
        message=message,
        expires_at=registration.expires_at,
        spayd=primary,
        qr_png_base64=base64.b64encode(spayd.qr_png(primary)).decode(),
        eur_amount=pricing.to_eur(registration.total_amount, tournament),
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
    return registration_out(session, registration)


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
    registration.total_amount = pricing.registration_total(registration, tournament)
    registration.expires_at = _now() + timedelta(days=tournament.reservation_validity_days)
    session.commit()
    # Admission opens the payment window: send the payment instructions now.
    emails.send_registration_confirmation(mailer, tournament, registration.fencer, registration)
    return registration_out(session, registration)
