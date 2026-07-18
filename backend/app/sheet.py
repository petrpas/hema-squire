"""Base projection of the fencer table: source records as rows, before rules.

Row ids are stable references: in-app registrations are "reg:<id>", imported
rows are "imp:<fingerprint>" (stable across re-uploads of unchanged rows).
Phase views (task 4.3) select columns over this same projection.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import importer
from app.models import ImportedRow, Registration, RegistrationState, Tournament
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
            "reg_name": None,
            "nationality": registration.fencer.nationality,
            "club": registration.fencer.club,
            "hr_id": registration.fencer.hr_id,
            "email": registration.fencer.email,
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
            "problems": None,
            "_deleted": False,
        }
    rows.update(_imported_rows(session, tournament))
    return rows


def _imported_rows(session: Session, tournament: Tournament) -> dict[str, Row]:
    batch = importer.latest_batch(session, tournament)
    if batch is None:
        return {}
    imported = session.scalars(
        select(ImportedRow)
        .where(ImportedRow.batch_id == batch.id)
        .order_by(ImportedRow.row_number)
    ).all()

    rows: dict[str, Row] = {}
    for row in imported:
        decision = importer.get_decision(session, tournament, "parse", row.key)
        record = decision.payload if decision else None
        row_id = f"imp:{row.key}"
        if record is None:
            # intake succeeded but the parse did not run (e.g. LLM unconfigured)
            rows[row_id] = _unparsed_row(row_id, row)
            continue
        disciplines = [
            importer.ParsedDiscipline(**d).code for d in record.get("disciplines", [])
        ]
        rows[row_id] = {
            "id": row_id,
            "name": record.get("name"),
            "reg_name": record.get("reg_name"),
            "nationality": record.get("nationality") or None,
            "club": record.get("club"),
            "hr_id": record.get("hr_id"),
            "email": record.get("email"),
            "disciplines": disciplines,
            "substitute_for": [],
            "state": "imported",
            "vs": None,
            "paid": False,
            "registered_at": record.get("registration_time"),
            "total_amount": None,
            "expires_at": None,
            "paid_at": None,
            "weapon_rentals": record.get("borrow", []),
            "afterparty": record.get("after_party") == "Yes",
            "aftersparring": record.get("aftersparring") == "Yes",
            "accommodation": record.get("accommodation"),
            "notes": record.get("notes"),
            "problems": record.get("problems"),
            "_source": {"file": row.batch.filename, "row": row.row_number},
            "_deleted": False,
        }
    return rows


def _unparsed_row(row_id: str, row: ImportedRow) -> Row:
    return {
        "id": row_id,
        "name": None,
        "reg_name": None,
        "nationality": None,
        "club": None,
        "hr_id": None,
        "email": None,
        "disciplines": [],
        "substitute_for": [],
        "state": "imported",
        "vs": None,
        "paid": False,
        "registered_at": None,
        "total_amount": None,
        "expires_at": None,
        "paid_at": None,
        "weapon_rentals": [],
        "afterparty": False,
        "aftersparring": False,
        "accommodation": None,
        "notes": None,
        "problems": "unparsed",
        "_source": {"file": row.batch.filename, "row": row.row_number},
        "_deleted": False,
    }
