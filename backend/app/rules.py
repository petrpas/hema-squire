"""The edit-rules engine.

Current table state = replay(base rows, ordered rule set). Rules apply in
creation order; where several touch the same field the latest wins, and
removing one exposes the earlier value on the next replay. The audit of
applied changes is a replay product, so it lives exactly as long as its
causing rule. Rule creation/update/deletion is journaled append-only.
"""

import copy
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import amendment
from app.hr_index import HRIndex, country_code, evidence_fields
from app.models import DisciplineKind, Fencer, Rule, RuleJournalEntry, Tournament

Row = dict[str, Any]
# A handler mutates rows in place and returns (target, field, before, after)
# quadruples for the audit; most kinds touch only rule.target, dedup merges
# absorb sibling rows too.
Handler = Callable[[dict[str, Row], str, dict], list[tuple[str, str, Any, Any]]]


def _apply_field_edit(rows: dict[str, Row], target: str, payload: dict):
    row = rows[target]
    field, value = payload["field"], payload["value"]
    before = row.get(field)
    row[field] = value
    return [(target, field, before, value)]


def _apply_registration_amendment(rows: dict[str, Row], target: str, payload: dict):
    """An organizer's correction to a priced field of a registration that
    already exists — its disciplines, or the items it borrows.

    The first kind whose subject is not the projected row. What it decides is
    applied to the registration itself — its entries replaced, its total
    recomputed — by `amendment.reapply_amendments`, called where the rule is
    created and again where it is withdrawn, the way a payment link is applied
    beside its rule rather than inside the replay. Replay is a pure function of
    its inputs and stays one; a handler that wrote to the database would make
    every read of the table a write.

    What is left here is the audit line, so the decision reaches the fencer
    list's manual-edits log and can be withdrawn there like any other. The
    projection is written too, but never as the point of the rule: the row's
    disciplines are already read off the amended registration, so this only
    keeps replay coherent for a row whose registration has since gone.

    `before` is the value the registration was issued with, recorded in the
    payload when the rule was created — not the row's current value, which is
    the amended state and would make every amendment read as a change from
    itself to itself.
    """
    row = rows[target]
    field, value = payload["field"], payload["value"]
    row[field] = value
    return [(target, field, payload.get("base"), value)]


def _apply_match_resolution(rows: dict[str, Row], target: str, payload: dict):
    """An organizer's HR verdict: sets hr_id (or its confirmed absence), moves
    the evidence register onto the profile decided upon, and promotes the HR
    canonical name to the display name.

    Promotion belongs here rather than to the match proposal: a fencer becomes
    HR-bound by a verdict, not by a machine's guess (spec hr-integration,
    Canonical naming). The profile travels in the payload, recorded when the
    rule was created, so a replay states the name that was bound at the moment
    of the decision and needs no index of its own.
    """
    changes = _apply_field_edit(rows, target, payload)
    row = rows[target]
    bound = payload["value"] is not None
    verdict = "confirmed" if bound else "none_found"
    before = row.get("match_verdict")
    row["match_verdict"] = verdict
    changes.append((target, "match_verdict", before, verdict))

    # The evidence register is a lookup, not the organizer's edit: it moves
    # with the id without an audit line of its own. The nationality is resolved
    # again on the way out rather than trusted as stored: a rule recorded before
    # the register spoke in ISO codes still carries the index's English spelling,
    # and one row reading "France" beside another reading "FRA" is a difference
    # the organizer would have to explain to themselves.
    nationality = payload.get("hr_nationality") if bound else None
    row["hr_name"] = payload.get("hr_name") if bound else None
    row["hr_nationality"] = country_code(nationality) or nationality
    row["hr_club"] = payload.get("hr_club") if bound else None

    # Promotion is the verdict's consequence, not a second decision, so it
    # leaves no audit line of its own: one decision reads as one entry in the
    # log, the way a resolution's verdict and the id it resolved already do
    # (spec etl-console, HR matching review). The organizer sees the promoted
    # name on the row, and the name they registered under stays beside it.
    canonical = payload.get("hr_name") if bound else None
    if canonical and canonical != row.get("name"):
        if not row.get("reg_name"):
            row["reg_name"] = row.get("name")
        row["name"] = canonical
    return changes


def _apply_row_delete(rows: dict[str, Row], target: str, payload: dict):
    row = rows[target]
    before = row.get("_deleted", False)
    row["_deleted"] = True
    return [(target, "_deleted", before, True)]


def _apply_row_restore(rows: dict[str, Row], target: str, payload: dict):
    row = rows[target]
    before = row.get("_deleted", False)
    row["_deleted"] = False
    return [(target, "_deleted", before, False)]


def _apply_dedup_decision(rows: dict[str, Row], target: str, payload: dict):
    """A confirmed merge: the target row takes the merged field values, the
    absorbed rows disappear from the table (they stay visible in the audit).

    **One decision, one entry.** Only the absorption is reported. The merged
    values and the merge note are applied without appending to the audit, as a
    match resolution's promoted name already is: they are consequences of one
    click, and reporting each of them separately said a single decision five or
    six times over — including, where a field merged one empty value onto
    another, a line stating that nothing had changed (spec etl-console, A merge
    reads as one entry).

    Nothing is lost. Undo still works, since the surviving entry carries the
    rule id and removing the rule reverses the whole merge. What the merge
    decided is on the group's conclusion in the Deduplication view, which is
    where a reader can compare it against the records it came from.
    """
    changes = []
    survivor = rows[target]
    for field, value in payload.get("fields", {}).items():
        survivor[field] = value
    if payload.get("note"):
        survivor["merge_note"] = payload["note"]
    for absorbed_id in payload.get("absorb", []):
        absorbed = rows.get(absorbed_id)
        if absorbed is None:
            continue  # source row vanished; nothing to absorb
        absorbed["_deleted"] = True
        absorbed["_merged_into"] = target
        changes.append((absorbed_id, "_merged_into", None, target))
    return changes


def _apply_rating_override(rows: dict[str, Row], target: str, payload: dict):
    """An organizer's correction to a fetched HEMA Ratings figure.

    The rating is a map on the row, keyed by discipline slug, so the rule
    writes one key of it and leaves the rest of the fetch standing. Replaying
    over a freshly seeded map is what makes the correction survive a ratings
    refresh with no special case in the refresh (design export-tables D2).

    The audit field is `rating:<slug>`, so a fencer entered in two disciplines
    carries two independently attributable cells — and the manual-edits log
    names the discipline the correction was made in.
    """
    row = rows[target]
    slug, rating = payload["discipline"], payload["rating"]
    ratings = dict(row.get("ratings") or {})
    before = ratings.get(slug)
    ratings[slug] = rating
    row["ratings"] = ratings
    return [(target, f"rating:{slug}", before, rating)]


def _apply_opaque(rows: dict[str, Row], target: str, payload: dict):
    """Kinds consumed by domain engines (e.g. payment links), not by the sheet."""
    return []


HANDLERS: dict[str, Handler] = {
    "field_edit": _apply_field_edit,
    "row_delete": _apply_row_delete,
    "row_restore": _apply_row_restore,
    "match_resolution": _apply_match_resolution,
    "registration_amendment": _apply_registration_amendment,
    "rating_override": _apply_rating_override,
    "payment_link": _apply_opaque,
    "dedup_decision": _apply_dedup_decision,
}


def _utc(moment: datetime) -> datetime:
    """Stamp UTC on an instant SQLite handed back naive.

    Every stored instant is UTC, but SQLite drops tzinfo on round-trip even for
    a `DateTime(timezone=True)` column. Serialized without a zone, the console
    reads the instant as its own local time and states the wrong hour on every
    entry of the manual-edits log."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


@dataclass
class AppliedChange:
    rule_id: int
    phase: str
    target: str
    field: str
    before: Any
    after: Any
    actor: str
    at: datetime


@dataclass
class NetChange:
    """One cell's difference from the source data, whatever it took to get
    there. Attribution is the newest contributing rule's: it is the operation
    that put the cell in the state now on screen."""

    phase: str
    target: str
    field: str
    before: Any
    after: Any
    rule_ids: list[int]
    actor: str
    at: datetime


def net_changes(audit: list[AppliedChange]) -> list[NetChange]:
    """Collapse the applied-change history into what differs from the source.

    Changes to one cell chain: the first before is that cell's source-derived
    value, the last after its current one. A chain that returns to where it
    started leaves nothing behind, so operations that undo one another cancel
    instead of stacking.
    """
    groups: dict[tuple[str, str], list[AppliedChange]] = {}
    for change in audit:
        groups.setdefault((change.target, change.field), []).append(change)

    changed = {key: chain for key, chain in groups.items() if chain[0].before != chain[-1].after}
    net = [
        NetChange(
            phase=chain[-1].phase,
            target=target,
            field=field,
            before=chain[0].before,
            after=chain[-1].after,
            rule_ids=[change.rule_id for change in chain],
            actor=chain[-1].actor,
            at=chain[-1].at,
        )
        for (target, field), chain in changed.items()
        # A match resolution states its verdict alongside the id it resolved;
        # while both stand, as two entries they say the same thing twice.
        if not (field == "match_verdict" and (target, "hr_id") in changed)
    ]
    return sorted(net, key=lambda change: change.rule_ids[-1])


def active_rules(session: Session, tournament: Tournament, kind: str | None = None) -> list[Rule]:
    query = (
        select(Rule)
        .where(Rule.tournament_id == tournament.id, Rule.deleted_at.is_(None))
        .order_by(Rule.id)
    )
    if kind is not None:
        query = query.where(Rule.kind == kind)
    return list(session.scalars(query))


def _mark_removal(row: Row, phase: str, field: str, after: Any) -> None:
    """Record on a row which phase took it out of the table, reading the change
    a handler just made.

    A deletion and a merge both remove a row, and either can be undone, so the
    phase is derived afresh on every replay rather than stored: it lives exactly
    as long as the rule that caused it (spec edit-rules, A removed row states
    where it was removed). The console needs it to tell a deletion made on
    Payments from one made on Import, since a phase lists the rows the phases
    before it have not yet removed.
    """
    if field == "_deleted":
        if after is True:
            row["_removed_in"] = phase
        else:
            row.pop("_removed_in", None)
    elif field == "_merged_into":
        # a merge reports where the row went, never that it deleted it
        row["_removed_in"] = phase


def replay(base: dict[str, Row], rules: list[Rule]) -> tuple[dict[str, Row], list[AppliedChange]]:
    """Pure function: identical inputs produce identical state and audit."""
    rows = copy.deepcopy(base)
    audit: list[AppliedChange] = []
    for rule in rules:
        if rule.target not in rows:
            continue  # target vanished from source data; rule is inert, not an error
        handler = HANDLERS[rule.kind]
        for target, field, before, after in handler(rows, rule.target, rule.payload):
            _mark_removal(rows[target], rule.phase, field, after)
            audit.append(
                AppliedChange(
                    rule_id=rule.id,
                    phase=rule.phase,
                    target=target,
                    field=field,
                    before=before,
                    after=after,
                    actor=rule.author.display_name,
                    at=_utc(rule.created_at),
                )
            )
    return rows, audit


def _journal(session: Session, rule: Rule, action: str, actor: Fencer) -> None:
    session.add(
        RuleJournalEntry(
            tournament_id=rule.tournament_id,
            rule_id=rule.id,
            action=action,
            actor_id=actor.id,
            content={
                "phase": rule.phase,
                "kind": rule.kind,
                "target": rule.target,
                "payload": rule.payload,
            },
        )
    )


AMENDMENT = "registration_amendment"

RATING_OVERRIDE = "rating_override"

# The fields of a registration an organizer may correct from the table. Each of
# them is priced, which is why the correction is an amendment rather than a
# field edit: what the row says and what the registration bills have to move
# together. The afterparty and merchandise belong here as soon as they have
# cells to be corrected in.
AMENDABLE_FIELDS = ("disciplines", "weapon_rentals")


def _amendments_of(session: Session, tournament: Tournament, target: str, field: str):
    """The amendments still standing against one field of one row, oldest
    first. Each states the whole of its field, so the last is what holds."""
    return [
        rule
        for rule in active_rules(session, tournament, kind=AMENDMENT)
        if rule.target == target and rule.payload.get("field") == field
    ]


def _issued_value(registration, field: str) -> list:
    """What the registration itself says a field held. A substitute placement
    counts as much as a seated one: what is restored is what was entered, not
    what happened to be seated."""
    if field == "disciplines":
        return [entry.discipline.slug for entry in registration.entries]
    return list(registration.weapon_rentals or [])


def issued_selection(
    session: Session,
    tournament: Tournament,
    target: str,
    registration,
    field: str = "disciplines",
    withdrawn: Rule | None = None,
) -> list:
    """What one field of the registration held before any organizer amendment.

    Read off the earliest amendment of this field on this row where there is one
    — they all carry it — and off the registration itself where there is none.
    `withdrawn` is the rule being removed, which is already out of the active
    set by the time a withdrawal asks: where it was the only amendment of its
    field, its own record of the issued value is the last copy left."""
    for rule in _amendments_of(session, tournament, target, field):
        if "base" in rule.payload:
            return rule.payload["base"]
    if (
        withdrawn is not None
        and withdrawn.payload.get("field") == field
        and "base" in withdrawn.payload
    ):
        return withdrawn.payload["base"]
    return _issued_value(registration, field)


def amended_state(
    session: Session,
    tournament: Tournament,
    target: str,
    registration,
    withdrawn: Rule | None = None,
) -> dict[str, list]:
    """Every amendable field of the registration as the standing amendments
    leave it: the last amendment of each field where there is one, and the
    issued value where there is none.

    All of them together, because an amendment is applied by restating the
    whole registration: rebuilding one field alone would price it against
    whatever the others happened to hold at the time."""
    state = {}
    for field in AMENDABLE_FIELDS:
        standing = _amendments_of(session, tournament, target, field)
        state[field] = (
            standing[-1].payload["value"]
            if standing
            else issued_selection(session, tournament, target, registration, field, withdrawn)
        )
    return state


def _check_rating_override(tournament: Tournament, payload: dict) -> None:
    """A typed rating names a discipline of this tournament and states a
    number, or states that there is none.

    Checked here rather than only in the console for the reason a discipline
    slug is: a slug the tournament does not know would replay onto a key no
    reader looks at, and the organizer would meet it as a correction that
    silently does nothing. Null is a legitimate rating — it is how an organizer
    says the register has nobody by that name — and is not the same as removing
    the rule, which exposes the fetched value again.
    """
    if not isinstance(payload, dict) or "discipline" not in payload or "rating" not in payload:
        raise HTTPException(status_code=422, detail="payload_requires_discipline_and_rating")
    offered = {
        discipline.slug
        for discipline in tournament.disciplines
        if discipline.kind is DisciplineKind.INDIVIDUAL
    }
    slug = payload["discipline"]
    if not isinstance(slug, str) or slug not in offered:
        raise HTTPException(
            status_code=422,
            detail={"code": "unknown_discipline_slug", "slugs": [slug]},
        )
    rating = payload["rating"]
    # bool is an int in Python, and a ticked checkbox reaching this field is a
    # bug in the caller rather than a rating of one
    if rating is not None and (isinstance(rating, bool) or not isinstance(rating, int | float)):
        raise HTTPException(status_code=422, detail="rating_must_be_a_number_or_null")


def create_rule(
    session: Session,
    tournament: Tournament,
    actor: Fencer,
    phase: str,
    kind: str,
    target: str,
    payload: dict,
    index: HRIndex | None = None,
) -> Rule:
    if kind not in HANDLERS:
        raise HTTPException(status_code=422, detail="unknown_rule_kind")
    if kind in ("field_edit", "match_resolution", AMENDMENT) and not (
        isinstance(payload, dict) and "field" in payload and "value" in payload
    ):
        raise HTTPException(status_code=422, detail="payload_requires_field_and_value")
    if kind == AMENDMENT and payload.get("field") not in AMENDABLE_FIELDS:
        raise HTTPException(status_code=422, detail="field_is_not_amendable")
    if kind == RATING_OVERRIDE:
        _check_rating_override(tournament, payload)
    if payload.get("field") in AMENDABLE_FIELDS and kind in ("field_edit", AMENDMENT):
        value = payload.get("value")
        if payload.get("field") == "disciplines":
            # A row's disciplines decide what it is priced at, where it is
            # seated and whether it can be issued at all, so an edit carries the
            # row's own shape — a list of slugs the tournament offers — rather
            # than whatever was typed. Checked here and not only in the console:
            # a slug the tournament does not know would be dropped silently by
            # issuing, and the organizer would meet it as a row that
            # mysteriously will not bill.
            offered = {
                discipline.slug
                for discipline in tournament.disciplines
                if discipline.kind is DisciplineKind.INDIVIDUAL
            }
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(slug, str) for slug in value)
            ):
                raise HTTPException(status_code=422, detail="disciplines_must_be_a_list")
            unknown = [slug for slug in value if slug not in offered]
            if unknown:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "unknown_discipline_slug", "slugs": unknown},
                )
        else:
            # What a row borrows is checked for its shape and nothing else. A
            # name the tournament lends nothing by is not refused: it is a
            # record of what the fencer asked for, billed nothing and stated as
            # such on the row (owner decision, 2026-09-06). Empty is a legitimate
            # answer here as it is not for disciplines — borrowing nothing is a
            # thing a fencer does.
            if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
                raise HTTPException(status_code=422, detail="rentals_must_be_a_list")
        # Which of the two kinds an edit to an amendable field is is not the
        # console's to choose: it follows from whether a registration stands
        # behind the row. A field edit writes the projection, so accepting one
        # where a registration stands behind the row would move the table and
        # leave the money where it was — silently, which is the whole defect
        # (spec edit-rules, A field edit is refused where it would only move the
        # table).
        registration = amendment.registration_for_row(session, tournament, target)
        if kind == "field_edit" and registration is not None:
            raise HTTPException(status_code=409, detail="row_has_registration")
        if kind == AMENDMENT:
            if registration is None:
                raise HTTPException(status_code=409, detail="no_registration_for_row")
            if not amendment.is_live(registration):
                raise HTTPException(status_code=409, detail="registration_not_live")
            # The value the registration was issued with, recorded once per
            # field and carried by every amendment of that field: it is what a
            # withdrawal returns to, and reading it off the registration later
            # would read the amended state instead. Earlier amendments of the
            # same field already carry it, so it survives their withdrawal.
            payload = {
                **payload,
                "base": issued_selection(
                    session, tournament, target, registration, payload["field"]
                ),
            }
    if kind == "match_resolution" and payload.get("value") is not None and index is not None:
        # The profile is read once, here, and stored with the rule: a verdict
        # says which fighter was bound, and replaying it must not depend on an
        # index that may since have been refreshed out from under it. This is
        # also what lets an id typed into the table carry the same consequences
        # as one picked from search (spec etl-console, A typed id is a verdict).
        profile = index.get(payload["value"])
        if profile is not None:
            payload = {**payload, **evidence_fields(profile)}
    rule = Rule(
        tournament_id=tournament.id,
        phase=phase,
        kind=kind,
        target=target,
        payload=payload,
        created_by=actor.id,
    )
    session.add(rule)
    session.flush()
    _journal(session, rule, "created", actor)
    session.commit()
    return rule


def update_rule(session: Session, rule: Rule, actor: Fencer, payload: dict) -> Rule:
    rule.payload = payload
    _journal(session, rule, "updated", actor)
    session.commit()
    return rule


def delete_rule(session: Session, rule: Rule, actor: Fencer) -> None:
    rule.deleted_at = datetime.now(UTC)
    rule.deleted_by = actor.id
    _journal(session, rule, "deleted", actor)
    session.commit()
