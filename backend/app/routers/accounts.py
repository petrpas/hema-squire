from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_fencer, is_deployment_owner
from app.db import get_session
from app.hr_index import HRIndex, HRProfile, get_hr_index
from app.models import Fencer, FencerProfileAudit, OrganizerRequest, RequestState
from app.schemas import AccountOut, AccountUpdate, HRBindIn, PleaIn, PleaOut

router = APIRouter(tags=["accounts"])

SessionDep = Annotated[Session, Depends(get_session)]
FencerDep = Annotated[Fencer, Depends(current_fencer)]
HRIndexDep = Annotated[HRIndex, Depends(get_hr_index)]


@router.get("/api/hr/search", response_model=list[HRProfile])
def hr_search(q: str, hr: HRIndexDep, nationality: str | None = None):
    return hr.search(q, nationality)


@router.get("/api/hr/nationalities", response_model=list[str])
def hr_nationalities(hr: HRIndexDep):
    return hr.nationalities()


def account_out(fencer: Fencer) -> AccountOut:
    out = AccountOut.model_validate(fencer)
    out.is_deployment_owner = is_deployment_owner(fencer)
    return out


@router.get("/api/account", response_model=AccountOut)
def my_account(fencer: FencerDep):
    return account_out(fencer)


def audit_change(session: Session, fencer: Fencer, field: str, new_value: str | None) -> None:
    old_value = getattr(fencer, field)
    if old_value == new_value:
        return
    session.add(
        FencerProfileAudit(
            fencer_id=fencer.id, field=field, old_value=old_value, new_value=new_value
        )
    )
    setattr(fencer, field, new_value)


@router.patch("/api/account", response_model=AccountOut)
def update_account(data: AccountUpdate, session: SessionDep, fencer: FencerDep):
    updates = data.model_dump(exclude_unset=True)
    if "email" in updates:
        taken = session.scalar(
            select(Fencer.id).where(Fencer.email == updates["email"], Fencer.id != fencer.id)
        )
        if taken:
            raise HTTPException(status_code=409, detail="email_already_registered")
    for field, value in updates.items():
        audit_change(session, fencer, field, value)
    session.commit()
    session.refresh(fencer)
    return account_out(fencer)


def bind_profile(session: Session, fencer: Fencer, profile: HRProfile) -> None:
    """Apply an HR profile to an account: canonical name, HR nationality, club if empty."""
    bound_elsewhere = session.scalar(
        select(Fencer.id).where(Fencer.hr_id == profile.hr_id, Fencer.id != fencer.id)
    )
    if bound_elsewhere:
        raise HTTPException(status_code=409, detail="hr_id_already_bound")
    audit_change(session, fencer, "hr_id", profile.hr_id)  # type: ignore[arg-type]
    audit_change(session, fencer, "display_name", profile.name)
    audit_change(session, fencer, "nationality", profile.nationality)
    if not fencer.club:
        audit_change(session, fencer, "club", profile.club)


@router.post("/api/account/hr-binding", response_model=AccountOut)
def bind_hr_later(data: HRBindIn, session: SessionDep, fencer: FencerDep, hr: HRIndexDep):
    if fencer.hr_id is not None:
        raise HTTPException(status_code=409, detail="already_bound")
    profile = hr.get(data.hr_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="hr_profile_not_found")
    bind_profile(session, fencer, profile)
    session.commit()
    session.refresh(fencer)
    return account_out(fencer)


def _plea_out(plea: OrganizerRequest | None) -> PleaOut:
    if plea is None:
        return PleaOut(state=None, message=None, created_at=None, decided_at=None)
    return PleaOut(
        state=plea.state,
        message=plea.message,
        created_at=plea.created_at,
        decided_at=plea.decided_at,
    )


@router.post("/api/account/plea", response_model=PleaOut, status_code=201)
def submit_plea(data: PleaIn, session: SessionDep, fencer: FencerDep):
    """Request the global Organizer role; at most one pending plea per account
    (design D4), a denied account may plead again (new row, history retained)."""
    pending = session.scalar(
        select(OrganizerRequest.id).where(
            OrganizerRequest.fencer_id == fencer.id,
            OrganizerRequest.state == RequestState.PENDING,
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="plea_pending")
    plea = OrganizerRequest(fencer_id=fencer.id, message=data.message)
    session.add(plea)
    session.commit()
    session.refresh(plea)
    return _plea_out(plea)


@router.get("/api/account/plea", response_model=PleaOut)
def my_plea(session: SessionDep, fencer: FencerDep):
    plea = session.scalar(
        select(OrganizerRequest)
        .where(OrganizerRequest.fencer_id == fencer.id)
        .order_by(OrganizerRequest.id.desc())
    )
    return _plea_out(plea)
