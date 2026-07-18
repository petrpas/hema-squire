from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app import emails, pricing
from app.auth import require_organizer
from app.mail import Mailer, get_mailer
from app.models import (
    Discipline,
    RefundState,
    Registration,
    RegistrationDiscipline,
    RegistrationState,
    Tournament,
    UnpaidListTreatment,
)
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import AvailabilityOut, ParticipantOut, RegisterIn, RegistrationOut
from app.taxonomy import WEAPONS

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["registrations"])

MailerDep = Annotated[Mailer, Depends(get_mailer)]

VS_START = 1000001


def _now() -> datetime:
    return datetime.now(UTC)


def taken_seats(session, discipline: Discipline) -> int:
    """Capacity is consumed by paid registrations and unexpired reservations."""
    return (
        session.scalar(
            select(func.count())
            .select_from(RegistrationDiscipline)
            .join(Registration)
            .where(
                RegistrationDiscipline.discipline_id == discipline.id,
                RegistrationDiscipline.is_substitute.is_(False),
                (Registration.state == RegistrationState.PAID)
                | (
                    (Registration.state == RegistrationState.RESERVED)
                    & ((Registration.expires_at.is_(None)) | (Registration.expires_at > _now()))
                ),
            )
        )
        or 0
    )


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
        "weapon_rentals": registration.weapon_rentals,
        "afterparty": registration.afterparty,
        "aftersparring": registration.aftersparring,
        "accommodation": registration.accommodation,
        "notes": registration.notes,
        "refundable": registration.refundable,
        "refund_state": registration.refund_state,
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
        queued = session.scalar(
            select(func.count())
            .select_from(RegistrationDiscipline)
            .join(Registration)
            .where(
                RegistrationDiscipline.discipline_id == discipline.id,
                RegistrationDiscipline.is_substitute.is_(True),
                Registration.state == RegistrationState.RESERVED,
            )
        )
        result.append(
            AvailabilityOut(
                code=discipline.code,
                capacity=discipline.capacity,
                taken=taken,
                free=max(discipline.capacity - taken, 0),
                queue_length=queued or 0,
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


@router.post("/register", response_model=RegistrationOut, status_code=201)
def register(
    data: RegisterIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    existing = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == fencer.id,
            Registration.state != RegistrationState.CANCELLED,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="already_registered")

    by_code = {d.code: d for d in tournament.disciplines}
    unknown = [c for c in data.disciplines if c not in by_code]
    if unknown:
        raise HTTPException(status_code=422, detail={"unknown_disciplines": unknown})
    invalid_rentals = [w for w in data.weapon_rentals if w not in WEAPONS]
    if invalid_rentals:
        raise HTTPException(status_code=422, detail={"unknown_weapons": invalid_rentals})

    selected = [by_code[c] for c in data.disciplines]
    full = [d.code for d in selected if taken_seats(session, d) >= d.capacity]

    if full and not data.wait_for_all:
        # The fencer chooses: trim the selection to open disciplines, or resubmit
        # with wait_for_all to queue the whole registration (Decision 7).
        raise HTTPException(status_code=409, detail={"full_disciplines": full})

    as_substitute = bool(full)
    registration = Registration(
        tournament=tournament,
        fencer=fencer,
        registered_at=_now(),
        vs=next_vs(session),
        weapon_rentals=data.weapon_rentals,
        afterparty=data.afterparty,
        aftersparring=data.aftersparring,
        accommodation=data.accommodation,
        notes=data.notes,
    )
    for discipline in selected:
        registration.entries.append(
            RegistrationDiscipline(discipline=discipline, is_substitute=as_substitute)
        )
    session.add(registration)
    session.flush()

    registration.total_amount = pricing.registration_total(registration, tournament)
    if not as_substitute:
        registration.expires_at = registration.registered_at + timedelta(
            days=tournament.reservation_validity_days
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
    require_organizer(session, tournament, fencer)
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
