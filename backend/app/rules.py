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
from app.hr_index import country_code, evidence_fields
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


def _apply_discipline_amendment(rows: dict[str, Row], target: str, payload: dict):
    """An organizer's correction to the disciplines of a registration that
    already exists.

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

    `before` is the selection the registration was issued with, recorded in the
    payload when the rule was created — not the row's current value, which is
    the amended state and would make every amendment read as a change from
    itself to itself.
    """
    row = rows[target]
    value = payload["value"]
    row["disciplines"] = value
    return [(target, "disciplines", payload.get("base"), value)]


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


def _apply_opaque(rows: dict[str, Row], target: str, payload: dict):
    """Kinds consumed by domain engines (e.g. payment links), not by the sheet."""
    return []


HANDLERS: dict[str, Handler] = {
    "field_edit": _apply_field_edit,
    "row_delete": _apply_row_delete,
    "row_restore": _apply_row_restore,
    "match_resolution": _apply_match_resolution,
    "discipline_amendment": _apply_discipline_amendment,
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


def amendments_for(session: Session, tournament: Tournament, target: str) -> list[list[str]]:
    """The selections the amendments still standing against a row name, oldest
    first. Each states the whole selection, so the last is what the row holds."""
    return [
        rule.payload["value"]
        for rule in active_rules(session, tournament, kind="discipline_amendment")
        if rule.target == target
    ]


def issued_selection(
    session: Session, tournament: Tournament, target: str, registration
) -> list[str]:
    """The disciplines the registration held before any organizer amendment.

    Read off the earliest amendment of this row where there is one — they all
    carry it — and off the registration itself where there is none. A
    substitute placement is in the selection as much as a seated one: what is
    restored is what was entered, not what happened to be seated."""
    for rule in active_rules(session, tournament, kind="discipline_amendment"):
        if rule.target == target and "base" in rule.payload:
            return rule.payload["base"]
    return [entry.discipline.slug for entry in registration.entries]


def create_rule(
    session: Session,
    tournament: Tournament,
    actor: Fencer,
    phase: str,
    kind: str,
    target: str,
    payload: dict,
    index: object | None = None,
) -> Rule:
    if kind not in HANDLERS:
        raise HTTPException(status_code=422, detail="unknown_rule_kind")
    if kind in ("field_edit", "match_resolution", "discipline_amendment") and not (
        isinstance(payload, dict) and "field" in payload and "value" in payload
    ):
        raise HTTPException(status_code=422, detail="payload_requires_field_and_value")
    if kind == "discipline_amendment" and payload.get("field") != "disciplines":
        raise HTTPException(status_code=422, detail="amendment_is_a_disciplines_edit")
    if payload.get("field") == "disciplines" and kind in ("field_edit", "discipline_amendment"):
        # A row's disciplines decide what it is priced at, where it is seated
        # and whether it can be issued at all, so an edit carries the row's own
        # shape — a list of slugs the tournament offers — rather than whatever
        # was typed. Checked here and not only in the console: a slug the
        # tournament does not know would be dropped silently by issuing, and the
        # organizer would meet it as a row that mysteriously will not bill.
        value = payload.get("value")
        offered = {
            discipline.slug
            for discipline in tournament.disciplines
            if discipline.kind is DisciplineKind.INDIVIDUAL
        }
        if not isinstance(value, list) or not value or not all(
            isinstance(slug, str) for slug in value
        ):
            raise HTTPException(status_code=422, detail="disciplines_must_be_a_list")
        unknown = [slug for slug in value if slug not in offered]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail={"code": "unknown_discipline_slug", "slugs": unknown},
            )
        # Which of the two kinds a disciplines edit is is not the console's to
        # choose: it follows from whether a registration stands behind the row.
        # A field edit writes the projection, so accepting one where a
        # registration stands behind the row would move the table and leave the
        # money where it was — silently, which is the whole defect (spec
        # edit-rules, A field edit is refused where it would only move the
        # table).
        registration = amendment.registration_for_row(session, tournament, target)
        if kind == "field_edit" and registration is not None:
            raise HTTPException(status_code=409, detail="row_has_registration")
        if kind == "discipline_amendment":
            if registration is None:
                raise HTTPException(status_code=409, detail="no_registration_for_row")
            if not amendment.is_live(registration):
                raise HTTPException(status_code=409, detail="registration_not_live")
            # The selection the registration was issued with, recorded once and
            # carried by every amendment of this row: it is what a withdrawal
            # returns to, and reading it off the registration later would read
            # the amended state instead. Earlier amendments of the same row
            # already carry it, so it survives their withdrawal.
            payload = {
                **payload,
                "base": issued_selection(session, tournament, target, registration),
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
