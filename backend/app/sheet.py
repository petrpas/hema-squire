"""Base projection of the fencer table: source records as rows, before rules.

Row ids are stable references: in-app registrations are "reg:<id>", imported
rows are "imp:<fingerprint>" (stable across re-uploads of unchanged rows), and
fencers the organizer entered by hand are "man:<id>".
Phase views select columns over this same projection; the Import view selects
the "imp:" rows of it.

A row the rules removed carries "_removed_in", the phase of the rule that
deleted or absorbed it. It is a replay product, not a base field: this module
never writes it, and it lives exactly as long as its causing rule.

The projection is returned in the order the fencer list displays: by
registration moment across all three populations together, rows without a readable
moment last (spec etl-console, Order of the fencer list). Each row carries the
fixed number allocated to it, or None where none has been.
"""

import datetime
import decimal
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import hr_match, importer, manualrows, pricing, rownumbers, setup, taxonomy
from app.hr_index import DbHRIndex, HRIndex, evidence_fields
from app.models import (
    Currency,
    ExtraCategory,
    ImportedRow,
    ManualRow,
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
    """Every population interleaved by registration moment, earliest first;
    rows stating none after them, in the order they were numbered — which for
    an imported batch is the order of its file."""

    def key(row: Row) -> tuple:
        moment = _wall_clock(row.get("registered_at"), zone)
        number = row.get("number")
        # an unnumbered row cannot jump ahead of numbered ones on the tiebreak
        rank = number if number is not None else float("inf")
        return (moment is None, moment or "", rank, row["id"])

    return {row["id"]: row for row in sorted(rows.values(), key=key)}


def _evidence(index: HRIndex | None, hr_id: int | None, payload: dict | None = None) -> Row:
    """The evidence register: what HEMA Ratings holds for this id.

    Every row carries the three fields, empty where there is no id or the index
    does not know it — an absence is stated, not omitted (spec etl-console, The
    ledger idiom).

    The index is authoritative. A stored match payload answers only where the
    index cannot, and only for the name and the club: its `nationality` is the
    registration's own where the registration had one, so carrying it here
    would show the claim register's value back as though the profile had
    confirmed it.
    """
    profile = index.get(hr_id) if index is not None and hr_id is not None else None
    if profile is not None:
        return evidence_fields(profile)
    if payload is not None:
        return {
            "hr_name": payload.get("matched_name"),
            "hr_nationality": None,
            "hr_club": payload.get("matched_club"),
        }
    return evidence_fields(None)


def _hr_proposal(
    session: Session, tournament: Tournament, index, name, club, nationality, hr_id
) -> tuple[int | None, dict | None, str]:
    """A row's standing HEMA Ratings match: the id it is bound to or proposed,
    the evidence payload behind a proposal, and the verdict to show.

    A fencer-provided hr_id is a verdict at birth. A cached match binds its id
    and fills the evidence register, and nothing else: the name, club and
    nationality on the row stay the fencer's words until an organizer reaches a
    verdict, or the review has nothing to compare against (spec etl-console,
    The ledger idiom).

    Shared with the registration branch of `base_rows`, because a registration
    issued for a fencer-list row stands in that row's place and has to show what
    the row showed. Issuing binds only a confirmed match, so an unratified
    proposal would otherwise vanish the moment the roster became billable —
    taking with it the only surface that could ratify it.
    """
    if hr_id is not None:
        return hr_id, None, "confirmed"
    if not name:
        return None, None, "unknown"
    match = importer.get_decision(
        session, tournament, "hr_match", hr_match.identity_key(name, club)
    )
    if match is None:
        return None, None, "unknown"
    if match.payload.get("hr_id") is None:
        return None, None, "none_found"
    payload = match.payload
    proposed = payload["hr_id"]
    return proposed, payload, hr_match.derive_tier(name, nationality, proposed, index)


def _add_source_rows(rows: dict[str, Row], source: dict[str, Row]) -> None:
    """Add the rows nothing has issued yet, and carry what the parser doubted
    onto the ones something has.

    A registration issued for a fencer-list row takes that row's id and stands
    in its place, so without this the source row is computed and thrown away —
    and with it every problem the parser recorded. What was doubtful about a row
    does not stop being true because the row became billable: an organizer who
    imported a roster with an unreadable email would otherwise lose the flag at
    the moment they load a statement, which is before they have read it.

    Only the problems come across. Everything else about an issued row is the
    registration's to state, and the registration is what the reader is looking
    at."""
    for row_id, row in source.items():
        if row_id in rows:
            rows[row_id]["problems"] = row["problems"]
        else:
            rows[row_id] = row


def base_rows(
    session: Session, tournament: Tournament, index: HRIndex | None = None
) -> dict[str, Row]:
    # The evidence register needs the fighters index. Callers holding the
    # request's own index pass it, so a test's stub reaches the rows; the rest
    # get the deployment's (spec etl-console, The ledger idiom).
    if index is None:
        index = DbHRIndex(session)
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
        # A registration issued for a fencer-list row stands in that row's
        # place, under the row's own id: the fencer keeps the fixed number the
        # row was born with (spec etl-console, Fixed fencer number), and the
        # list shows them once rather than once as a row and once as a
        # registration. The source rows below are added with `setdefault`, so
        # claiming the id here is what removes the duplicate.
        row_id = registration.source_row_id or f"reg:{registration.id}"
        # A registration issued for a fencer-list row keeps the row's standing
        # match proposal. Issuing binds only a confirmed one, so without this a
        # roster matched but not yet ratified reads as wholly unmatched the
        # moment it becomes billable — and the proposals are unreachable, since
        # ratifying happens on this table.
        row_hr_id, row_hr_payload, row_verdict = _hr_proposal(
            session,
            tournament,
            index,
            registration.fencer.display_name,
            registration.fencer.club,
            registration.fencer.nationality,
            registration.fencer.hr_id,
        )
        extra_rentals, extra_afterparty, extra_other = _extras_summary(registration)
        balance, balance_currency = registration.balance_cents(tournament)
        # What a waiver forgave, where money had already arrived against the
        # price. A waiver owes nothing, so `balance` is zero on such a row and
        # cannot say how much was written off; the console states the figure
        # rather than the bare word wherever a payment stands behind it (owner
        # decision, 2026-09-06). Null where nothing was credited — the whole
        # price was forgiven, and the cell says so in words.
        remaining, _lane = registration.remaining_cents(tournament)
        credited = (
            registration.amount_paid_eur_cents
            if balance_currency == Currency.EUR
            else registration.amount_paid_cents
        )
        waived = (
            _money(remaining)
            if registration.settled_by_hand_at is not None and credited
            else None
        )
        notes = registration.notes
        if extra_other:
            summary = "; ".join(extra_other)
            notes = f"{notes} | {summary}" if notes else summary
        rows[row_id] = {
            "id": row_id,
            "name": registration.fencer.display_name,
            "reg_name": None,
            "nationality": registration.fencer.nationality,
            "club": registration.fencer.club,
            "hr_id": row_hr_id,
            **_evidence(index, row_hr_id, row_hr_payload),
            "match_verdict": row_verdict,
            "email": registration.fencer.email,
            "disciplines": [
                e.discipline.slug for e in registration.entries if not e.is_substitute
            ],
            "substitute_for": [
                e.discipline.slug for e in registration.entries if e.is_substitute
            ],
            "state": registration.state.value,
            # the registration behind this row, where one is behind it. The row
            # id cannot stand in: an issued registration takes its source row's
            # id, so `reg:<id>` is only sometimes the shape (see above). Read by
            # the settled mark, which addresses the registration itself
            "registration_id": registration.id,
            "vs": registration.vs,
            "paid": registration.state == RegistrationState.PAID,
            # settled with nothing passing through Squire, and why. Carried as
            # a row value rather than deduced from a paid state with empty
            # counters, which a waiver holding a recorded payment defeats
            # (design add-manual-payment-entry D4). The outstanding column
            # reads it and states the balance as waived rather than owed
            "settled_by_hand": registration.settled_by_hand_at is not None,
            "settled_by_hand_reason": registration.settled_by_hand_reason,
            # what the waiver forgave, where it forgave only part; null where
            # it forgave the whole price
            "waived_amount": waived,
            "registered_at": registration.registered_at.isoformat(),
            "total_amount": registration.total_amount,
            # what is still owed, as a decimal string exactly as
            # RegistrationOut states it — the same quantity, so the same shape.
            # A row value, not a panel: it reruns, sorts and exports with the
            # rest of the table (design add-payments-console-ui D5).
            #
            # One figure and the currency it is in, decided by
            # `balance_cents`: the two currency lanes are alternative prices,
            # and the row used to carry both as though the second were a
            # conversion of the first.
            "outstanding_amount": _money(balance),
            "outstanding_currency": balance_currency,
            "expires_at": registration.expires_at.isoformat()
            if registration.expires_at
            else None,
            "paid_at": registration.paid_at.isoformat() if registration.paid_at else None,
            "weapon_rentals": registration.weapon_rentals or extra_rentals,
            # of those, the ones this tournament lends nothing by that name and
            # therefore billed nothing for. Stated on the row, because a total
            # that is quietly short is not something an organizer can find
            "unpriced_rentals": pricing.unpriced_rentals(
                tournament, registration.weapon_rentals or []
            ),
            "afterparty": registration.afterparty or extra_afterparty,
            "aftersparring": registration.aftersparring,
            "notes": notes,
            "problems": None,
            "_deleted": False,
        }
    # A source row that has been issued a registration is already present
    # above, as that registration, and must not be drawn a second time as the
    # row it came from
    _add_source_rows(rows, _imported_rows(session, tournament, index))
    _add_source_rows(rows, _manual_rows(session, tournament, index))
    numbers = rownumbers.numbers_for(session, tournament)
    for row_id, row in rows.items():
        # None rather than a positional fallback: a visible gap beats a number
        # that lies (design, Allocation happens where a row is born)
        row["number"] = numbers.get(row_id)
    return _display_order(rows, setup.zone_for(tournament))


def _money(cents: int | None) -> str | None:
    """Cents to the decimal string the API states money in; None stays None,
    which is how a tournament that prices in no EUR says so."""
    if cents is None:
        return None
    return str((decimal.Decimal(cents) / 100).quantize(decimal.Decimal("0.01")))


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


def _imported_rows(
    session: Session, tournament: Tournament, index: HRIndex | None = None
) -> dict[str, Row]:
    """Every row the tournament has imported, from every upload it was given.

    Not the latest batch alone: uploads accumulate, and a row that arrived in an
    earlier file is as much an imported row as one that arrived in the newest
    (spec etl-console, Import view of everything imported). Ordered by id, which
    is arrival — a row is taken in once, when its content first appears.
    """
    imported = session.scalars(
        select(ImportedRow)
        .where(ImportedRow.tournament_id == tournament.id)
        .options(selectinload(ImportedRow.batch))
        .order_by(ImportedRow.id)
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
        hr_id, payload, verdict = _hr_proposal(
            session, tournament, index, name, club, nationality, hr_id
        )
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
            **_evidence(index, hr_id, payload),
            "match_verdict": verdict,
            "email": record.get("email"),
            "disciplines": disciplines,
            "substitute_for": [],
            "state": "imported",
            "vs": None,
            "paid": False,
            "settled_by_hand": False,
            "settled_by_hand_reason": None,
            "waived_amount": None,
            "registration_id": None,
            "registered_at": record.get("registration_time"),
            "total_amount": None,
            "expires_at": None,
            "paid_at": None,
            "weapon_rentals": record.get("borrow", []),
            # named before the row is issued anything, so the item list can be
            # put right while the row is still a row
            "unpriced_rentals": pricing.unpriced_rentals(
                tournament, record.get("borrow", []) or []
            ),
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
        **_evidence(None, None),
        "match_verdict": "unknown",
        "email": None,
        "disciplines": [],
        "substitute_for": [],
        "state": "imported",
        "vs": None,
        "paid": False,
        "settled_by_hand": False,
        "settled_by_hand_reason": None,
        "waived_amount": None,
        "registration_id": None,
        "registered_at": None,
        "total_amount": None,
        "expires_at": None,
        "paid_at": None,
        "weapon_rentals": [],
        "unpriced_rentals": [],
        "afterparty": False,
        "aftersparring": False,
        "accommodation": None,
        "notes": None,
        "problems": "unparsed",
        "_source": {"file": row.batch.filename, "row": row.row_number},
        "_deleted": False,
    }


def _manual_rows(
    session: Session, tournament: Tournament, index: HRIndex | None = None
) -> dict[str, Row]:
    """The fencers the organizer entered by hand.

    Structured at birth — every field was chosen from the tournament's own
    structure — but unmatched unless the organizer supplied an hr_id, the same
    rule an imported row's fencer-provided id follows (spec etl-console, Per-row
    phase status). No `_source`: nothing here came from a file.
    """
    rows: dict[str, Row] = {}
    for row in manualrows.rows_for(session, tournament):
        rows[manualrows.row_id(row)] = _manual_row(row, index)
    return rows


def _manual_row(row: ManualRow, index: HRIndex | None = None) -> Row:
    return {
        "id": f"man:{row.id}",
        "name": row.name,
        "reg_name": None,
        "nationality": row.nationality,
        "club": row.club,
        "hr_id": row.hr_id,
        **_evidence(index, row.hr_id),
        "match_verdict": "confirmed" if row.hr_id is not None else "unknown",
        "email": row.email,
        "disciplines": list(row.disciplines),
        "substitute_for": [],
        "state": "manual",
        "vs": None,
        "paid": False,
        "settled_by_hand": False,
        "settled_by_hand_reason": None,
        "waived_amount": None,
        "registration_id": None,
        "registered_at": row.registered_at.isoformat(),
        "total_amount": None,
        "expires_at": None,
        "paid_at": None,
        "weapon_rentals": list(row.weapon_rentals),
        # a hand-entered row's rentals are checked against the lent items as it
        # is written (`routers.manual_api`), so none of them can be unnamed here
        "unpriced_rentals": [],
        "afterparty": row.afterparty,
        "aftersparring": False,
        "accommodation": None,
        "notes": row.notes,
        "problems": None,
        "_deleted": False,
    }


def source_rows(
    session: Session, tournament: Tournament, index: HRIndex | None = None
) -> list[Row]:
    """The rows matching, deduplication and issuing work on: the ones that
    entered unmatched. An in-app registration is HR-bound at birth and stays out
    of it; an imported row and a hand-entered one both traverse the operations
    (spec etl-console, Per-row phase status).

    Replayed, so what this returns is what the organizer sees — every manual
    edit, deletion and merge applied. Callers filter `_deleted` themselves,
    because what a deleted row means differs by caller: deduplication still has
    to see one to know it was absorbed, and issuing must not give it a
    registration.

    Selected on `state` rather than on the `imp:`/`man:` id prefix, which no
    longer distinguishes them: a registration issued for a source row takes that
    row's id, so the prefix now says where a row came from and the state says
    what it is now. A row that has become a registration has left this
    population — it has been matched, deduplicated and now billed, and handing
    it back to those operations would have them work it a second time.
    """
    from app import rules

    base = base_rows(session, tournament, index)
    replayed, _ = rules.replay(base, rules.active_rules(session, tournament))
    return [row for row in replayed.values() if row["state"] in ("imported", "manual")]
