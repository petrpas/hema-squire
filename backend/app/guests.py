"""Who a guest registration belongs to (spec `guest-registration`, A guest's
identity is a record without credentials; design D3).

A sibling of `issuing._resolve_fencer` rather than a use of it: issuing works
through a list in one pass, keeping a `claimed` set, and carries HR bindings by
the organizer's verdict; a guest is one person at a time, binding what they
confirmed themselves. The two read alike on purpose — the address names a
person only where the names agree, and otherwise is somebody's way of reaching
them."""

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hr_index import name_key
from app.models import Fencer, Registration, RegistrationState, Tournament

_ENDED = (RegistrationState.CANCELLED, RegistrationState.EXPIRED)


@dataclass(frozen=True)
class Identity:
    email: str
    name: str
    hr_id: int | None
    nationality: str | None
    club: str | None
    language: str


@dataclass(frozen=True)
class Resolved:
    fencer: Fencer
    # the address the registration's messages go to, where the record does not
    # hold it itself
    contact_email: str | None


def _already_registered() -> HTTPException:
    return HTTPException(status_code=409, detail="already_registered")


def resolve(session: Session, tournament: Tournament, identity: Identity) -> Resolved:
    """The fencer record a guest's submission is held on, created where none
    fits. Refuses an account's address, and the same person entered twice from
    one address. Nothing is flushed for a refusal."""
    key = name_key(identity.name)
    holder = session.scalar(select(Fencer).where(Fencer.email == identity.email))
    if holder is not None and holder.password_hash is not None:
        # a guest entry never attaches a registration to somebody's account
        raise HTTPException(status_code=409, detail="email_has_account")
    if holder is not None and name_key(holder.display_name) == key:
        # the core's own one-registration-per-fencer check refuses a second
        # live registration, and reuses an ended one in place
        return Resolved(holder, None)

    # Seats this address already reaches on this tournament without a record
    # holding it — a parent's children after the first.
    reached = session.scalars(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.contact_email == identity.email,
        )
    ).all()
    for registration in reached:
        if name_key(registration.fencer.display_name) != key:
            continue
        if registration.state not in _ENDED:
            raise _already_registered()
        # entered before and since cancelled or expired: the same record, so
        # the core reuses its registration in place
        return Resolved(registration.fencer, identity.email)

    # the address is somebody's way of reaching this person, not a statement
    # of who they are, wherever it already stands for somebody else
    keeps_address = holder is None and not reached
    fencer = Fencer(
        email=identity.email if keeps_address else None,
        password_hash=None,
        display_name=identity.name,
        hr_id=identity.hr_id,
        nationality=identity.nationality,
        club=identity.club,
        language=identity.language,
    )
    session.add(fencer)
    return Resolved(fencer, None if keeps_address else identity.email)
