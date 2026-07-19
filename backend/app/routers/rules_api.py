from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app import matching, rules, sheet
from app.auth import require_console_access
from app.models import Rule, RuleJournalEntry
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import AppliedChangeOut, RuleIn, RuleOut, RulePayloadIn, SheetOut

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["rules"])


@router.get("/rules", response_model=list[RuleOut])
def list_rules(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    phase: str | None = None,
):
    require_console_access(session, tournament, fencer)
    listed = rules.active_rules(session, tournament)
    if phase is not None:
        listed = [rule for rule in listed if rule.phase == phase]
    return listed


@router.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(
    data: RuleIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    return rules.create_rule(
        session, tournament, fencer, data.phase, data.kind, data.target, data.payload
    )


def _get_rule(session, tournament, rule_id: int) -> Rule:
    rule = session.get(Rule, rule_id)
    if rule is None or rule.tournament_id != tournament.id or rule.deleted_at is not None:
        raise HTTPException(status_code=404, detail="rule_not_found")
    return rule


@router.patch("/rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    data: RulePayloadIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    rule = _get_rule(session, tournament, rule_id)
    return rules.update_rule(session, rule, fencer, data.payload)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    rule = _get_rule(session, tournament, rule_id)
    rules.delete_rule(session, rule, fencer)
    if rule.kind == "payment_link":
        matching.unapply_payment_link(session, tournament, rule)


@router.get("/rules/journal")
def rule_journal(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    entries = session.scalars(
        select(RuleJournalEntry)
        .where(RuleJournalEntry.tournament_id == tournament.id)
        .order_by(RuleJournalEntry.id)
    ).all()
    return [
        {
            "rule_id": entry.rule_id,
            "action": entry.action,
            "actor_id": entry.actor_id,
            "content": entry.content,
            "at": entry.created_at,
        }
        for entry in entries
    ]


@router.get("/sheet", response_model=SheetOut)
def sheet_view(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """The fencer table: base rows with all active rules replayed, plus the
    audit of applied changes (the manual-edits log)."""
    require_console_access(session, tournament, fencer)
    base = sheet.base_rows(session, tournament)
    rows, audit = rules.replay(base, rules.active_rules(session, tournament))
    # Deleted rows are included with _deleted=True so the console can render
    # them greyed with a restore action; exports are where they disappear.
    return SheetOut(
        rows=list(rows.values()),
        edits=[AppliedChangeOut(**change.__dict__) for change in audit],
    )
