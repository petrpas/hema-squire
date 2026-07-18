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

from app.models import Fencer, Rule, RuleJournalEntry, Tournament

Row = dict[str, Any]
# A handler mutates the row and returns (field, before, after) triples for audit.
Handler = Callable[[Row, dict], list[tuple[str, Any, Any]]]


def _apply_field_edit(row: Row, payload: dict) -> list[tuple[str, Any, Any]]:
    field, value = payload["field"], payload["value"]
    before = row.get(field)
    row[field] = value
    return [(field, before, value)]


def _apply_row_delete(row: Row, payload: dict) -> list[tuple[str, Any, Any]]:
    before = row.get("_deleted", False)
    row["_deleted"] = True
    return [("_deleted", before, True)]


def _apply_row_restore(row: Row, payload: dict) -> list[tuple[str, Any, Any]]:
    before = row.get("_deleted", False)
    row["_deleted"] = False
    return [("_deleted", before, False)]


def _apply_opaque(row: Row, payload: dict) -> list[tuple[str, Any, Any]]:
    """Kinds consumed by domain engines (e.g. payment links), not by the sheet."""
    return []


HANDLERS: dict[str, Handler] = {
    "field_edit": _apply_field_edit,
    "row_delete": _apply_row_delete,
    "row_restore": _apply_row_restore,
    "match_resolution": _apply_field_edit,
    "payment_link": _apply_opaque,
    "dedup_decision": _apply_opaque,
}


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


def active_rules(session: Session, tournament: Tournament, kind: str | None = None) -> list[Rule]:
    query = (
        select(Rule)
        .where(Rule.tournament_id == tournament.id, Rule.deleted_at.is_(None))
        .order_by(Rule.id)
    )
    if kind is not None:
        query = query.where(Rule.kind == kind)
    return list(session.scalars(query))


def replay(base: dict[str, Row], rules: list[Rule]) -> tuple[dict[str, Row], list[AppliedChange]]:
    """Pure function: identical inputs produce identical state and audit."""
    rows = copy.deepcopy(base)
    audit: list[AppliedChange] = []
    for rule in rules:
        row = rows.get(rule.target)
        if row is None:
            continue  # target vanished from source data; rule is inert, not an error
        handler = HANDLERS[rule.kind]
        for field, before, after in handler(row, rule.payload):
            audit.append(
                AppliedChange(
                    rule_id=rule.id,
                    phase=rule.phase,
                    target=rule.target,
                    field=field,
                    before=before,
                    after=after,
                    actor=rule.author.display_name,
                    at=rule.created_at,
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


def create_rule(
    session: Session,
    tournament: Tournament,
    actor: Fencer,
    phase: str,
    kind: str,
    target: str,
    payload: dict,
) -> Rule:
    if kind not in HANDLERS:
        raise HTTPException(status_code=422, detail="unknown_rule_kind")
    if kind in ("field_edit", "match_resolution") and not (
        isinstance(payload, dict) and "field" in payload and "value" in payload
    ):
        raise HTTPException(status_code=422, detail="payload_requires_field_and_value")
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
