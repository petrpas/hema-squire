"""Base projection of the fencer table: source records as rows, before rules.

Row ids are stable references: in-app registrations are "reg:<id>", imported
rows are "imp:<fingerprint>" (stable across re-uploads of unchanged rows).
Phase views select columns over this same projection; the Import view selects
the "imp:" rows of it.

A row the rules removed carries "_removed_in", the phase of the rule that
deleted or absorbed it. It is a replay product, not a base field: this module
never writes it, and it lives exactly as long as its causing rule.

The projection is returned in the order the fencer list displays: by
registration moment across both populations together, rows without a readable
moment last (spec etl-console, Order of the fencer list). Each row carries the
fixed number allocated to it, or None where none has been.
"""

import datetime
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import hr_match, importer, rownumbers, setup, taxonomy
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


def _wall_clock(value: object, zone: datetime.tzinfo) -> str | None:
    """A registration moment as the wall clock the table shows it as, in a form
    two rows can be compared by.

    An in-app registration states an instant with a zone and is read in the
    tournament's own; an imported row states whatever clock its file did and is
    shown unshifted (spec etl-console, Registration moment in the fencer table).
    Comparing them raw would rank the two kinds against different frames. A
    moment the parser produced that does not read as one is treated as absent —
    it sorts with the rows that state none, rather than somewhere arbitrary.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is not None:
        moment = moment.astimezone(zone).replace(tzinfo=None)
    return moment.isoformat()


def _display_order(rows: dict[str, Row], zone: datetime.tzinfo) -> dict[str, Row]:
    """Both populations interleaved by registration moment, earliest first;
    rows stating none after them, in the order they were numbered — which for
    an imported batch is the order of its file."""

    def key(row: Row) -> tuple:
        moment = _wall_clock(row.get("registered_at"), zone)
        number = row.get("number")
        # an unnumbered row cannot jump ahead of numbered ones on the tiebreak
        rank = number if number is not None else float("inf")
        return (moment is None, moment or "", rank, row["id"])

    return {row["id"]: row for row in sorted(rows.values(), key=key)}


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
                e.discipline.slug for e in registration.entries if not e.is_substitute
            ],
            "substitute_for": [
                e.discipline.slug for e in registration.entries if e.is_substitute
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
    numbers = rownumbers.numbers_for(session, tournament)
    for row_id, row in rows.items():
        # None rather than a positional fallback: a visible gap beats a number
        # that lies (design, Allocation happens where a row is born)
        row["number"] = numbers.get(row_id)
    return _display_order(rows, setup.zone_for(tournament))


def _resolve_discipline_slugs(tournament: Tournament, entries: list) -> tuple[list[str], list[str]]:
    """A stored parse decision's `disciplines` entries, resolved to slugs.

    New-shape entries already are slugs (design discipline-identity D7). Old
    entries — decisions stored before disciplines carried slugs — describe a
    discipline as a `{weapon, gender, material}` dict; each resolves through
    `taxonomy.taxonomy_code` to the offered disciplines sharing that
    classification: to the one when there is exactly one, and to a reported
    problem when the weapon was since split into several (design D8, Risks).
    This shim expires per row at its next re-upload, once it is reparsed into
    the new shape — it is not a permanent fork.
    """
    by_taxonomy_code: dict[str, list] = defaultdict(list)
    for d in tournament.disciplines:
        by_taxonomy_code[d.taxonomy_code].append(d)

    slugs: list[str] = []
    problems: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            slugs.append(entry)
            continue
        code = taxonomy.taxonomy_code(
            entry.get("weapon", ""), entry.get("gender", ""), entry.get("material", "")
        )
        matches = by_taxonomy_code.get(code, [])
        if len(matches) == 1:
            slugs.append(matches[0].slug)
        else:
            problems.append(
                f"legacy discipline {code!r} is ambiguous among this tournament's disciplines"
            )
    return slugs, problems


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
        disciplines, discipline_problems = _resolve_discipline_slugs(
            tournament, record.get("disciplines", [])
        )
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
        problems = record.get("problems")
        if discipline_problems:
            extra = "; ".join(discipline_problems)
            problems = f"{problems} | {extra}" if problems else extra
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
            "problems": problems,
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
