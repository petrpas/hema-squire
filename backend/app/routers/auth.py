from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_token, hash_password, verify_password
from app.db import get_session
from app.hr_index import HRIndex, get_hr_index
from app.models import Fencer
from app.schemas import LoginIn, SignupIn, TokenOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=201)
def signup(
    data: SignupIn,
    session: Annotated[Session, Depends(get_session)],
    hr: Annotated[HRIndex, Depends(get_hr_index)],
):
    existing = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="email_already_registered")

    if data.hr_id is not None:
        profile = hr.get(data.hr_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="hr_profile_not_found")
        fencer = Fencer(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=profile.name,
            hr_id=profile.hr_id,
            nationality=profile.nationality,
            club=data.club if data.club is not None else profile.club,
            language=data.language,
        )
    else:
        if data.display_name is None:
            raise HTTPException(status_code=422, detail="display_name_required")
        fencer = Fencer(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            club=data.club,
            language=data.language,
        )

    session.add(fencer)
    session.commit()
    return TokenOut(token=create_token(fencer))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, session: Annotated[Session, Depends(get_session)]):
    fencer = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if fencer is None or not fencer.password_hash or not verify_password(
        data.password, fencer.password_hash
    ):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return TokenOut(token=create_token(fencer))
