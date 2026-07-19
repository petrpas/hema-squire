"""Base projection of the fencer table: source records as rows, before rules.

Row ids are stable references: in-app registrations are "reg:<id>", imported
rows are "imp:<fingerprint>" (stable across re-uploads of unchanged rows).
Phase views (task 4.3) select columns over this same projection.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import hr_match, importer
from app.models import (
    ExtraCategory,
    ImportedRow,
    Registration,
    RegistrationExtra,
    RegistrationState,
    Tournament,
)
from app.rules import Row


def _extras_summary(registration: Registration) -> tuple[list[str], bool, list[str]]:
    """Split a registration's extra-item selections into the v1 sheet's
    fixed slots: rental names, an afterparty flag, and everything else
    (seminar/merch) as freetext labels for the notes summary column."""
    rentals: list[str] = []
    afterparty = False
    other: list[str] = []
    for selection in registration.extra_selections:
        label = (
            f"{selection.item.name} x{selection.qty}"
            if selection.qty > 1
            else selection.item.name
        )
        if selection.item.category == ExtraCategory.RENTAL:
            rentals.append(label)
        elif selection.item.category == ExtraCategory.AFTERPARTY:
            afterparty = True
        else:
            other.append(label)
    return rentals, afterparty, other


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
            selectinload(Registration.extra_selections).selectinload(RegistrationExtra.item),
        )
        .order_by(Registration.registered_at)
    ).all()

    rows: dict[str, Row] = {}
    for registration in registrations:
        extra_rentals, extra_afterparty, extra_other = _extras_summary(registration)
        notes = registration.notes
        if extra_other:
            summary = "; ".join(extra_other)
            notes = f"{notes} | {summary}" if notes else summary
        rows[f"reg:{registration.id}"] = {
            "id": f"reg:{registration.id}",
            "name": registration.fencer.display_name,
            "reg_name": None,
            "nationality": registration.fencer.nationality,
            "club": registration.fencer.club,
            "hr_id": registration.fencer.hr_id,
            "match_verdict": "confirmed" if registration.fencer.hr_id else "unknown",
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
            "weapon_rentals": registration.weapon_rentals or extra_rentals,
            "afterparty": registration.afterparty or extra_afterparty,
            "aftersparring": registration.aftersparring,
            "notes": notes,
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
        name = record.get("name")
        reg_name = record.get("reg_name")
        club = record.get("club")
        nationality = record.get("nationality") or None
        hr_id = record.get("hr_id")
        # fencer-provided hr_id counts as confirmed; otherwise overlay the
        # cached LLM match proposal for the organizer to review
        verdict = "confirmed" if hr_id is not None else "unknown"
        if hr_id is None and name:
            match = importer.get_decision(
                session, tournament, "hr_match", hr_match.identity_key(name, club)
            )
            if match is not None:
                if match.payload.get("hr_id") is not None:
                    hr_id = match.payload["hr_id"]
                    verdict = "proposed"
                    if match.payload.get("matched_name") and match.payload["matched_name"] != name:
                        reg_name = reg_name or name
                        name = match.payload["matched_name"]
                    club = match.payload.get("matched_club") or club
                    nationality = match.payload.get("nationality") or nationality
                else:
                    verdict = "none_found"
        rows[row_id] = {
            "id": row_id,
            "name": name,
            "reg_name": reg_name,
            "nationality": nationality,
            "club": club,
            "hr_id": hr_id,
            "match_verdict": verdict,
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
        "match_verdict": "unknown",
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
