from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import amendment, ledger, matching, rules, sheet
from app.auth import require_console_access, require_published
from app.fieldtypes import RowId
from app.hr_index import HRIndex, get_hr_index
from app.mail import Mailer, get_mailer
from app.models import Rule, RuleJournalEntry
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import (
    AmendmentOut,
    NetChangeOut,
    RuleIn,
    RuleOut,
    RulePayloadIn,
    SheetOut,
)

router = APIRouter(prefix="/api/tournaments/{slug}", tags=["rules"])

HRIndexDep = Annotated[HRIndex, Depends(get_hr_index)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]


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
    data: RuleIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    index: HRIndexDep,
    mailer: MailerDep,
):
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    rule = rules.create_rule(
        session,
        tournament,
        fencer,
        data.phase,
        data.kind,
        data.target,
        data.payload,
        index,
    )
    if rule.kind == rules.AMENDMENT:
        result = _settle_amendments(session, tournament, rule, mailer)
        out = RuleOut.model_validate(rule)
        out.amendment = None if result is None else AmendmentOut(**result.__dict__)
        return out
    return rule


def _settle_amendments(
    session, tournament, rule: Rule, mailer: Mailer
) -> amendment.AmendmentResult | None:
    """Put the registration behind a row into the state its standing
    amendments produce.

    Called where an amendment is created and again where one is withdrawn, the
    way a payment link is applied and unapplied beside its rule: the replay that
    builds the table is a pure function and stays one, so a rule whose subject
    is the registration reaches it from here."""
    registration = amendment.registration_for_row(session, tournament, rule.target)
    if registration is None:
        return None
    return amendment.reapply_amendments(
        session,
        tournament,
        registration,
        # every amendable field, not only the one this rule touched: the
        # amendment restates a whole registration, and `rule` is passed as the
        # withdrawn one so that a field whose last amendment has just gone can
        # still find what it was issued with
        rules.amended_state(session, tournament, rule.target, registration, rule),
        mailer,
    )


def _get_rule(session, tournament, rule_id: int) -> Rule:
    rule = session.get(Rule, rule_id)
    if rule is None or rule.tournament_id != tournament.id or rule.deleted_at is not None:
        raise HTTPException(status_code=404, detail="rule_not_found")
    return rule


@router.patch("/rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: RowId,
    data: RulePayloadIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    rule = _get_rule(session, tournament, rule_id)
    return rules.update_rule(session, rule, fencer, data.payload)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: RowId,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    mailer: MailerDep,
):
    require_console_access(session, tournament, fencer)
    require_published(tournament)
    rule = _get_rule(session, tournament, rule_id)
    rules.delete_rule(session, rule, fencer)
    if rule.kind == "payment_link":
        matching.unapply_payment_link(session, tournament, rule, ledger.actor_label(fencer))
    if rule.kind == rules.AMENDMENT:
        # withdrawal is a replay of what remains, not an inverse of what went:
        # where nothing remains for this field, the registration returns to the
        # value it was issued with, which this rule carries
        _settle_amendments(session, tournament, rule, mailer)


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
def sheet_view(
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
    index: HRIndexDep,
):
    """The fencer table: base rows with all active rules replayed, plus the
    manual-edits log — what differs from the source data, not the history of
    how it got there, so operations that undo one another leave nothing."""
    require_console_access(session, tournament, fencer)
    base = sheet.base_rows(session, tournament, index)
    rows, audit = rules.replay(base, rules.active_rules(session, tournament))
    # Deleted rows are included with _deleted=True so the console can render
    # them greyed with a restore action; exports are where they disappear.
    return SheetOut(
        rows=list(rows.values()),
        edits=[NetChangeOut(**change.__dict__) for change in rules.net_changes(audit)],
    )
