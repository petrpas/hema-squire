"""Canonical JSON export and restore.

The versioned document carries everything the replay architecture needs to
reconstruct the fencer table on an empty deployment: source records
(registrations, import batches), cached decisions, and the rule set. Fencers
travel by email; registration ids are remapped on restore, and rule targets
"reg:<id>" are rewritten accordingly (imp:* targets are content-stable).
Password hashes never leave the deployment.
"""

import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    BankTransaction,
    Discipline,
    ExtraItem,
    Fencer,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    Rule,
    Tournament,
    TournamentOrganizer,
)

SCHEMA_VERSION = 2

_TOURNAMENT_FIELDS = [
    "slug", "display_name", "date", "language",
    "reservation_validity_days", "reminder_day", "amount_tolerance_percent",
    "refundable_until", "bank_account", "unpaid_list_treatment",
    "early_bird_until", "weapon_rental_fee", "weapon_rental_fee_early",
    "afterparty_fee", "afterparty_fee_early",
    "location", "description", "qualification_open", "qualification_criteria",
    "organizers", "discounts",
    "registration_opens", "registration_closes",
]

_REGISTRATION_FIELDS = [
    "registered_at", "state", "vs", "total_amount", "expires_at", "reminded_at",
    "paid_at", "cancelled_at", "refundable", "refund_state",
    "weapon_rentals", "afterparty", "aftersparring", "accommodation", "notes",
]

_TRANSACTION_FIELDS = [
    "external_id", "source", "date", "amount_cents", "currency", "vs", "message",
    "payer_name", "payer_account", "status", "status_reason",
]


def _plain(value: Any) -> Any:
    if isinstance(value, datetime.datetime | datetime.date):
        return value.isoformat()
    if hasattr(value, "value"):  # StrEnum
        return value.value
    return value


def _record(obj: Any, fields: list[str]) -> dict:
    return {field: _plain(getattr(obj, field)) for field in fields}


def export_tournament(session: Session, tournament: Tournament) -> dict:
    registrations = session.scalars(
        select(Registration)
        .where(Registration.tournament_id == tournament.id)
        .options(
            selectinload(Registration.fencer),
            selectinload(Registration.entries),
            selectinload(Registration.extra_selections).selectinload(RegistrationExtra.item),
        )
        .order_by(Registration.id)
    ).all()
    transactions = session.scalars(
        select(BankTransaction)
        .where(BankTransaction.tournament_id == tournament.id)
        .order_by(BankTransaction.id)
    ).all()
    batches = session.scalars(
        select(ImportBatch)
        .where(ImportBatch.tournament_id == tournament.id)
        .order_by(ImportBatch.id)
    ).all()
    rows = session.scalars(
        select(ImportedRow)
        .where(ImportedRow.tournament_id == tournament.id)
        .order_by(ImportedRow.id)
    ).all()
    decisions = session.scalars(
        select(ImportDecision)
        .where(ImportDecision.tournament_id == tournament.id)
        .order_by(ImportDecision.id)
    ).all()
    rules = session.scalars(
        select(Rule)
        .where(Rule.tournament_id == tournament.id, Rule.deleted_at.is_(None))
        .options(selectinload(Rule.author))
        .order_by(Rule.id)
    ).all()

    fencers = {r.fencer.email: r.fencer for r in registrations}
    reg_by_id = {r.id: r for r in registrations}

    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "tournament": _record(tournament, _TOURNAMENT_FIELDS),
        "disciplines": [
            _record(d, ["code", "name", "capacity", "fee", "fee_early"])
            for d in tournament.disciplines
        ],
        "extra_items": [
            _record(i, ["name", "category", "price", "max_qty"])
            for i in tournament.extra_items
        ],
        "fencers": [
            _record(f, ["email", "display_name", "hr_id", "nationality", "club"])
            for f in fencers.values()
        ],
        "registrations": [
            {
                "ref": r.id,
                "fencer_email": r.fencer.email,
                **_record(r, _REGISTRATION_FIELDS),
                "entries": [
                    {"code": e.discipline.code, "is_substitute": e.is_substitute}
                    for e in r.entries
                ],
                "extras": [
                    {
                        "item_name": sel.item.name,
                        "item_category": sel.item.category.value,
                        "qty": sel.qty,
                    }
                    for sel in r.extra_selections
                ],
            }
            for r in registrations
        ],
        "bank_transactions": [
            {
                **_record(t, _TRANSACTION_FIELDS),
                "matched_registration_ref": t.matched_registration_id
                if t.matched_registration_id in reg_by_id
                else None,
            }
            for t in transactions
        ],
        "import_batches": [
            {
                "ref": b.id,
                **_record(b, ["filename", "uploaded_at", "row_count"]),
                "rows": [
                    _record(row, ["row_number", "key", "raw"])
                    for row in rows
                    if row.batch_id == b.id
                ],
            }
            for b in batches
        ],
        "decisions": [
            _record(d, ["kind", "key", "payload", "source"]) for d in decisions
        ],
        "rules": [
            {
                **_record(r, ["phase", "kind", "target", "payload", "created_at"]),
                "author_email": r.author.email,
            }
            for r in rules
        ],
    }


def _parse_dt(value: str | None) -> datetime.datetime | None:
    return datetime.datetime.fromisoformat(value) if value else None


def _parse_date(value: str | None) -> datetime.date | None:
    return datetime.date.fromisoformat(value) if value else None


def restore_tournament(session: Session, data: dict, actor: Fencer) -> Tournament:
    version = data.get("schema_version")
    if version not in (1, SCHEMA_VERSION):
        raise HTTPException(status_code=422, detail="unsupported_schema_version")
    doc = dict(data["tournament"])
    if version == 1:
        # v1 carried organizer_names: list[str]; normalize to the v2 shape
        names = doc.pop("organizer_names", [])
        doc["organizers"] = [{"name": name, "link": None} for name in names]
        doc.setdefault("description", None)
        doc.setdefault("qualification_open", True)
        doc.setdefault("qualification_criteria", None)
    if session.scalar(select(Tournament).where(Tournament.slug == doc["slug"])):
        raise HTTPException(status_code=409, detail="slug_taken")

    tournament = Tournament(
        **{
            **doc,
            "date": _parse_date(doc["date"]),
            "refundable_until": _parse_date(doc.get("refundable_until")),
            "early_bird_until": _parse_date(doc.get("early_bird_until")),
            "registration_opens": _parse_date(doc.get("registration_opens")),
            "registration_closes": _parse_date(doc.get("registration_closes")),
        }
    )
    session.add(tournament)
    session.flush()
    session.add(TournamentOrganizer(tournament_id=tournament.id, fencer_id=actor.id))

    disciplines: dict[str, Discipline] = {}
    for entry in data.get("disciplines", []):
        discipline = Discipline(tournament_id=tournament.id, **entry)
        session.add(discipline)
        disciplines[entry["code"]] = discipline

    extra_items: dict[tuple[str, str], ExtraItem] = {}
    for entry in data.get("extra_items", []):
        item = ExtraItem(tournament_id=tournament.id, **entry)
        session.add(item)
        extra_items[(entry["name"], entry["category"])] = item
    session.flush()

    fencers: dict[str, Fencer] = {}
    for entry in data.get("fencers", []):
        fencer = session.scalar(select(Fencer).where(Fencer.email == entry["email"]))
        if fencer is None:
            fencer = Fencer(**entry)  # restored accounts carry no password
            session.add(fencer)
        fencers[entry["email"]] = fencer
    session.flush()

    reg_map: dict[int, Registration] = {}
    for entry in data.get("registrations", []):
        payload = {k: entry[k] for k in _REGISTRATION_FIELDS}
        for field in ("registered_at", "expires_at", "reminded_at", "paid_at",
                      "cancelled_at"):
            payload[field] = _parse_dt(payload[field])
        registration = Registration(
            tournament_id=tournament.id,
            fencer_id=fencers[entry["fencer_email"]].id,
            **payload,
        )
        session.add(registration)
        session.flush()
        for item in entry["entries"]:
            session.add(
                RegistrationDiscipline(
                    registration_id=registration.id,
                    discipline_id=disciplines[item["code"]].id,
                    is_substitute=item["is_substitute"],
                )
            )
        for extra in entry.get("extras", []):
            key = (extra["item_name"], extra["item_category"])
            if key in extra_items:
                session.add(
                    RegistrationExtra(
                        registration_id=registration.id,
                        extra_item_id=extra_items[key].id,
                        qty=extra["qty"],
                    )
                )
        reg_map[entry["ref"]] = registration

    for entry in data.get("bank_transactions", []):
        ref = entry.pop("matched_registration_ref", None)
        entry["date"] = _parse_date(entry["date"])
        session.add(
            BankTransaction(
                tournament_id=tournament.id,
                matched_registration_id=reg_map[ref].id if ref in reg_map else None,
                **entry,
            )
        )

    for entry in data.get("import_batches", []):
        batch = ImportBatch(
            tournament_id=tournament.id,
            filename=entry["filename"],
            uploaded_by=actor.id,
            uploaded_at=_parse_dt(entry["uploaded_at"]),
            row_count=entry["row_count"],
        )
        session.add(batch)
        session.flush()
        for row in entry["rows"]:
            session.add(
                ImportedRow(batch_id=batch.id, tournament_id=tournament.id, **row)
            )

    for entry in data.get("decisions", []):
        session.add(ImportDecision(tournament_id=tournament.id, **entry))

    for entry in data.get("rules", []):
        target = entry["target"]
        if target.startswith("reg:"):
            ref = int(target.removeprefix("reg:"))
            if ref not in reg_map:
                continue  # rule over a registration absent from the document
            target = f"reg:{reg_map[ref].id}"
        author = fencers.get(entry["author_email"]) or session.scalar(
            select(Fencer).where(Fencer.email == entry["author_email"])
        )
        session.add(
            Rule(
                tournament_id=tournament.id,
                phase=entry["phase"],
                kind=entry["kind"],
                target=target,
                payload=entry["payload"],
                created_by=(author or actor).id,
                created_at=_parse_dt(entry["created_at"]),
            )
        )

    session.commit()
    return tournament
