"""Registering without an account (spec `guest-registration`)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app import guests, managekey
from app.hr_index import HRIndex, get_hr_index
from app.outgoing import QueuedMailerDep
from app.ratelimit import limiter
from app.routers.registrations import create_registration, registration_out, send_confirmation
from app.routers.tournaments import SessionDep, TournamentDep
from app.schemas import GuestRegisterIn, GuestRegistrationOut, RegistrationOut

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["registrations"])


@router.post("/guest-register", response_model=GuestRegistrationOut, status_code=201)
@limiter.limit("3/minute")
def guest_register(
    request: Request,
    data: GuestRegisterIn,
    tournament: TournamentDep,
    session: SessionDep,
    hr: Annotated[HRIndex, Depends(get_hr_index)],
    mailer: QueuedMailerDep,
):
    """A guest's identity and selection, submitted together: the registration
    is created now or not at all, and nothing exists for a visitor who filled
    in the guest form and left. Rate-limited as signup is."""
    guest = data.guest
    if guest.hr_id is not None:
        profile = hr.get(guest.hr_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="hr_profile_not_found")
        name, nationality = profile.name, profile.nationality
        club = guest.club if guest.club is not None else profile.club
    else:
        if guest.display_name is None:
            raise HTTPException(status_code=422, detail="display_name_required")
        name, nationality, club = guest.display_name, None, guest.club

    identity = guests.Identity(
        email=guest.email,
        name=name,
        hr_id=guest.hr_id,
        nationality=nationality,
        club=club,
        language=guest.language,
    )
    resolved = guests.resolve(session, tournament, identity)
    registration = create_registration(
        session,
        tournament,
        resolved.fencer,
        data,
        contact_email=resolved.contact_email,
        guest=True,
    )
    send_confirmation(session, mailer, tournament, resolved.fencer, registration)
    key = managekey.key_for(registration)
    if key is None:  # create_registration(guest=True) always gives one
        raise HTTPException(status_code=500, detail="manage_key_missing")
    return GuestRegistrationOut(
        registration=RegistrationOut.model_validate(
            registration_out(session, registration, tournament)
        ),
        manage_key=key,
    )
