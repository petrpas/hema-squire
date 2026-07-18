"""Base projection of the fencer table: source records as rows, before rules.

Row ids are stable references ("reg:<id>"); imported records will join with
their own prefix when table-import lands. Phase views (task 4.3) select
columns over this same projection.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Registration, RegistrationState, Tournament
from app.rules import Row


def base_rows(session: Session, tournament: Tournament) -> dict[str, Row]:
    registrations = session.scalars(
        select(Registration)
        .where(
            Registration.tournament_id == tournament.id,
            Registration.state != RegistrationState.CANCELLED,
        )
        .options(
            selectinload(Registration.fencer),
            selectinload(Registration.entries),
        )
        .order_by(Registration.registered_at)
    ).all()

    rows: dict[str, Row] = {}
    for registration in registrations:
        rows[f"reg:{registration.id}"] = {
            "id": f"reg:{registration.id}",
            "name": registration.fencer.display_name,
            "nationality": registration.fencer.nationality,
            "club": registration.fencer.club,
            "hr_id": registration.fencer.hr_id,
            "disciplines": [
                e.discipline.code for e in registration.entries if not e.is_substitute
            ],
            "substitute_for": [
                e.discipline.code for e in registration.entries if e.is_substitute
            ],
            "state": registration.state.value,
            "vs": registration.vs,
            "paid": registration.state == RegistrationState.PAID,
            "registered_at": registration.registered_at.isoformat(),
            "total_amount": registration.total_amount,
            "expires_at": registration.expires_at.isoformat()
            if registration.expires_at
            else None,
            "paid_at": registration.paid_at.isoformat() if registration.paid_at else None,
            "weapon_rentals": registration.weapon_rentals,
            "afterparty": registration.afterparty,
            "aftersparring": registration.aftersparring,
            "notes": registration.notes,
            "_deleted": False,
        }
    return rows
