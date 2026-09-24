"""A fencer entered by hand on an automatic tournament: a registration at once.

On a tournament Squire keeps the list of, a fencer arrives by registering in the
application or by an organizer entering them at the console — the door on the
tournament's day, a paper form. Both roads make a registration, placed against
capacity the same way, so that the tournament holds one kind of entrant (spec
registration, A registration entered by hand).

What sets this one apart is that nobody is enrolled in the application: no
account is made, no clock runs, and Squire writes to nobody. Its clocks are
dormant by origin, and the origin is told apart from an issued registration by
the source row it does not have (design manual-entry-registers D2).
"""

import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import issuing, placement, pricing, rownumbers
from app.availability import queued_on_entry
from app.models import (
    Discipline,
    Fencer,
    Registration,
    RegistrationDiscipline,
    RegistrationState,
    Tournament,
)
from app.routers.registrations import next_vs


def _fencer(session: Session, tournament: Tournament, name: str, email: str | None, **fields):
    """A fencer record for the entry, never an account.

    The typed address goes on the new record only where no record holds it. An
    address held by someone already registered here refuses the entry — the
    person is certainly on the list already, and the unique registration per
    fencer would refuse it anyway, less legibly. An address held by anyone else
    is left with them and the new record carries none, as issuing does for an
    address that names somebody else (design manual-entry-registers D4). Any
    other likeness is deduplication's to find."""
    address = (email or "").strip().lower() or None
    if address is not None:
        holder = session.scalar(select(Fencer).where(Fencer.email == address))
        if holder is not None:
            registered = session.scalar(
                select(Registration).where(
                    Registration.tournament_id == tournament.id,
                    Registration.fencer_id == holder.id,
                    Registration.state == RegistrationState.RESERVED,
                )
            )
            if registered is not None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "already_registered": {
                            "registration_id": registered.id,
                            "name": holder.display_name,
                            "vs": registered.vs,
                        }
                    },
                )
            address = None
    fencer = Fencer(
        email=address,
        password_hash=None,
        display_name=name,
        language=tournament.language,
        **fields,
    )
    session.add(fencer)
    return fencer


def register(
    session: Session,
    tournament: Tournament,
    *,
    name: str,
    nationality: str | None,
    club: str | None,
    hr_id: int | None,
    email: str | None,
    registered_at: datetime.datetime,
    disciplines: list[Discipline],
    weapon_rentals: list[str],
    afterparty: bool,
    notes: str | None,
    condition: set[str] | None = None,
) -> Registration:
    """Create the registration for one hand entry, placed, priced and numbered,
    and commit it. Sends nothing: the organizer who entered the fencer is the
    one in contact with them."""
    now = datetime.datetime.now(datetime.UTC)
    queued = queued_on_entry(session, tournament, disciplines, now)
    condition = condition or set()
    fencer = _fencer(
        session,
        tournament,
        name,
        email,
        nationality=nationality,
        club=club,
        hr_id=hr_id,
    )
    for attempt in range(3):
        # a symbol from the tournament's own sequence, so a payment quoting it
        # is matched like any other; `next_vs` commits its own counter bump,
        # which is why a collision retries with a fresh one
        registration = Registration(
            tournament=tournament,
            fencer=fencer,
            state=RegistrationState.RESERVED,
            registered_at=registered_at,
            vs=next_vs(session, tournament),
            # the origin that keeps every clock still and every letter unsent;
            # no source row, which is what names the cause *entered by hand*
            clocks_dormant=True,
            expires_at=None,
            weapon_rentals=weapon_rentals,
            afterparty=afterparty,
            aftersparring=False,
            notes=notes,
        )
        for discipline in disciplines:
            registration.entries.append(
                RegistrationDiscipline(
                    discipline=discipline,
                    queued_since=registered_at,
                    conditional=discipline.slug in condition,
                )
            )
        placement.place(registration.entries, queued)
        session.add(registration)
        try:
            session.flush()
            break
        except IntegrityError:
            session.rollback()
            if attempt == 2:
                raise
            # the rollback took the new fencer with it
            fencer = _fencer(
                session, tournament, name, email, nationality=nationality, club=club, hr_id=hr_id
            )
    else:  # pragma: no cover - the loop always breaks or raises
        raise RuntimeError("vs allocation exhausted its retries")

    issuing.select_extras(
        tournament,
        registration,
        {"weapon_rentals": weapon_rentals, "afterparty": afterparty},
    )
    pricing.reprice(registration, tournament)
    # it enters the tournament's table here and takes its fixed number
    rownumbers.allocate(session, tournament, [f"reg:{registration.id}"])
    session.commit()
    return registration
