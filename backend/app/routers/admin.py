"""Minimal admin panel API: account list, role management, plea queue, and
audited HR unbinding. Every endpoint requires the Admin role or higher
(the deployment Owner outranks Admin — see app.auth.has_role)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_fencer, is_deployment_owner, require_role
from app.db import get_session
from app.models import Fencer, OrganizerRequest, RequestState, Role
from app.routers.accounts import audit_change
from app.schemas import (
    AdminAccountOut,
    PleaDecisionOut,
    PleaQueueOut,
    RoleUpdateIn,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

SessionDep = Annotated[Session, Depends(get_session)]
FencerDep = Annotated[Fencer, Depends(current_fencer)]


def _admin_account_out(
    session: Session, account: Fencer, shared_hr_ids: set[int]
) -> AdminAccountOut:
    out = AdminAccountOut.model_validate(account)
    out.is_deployment_owner = is_deployment_owner(account)
    out.has_pending_plea = bool(
        session.scalar(
            select(OrganizerRequest.id).where(
                OrganizerRequest.fencer_id == account.id,
                OrganizerRequest.state == RequestState.PENDING,
            )
        )
    )
    out.hr_shared = account.hr_id in shared_hr_ids
    return out


def _shared_hr_ids(session: Session) -> set[int]:
    """hr_ids bound by more than one account (design D4)."""
    rows = session.scalars(
        select(Fencer.hr_id)
        .where(Fencer.hr_id.isnot(None))
        .group_by(Fencer.hr_id)
        .having(func.count(Fencer.id) > 1)
    )
    return set(rows)


@router.get("/accounts", response_model=list[AdminAccountOut])
def list_accounts(session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    accounts = session.scalars(select(Fencer).order_by(Fencer.email)).all()
    shared_hr_ids = _shared_hr_ids(session)
    return [_admin_account_out(session, account, shared_hr_ids) for account in accounts]


def _authorize_role_change(actor: Fencer, target: Fencer, new_role: Role) -> None:
    """Owner grants/revokes Admin and everything below; an Admin (not the
    Owner) may only grant/revoke Organizer and never touches an Admin
    account or the Owner (design D1/D2, spec: Global role model)."""
    if is_deployment_owner(target):
        raise HTTPException(status_code=403, detail="cannot_edit_owner")
    if is_deployment_owner(actor):
        return
    if target.role == Role.ADMIN or new_role == Role.ADMIN:
        raise HTTPException(status_code=403, detail="insufficient_role")


@router.patch("/accounts/{fencer_id}/role", response_model=AdminAccountOut)
def set_role(fencer_id: int, data: RoleUpdateIn, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    target = session.get(Fencer, fencer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    _authorize_role_change(fencer, target, data.role)
    target.role = data.role
    session.commit()
    session.refresh(target)
    return _admin_account_out(session, target, _shared_hr_ids(session))


@router.post("/accounts/{fencer_id}/hr-unbind", response_model=AdminAccountOut)
def hr_unbind(fencer_id: int, session: SessionDep, fencer: FencerDep):
    """Clear a wrongly linked hr_id; profile fields keep their values and the
    change is audited (design D6). Fencer-side rebinding stays write-once —
    unaffected by this endpoint, since bind_hr_later only checks hr_id."""
    require_role(fencer, Role.ADMIN)
    target = session.get(Fencer, fencer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    audit_change(session, target, "hr_id", None)
    session.commit()
    session.refresh(target)
    return _admin_account_out(session, target, _shared_hr_ids(session))


@router.get("/pleas", response_model=list[PleaQueueOut])
def list_pleas(session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    rows = session.scalars(
        select(OrganizerRequest)
        .where(OrganizerRequest.state == RequestState.PENDING)
        .order_by(OrganizerRequest.created_at)
    ).all()
    return [
        PleaQueueOut(
            id=row.id,
            fencer_id=row.fencer_id,
            email=row.fencer.email,
            display_name=row.fencer.display_name,
            message=row.message,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _get_pending_plea(session: Session, plea_id: int) -> OrganizerRequest:
    plea = session.get(OrganizerRequest, plea_id)
    if plea is None:
        raise HTTPException(status_code=404, detail="plea_not_found")
    if plea.state != RequestState.PENDING:
        raise HTTPException(status_code=409, detail="plea_not_pending")
    return plea


@router.post("/pleas/{plea_id}/grant", response_model=PleaDecisionOut)
def grant_plea(plea_id: int, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    plea = _get_pending_plea(session, plea_id)
    plea.state = RequestState.GRANTED
    plea.decided_at = datetime.now(UTC)
    plea.decided_by = fencer.id
    plea.fencer.role = Role.ORGANIZER
    session.commit()
    return PleaDecisionOut(id=plea.id, state=plea.state)


@router.post("/pleas/{plea_id}/deny", response_model=PleaDecisionOut)
def deny_plea(plea_id: int, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    plea = _get_pending_plea(session, plea_id)
    plea.state = RequestState.DENIED
    plea.decided_at = datetime.now(UTC)
    plea.decided_by = fencer.id
    session.commit()
    return PleaDecisionOut(id=plea.id, state=plea.state)
