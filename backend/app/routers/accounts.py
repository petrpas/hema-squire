from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_fencer
from app.db import get_session
from app.hr_index import HRIndex, HRProfile, get_hr_index
from app.models import Fencer, FencerProfileAudit
from app.schemas import AccountOut, AccountUpdate, HRBindIn

router = APIRouter(tags=["accounts"])

SessionDep = Annotated[Session, Depends(get_session)]
FencerDep = Annotated[Fencer, Depends(current_fencer)]
HRIndexDep = Annotated[HRIndex, Depends(get_hr_index)]


@router.get("/api/hr/search", response_model=list[HRProfile])
def hr_search(q: str, hr: HRIndexDep):
    return hr.search(q)


@router.get("/api/account", response_model=AccountOut)
def my_account(fencer: FencerDep):
    return fencer


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
    return fencer


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
    return fencer
