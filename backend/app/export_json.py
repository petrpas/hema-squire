"""Canonical JSON export and restore.

The versioned document carries everything the replay architecture needs to
reconstruct the fencer table on an empty deployment: source records
(registrations, import batches), cached decisions, and the rule set. Fencers
travel by email; registration ids are remapped on restore, and rule targets
"reg:<id>" and "man:<id>" are rewritten accordingly (imp:* targets are
content-stable).
Password hashes never leave the deployment.
"""

import datetime
import decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import rownumbers, taxonomy
from app.constraints import DEFAULT_TIMEZONE
from app.models import (
    BankTransaction,
    Discipline,
    ExtraItem,
    Fencer,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    ManualRow,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    Rule,
    SheetRowNumber,
    Team,
    TeamMember,
    Tournament,
    TournamentOrganizer,
)
from app.routers.tournaments import _lowest_free_series

SCHEMA_VERSION = 11

_TOURNAMENT_FIELDS = [
    "slug", "display_name", "date", "language",
    "reservation_validity_days", "reminder_day", "amount_tolerance_percent",
    "refundable_until", "bank_account", "unpaid_list_treatment",
    "early_bird_until", "weapon_rental_fee", "weapon_rental_fee_early",
    "afterparty_fee", "afterparty_fee_early",
    "location", "description", "qualification_open", "qualification_criteria",
    "registration_instructions",
    "local_currency", "eur_payments_enabled", "eur_rate",
    "organizers", "discounts",
    "registration_opens", "registration_opens_time", "registration_closes",
    "timezone",
    "vs_year", "vs_series", "vs_next_seq",
    "team_composition_deadline",
]

# v6 addition, defaulted when restoring an older file so a v1-v5 export lands
# with no composition deadline (design team-disciplines D8)
_V6_TOURNAMENT_DEFAULTS = {"team_composition_deadline": None}

# v8 additions. A v1-v7 export carries no opening time — it was written when
# the only opening moment was the start of a day — and no zone, so it lands
# with the default one, exactly as the migration backfilled the tournaments
# that file was taken from (change add-registration-open-time)
_V7_TOURNAMENT_DEFAULTS = {
    "registration_opens_time": None,
    "timezone": DEFAULT_TIMEZONE,
}

# v3 additions, defaulted when restoring an older file so a v1/v2 export lands
# as the CZK, EUR-off, option-less tournament it was
_V3_TOURNAMENT_DEFAULTS = {
    "registration_instructions": None,
    "local_currency": "CZK",
    "eur_payments_enabled": False,
    "eur_rate": None,
}

_REGISTRATION_FIELDS = [
    "registered_at", "state", "vs", "total_amount", "total_eur", "expires_at",
    "reminded_at", "paid_at", "cancelled_at", "refundable", "refund_state",
    # what has actually been credited, in both lanes. Carried since v11: a
    # restore that reconstructs the totals but not the credit leaves every
    # registration reading as if nothing had been paid against it, while its
    # state still says paid.
    "amount_paid_cents", "amount_paid_eur_cents",
    "weapon_rentals", "afterparty", "aftersparring", "accommodation", "notes",
]

_TRANSACTION_FIELDS = [
    "external_id", "source", "date", "amount_cents", "currency", "vs", "message",
    "payer_name", "payer_account", "status", "status_reason",
]


_MANUAL_ROW_FIELDS = [
    "name", "nationality", "club", "hr_id", "email", "registered_at",
    "disciplines", "weapon_rentals", "afterparty", "notes", "created_at",
]


def _author_email(session: Session, fencer_id: int) -> str | None:
    author = session.get(Fencer, fencer_id)
    return author.email if author else None


def _plain(value: Any) -> Any:
    if isinstance(value, datetime.datetime | datetime.date):
        return value.isoformat()
    if hasattr(value, "value"):  # StrEnum
        return value.value
    # exchange rates are Decimal; a string keeps the exact value through JSON
    if isinstance(value, decimal.Decimal):
        return str(value)
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
            selectinload(Registration.teams).selectinload(Team.discipline),
            selectinload(Registration.teams).selectinload(Team.members),
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
    manual = session.scalars(
        select(ManualRow)
        .where(ManualRow.tournament_id == tournament.id)
        .order_by(ManualRow.id)
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

    row_numbers = session.scalars(
        select(SheetRowNumber)
        .where(SheetRowNumber.tournament_id == tournament.id)
        .order_by(SheetRowNumber.number)
    ).all()

    fencers = {r.fencer.email: r.fencer for r in registrations}
    reg_by_id = {r.id: r for r in registrations}

    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "tournament": _record(tournament, _TOURNAMENT_FIELDS),
        "disciplines": [
            _record(
                d,
                [
                    "slug", "name", "weapon", "gender", "material", "kind",
                    "team_min", "team_max",
                    "capacity", "fee", "fee_early", "fee_eur", "fee_early_eur",
                ],
            )
            for d in tournament.disciplines
        ],
        "extra_items": [
            _record(
                i,
                [
                    "name", "category", "price", "price_eur", "max_qty",
                    "option_label", "option_choices",
                ],
            )
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
                    {"slug": e.discipline.slug, "is_substitute": e.is_substitute}
                    for e in r.entries
                ],
                "extras": [
                    {
                        "item_name": sel.item.name,
                        "item_category": sel.item.category.value,
                        "qty": sel.qty,
                        "option_value": sel.option_value,
                    }
                    for sel in r.extra_selections
                ],
                "teams": [
                    {
                        "name": team.name,
                        "discipline_slug": team.discipline.slug,
                        "waitlisted": team.waitlisted,
                        "members": [
                            {
                                "name": m.name,
                                "hr_id": m.hr_id,
                                "club": m.club,
                                "nationality": m.nationality,
                            }
                            for m in team.members
                        ],
                    }
                    for team in r.teams
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
        # the hand-entered fencers, by the id their row id is built from, so
        # their numbers and the rules over them can be rewritten on restore (v10)
        "manual_rows": [
            {
                "ref": m.id,
                **_record(m, _MANUAL_ROW_FIELDS),
                "author_email": _author_email(session, m.created_by),
            }
            for m in manual
        ],
        "decisions": [
            _record(d, ["kind", "key", "payload", "source"]) for d in decisions
        ],
        # the fixed numbers, so a restored tournament keeps the numbers its
        # fencers were given rather than renumbering everyone (v9)
        "row_numbers": [
            {"row_id": n.row_id, "number": n.number} for n in row_numbers
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


def _parse_time(value: str | None) -> datetime.time | None:
    return datetime.time.fromisoformat(value) if value else None


def restore_tournament(session: Session, data: dict, actor: Fencer) -> Tournament:
    version = data.get("schema_version")
    if version not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, SCHEMA_VERSION):
        raise HTTPException(status_code=422, detail="unsupported_schema_version")
    doc = dict(data["tournament"])
    if version == 1:
        # v1 carried organizer_names: list[str]; normalize to the v2 shape
        names = doc.pop("organizer_names", [])
        doc["organizers"] = [{"name": name, "link": None} for name in names]
        doc.setdefault("description", None)
        doc.setdefault("qualification_open", True)
        doc.setdefault("qualification_criteria", None)
    if version < 4:
        for field, default in _V3_TOURNAMENT_DEFAULTS.items():
            doc.setdefault(field, default)
    if version < 5 and "primary_currency" in doc:
        # the field was renamed local_currency in v5; a v2-v4 export still
        # carries the old key (design Decision 2)
        doc["local_currency"] = doc.pop("primary_currency")
    if version < 6:
        for field, default in _V6_TOURNAMENT_DEFAULTS.items():
            doc.setdefault(field, default)
    if version < 8:
        for field, default in _V7_TOURNAMENT_DEFAULTS.items():
            doc.setdefault(field, default)
    if session.scalar(select(Tournament).where(Tournament.slug == doc["slug"])):
        raise HTTPException(status_code=409, detail="slug_taken")

    if version < 4:
        # a pre-v4 export predates the series entirely; its registrations
        # carry only legacy sequential VS, so a fresh series consumes none of
        # their range — same reasoning as the migration's backfill (design
        # Decision 7)
        restore_year = _parse_date(doc["date"]).year
        doc["vs_year"] = restore_year
        doc["vs_series"] = _lowest_free_series(session, restore_year)
        doc["vs_next_seq"] = 1

    tournament = Tournament(
        **{
            **doc,
            "date": _parse_date(doc["date"]),
            "refundable_until": _parse_date(doc.get("refundable_until")),
            "early_bird_until": _parse_date(doc.get("early_bird_until")),
            "registration_opens": _parse_date(doc.get("registration_opens")),
            "registration_opens_time": _parse_time(doc.get("registration_opens_time")),
            "registration_closes": _parse_date(doc.get("registration_closes")),
            "team_composition_deadline": _parse_date(doc.get("team_composition_deadline")),
        }
    )
    session.add(tournament)
    session.flush()
    session.add(TournamentOrganizer(tournament_id=tournament.id, fencer_id=actor.id))

    disciplines: dict[str, Discipline] = {}
    for entry in data.get("disciplines", []):
        # kind/team_min/team_max arrived in v6; an older file's disciplines
        # are all individual (design team-disciplines D8)
        fields = {"kind": "individual", "team_min": None, "team_max": None, **entry}
        if "code" in fields:
            # a pre-split document carries a discipline's identity and
            # classification packed into one "code" — that value becomes the
            # slug verbatim, and the classification is parsed back out of it,
            # exactly as the migration backfills stored rows (design
            # discipline-identity Migration Plan)
            code = fields.pop("code")
            weapon, gender, material = taxonomy.parse_code(code)
            fields = {
                **fields, "slug": code, "weapon": weapon, "gender": gender, "material": material,
            }
        discipline = Discipline(tournament_id=tournament.id, **fields)
        session.add(discipline)
        disciplines[fields["slug"]] = discipline

    extra_items: dict[tuple[str, str], ExtraItem] = {}
    for entry in data.get("extra_items", []):
        # option fields arrived in v3; an older file's items declare no option
        fields = {
            "option_label": None,
            "option_choices": [],
            **entry,
        }
        item = ExtraItem(tournament_id=tournament.id, **fields)
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
        # total_eur arrived in v5; an older file's registrations priced in
        # local currency only. The credited counters arrived in v11; a document
        # written before that recorded no credit, which restores as zero — the
        # same reading those deployments already had.
        entry = {
            "total_eur": None,
            "amount_paid_cents": 0,
            "amount_paid_eur_cents": 0,
            **entry,
        }
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
            # "code" is the pre-v7 key; a v7+ document carries "slug"
            slug = item.get("slug", item.get("code"))
            if slug not in disciplines:
                raise HTTPException(
                    status_code=422, detail=f"unknown_discipline_slug: {slug}"
                )
            session.add(
                RegistrationDiscipline(
                    registration_id=registration.id,
                    discipline_id=disciplines[slug].id,
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
                        option_value=extra.get("option_value"),
                    )
                )
        # teams arrived in v6; an older file's registrations carry none
        # (design team-disciplines D8). A member is restored as the plain
        # record it is — never as a Fencer (design D4)
        for team_entry in entry.get("teams", []):
            # "discipline_code" is the pre-v7 key; a v7+ document carries
            # "discipline_slug"
            slug = team_entry.get("discipline_slug", team_entry.get("discipline_code"))
            if slug not in disciplines:
                raise HTTPException(
                    status_code=422, detail=f"unknown_discipline_slug: {slug}"
                )
            team = Team(
                tournament_id=tournament.id,
                registration_id=registration.id,
                discipline_id=disciplines[slug].id,
                name=team_entry["name"],
                waitlisted=team_entry["waitlisted"],
            )
            session.add(team)
            session.flush()
            for ordinal, member in enumerate(team_entry.get("members", [])):
                session.add(
                    TeamMember(
                        team_id=team.id,
                        ordinal=ordinal,
                        name=member["name"],
                        hr_id=member.get("hr_id"),
                        club=member.get("club"),
                        nationality=member.get("nationality"),
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
    man_map: dict[int, ManualRow] = {}
    for entry in data.get("manual_rows", []):
        fields = {field: entry[field] for field in _MANUAL_ROW_FIELDS if field in entry}
        fields["registered_at"] = _parse_dt(fields.get("registered_at"))
        fields["created_at"] = _parse_dt(fields.get("created_at"))
        author = fencers.get(entry.get("author_email")) or session.scalar(
            select(Fencer).where(Fencer.email == entry.get("author_email"))
        )
        row = ManualRow(
            tournament_id=tournament.id, created_by=(author or actor).id, **fields
        )
        session.add(row)
        session.flush()
        man_map[entry["ref"]] = row
    session.flush()

    if "row_numbers" in data:
        # registration ids are remapped on restore, so their row ids are
        # rewritten the way rules over them are; imported keys are content
        # fingerprints and carry over as they stand
        pairs = []
        for entry in data["row_numbers"]:
            row_id = entry["row_id"]
            if row_id.startswith("reg:"):
                ref = int(row_id.removeprefix("reg:"))
                if ref not in reg_map:
                    continue  # a number for a registration this document omits
                row_id = f"reg:{reg_map[ref].id}"
            elif row_id.startswith("man:"):
                ref = int(row_id.removeprefix("man:"))
                if ref not in man_map:
                    continue  # a number for a manual row this document omits
                row_id = f"man:{man_map[ref].id}"
            pairs.append((row_id, entry["number"]))
        rownumbers.restore(session, tournament, pairs)
    else:
        # a document written before numbers existed: allocate in the order the
        # rows would have arrived in
        rownumbers.allocate(session, tournament, rownumbers.arrival_order(session, tournament))

    for entry in data.get("decisions", []):
        session.add(ImportDecision(tournament_id=tournament.id, **entry))

    for entry in data.get("rules", []):
        target = entry["target"]
        if target.startswith("reg:"):
            ref = int(target.removeprefix("reg:"))
            if ref not in reg_map:
                continue  # rule over a registration absent from the document
            target = f"reg:{reg_map[ref].id}"
        elif target.startswith("man:"):
            ref = int(target.removeprefix("man:"))
            if ref not in man_map:
                continue  # rule over a manual row absent from the document
            target = f"man:{man_map[ref].id}"
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
