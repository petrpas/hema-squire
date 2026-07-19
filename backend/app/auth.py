"""Email + password authentication and authorization.

Two independent layers:
- the global role ladder (Role enum; rank-based capabilities, with the
  deployment Owner computed from settings.owner_email, never stored), and
- per-tournament console access (Tournament Owner via tournaments.owner_id,
  team members via TournamentOrganizer). No global role grants console
  access — Admins manage people, not tournaments.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import Fencer, Role, Tournament, TournamentOrganizer

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return secrets.compare_digest(digest.hex(), digest_hex)


def create_token(fencer: Fencer) -> str:
    payload = {
        "sub": str(fencer.id),
        "exp": datetime.now(UTC) + timedelta(hours=settings.token_ttl_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def current_fencer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> Fencer:
    if credentials is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid_token") from None
    fencer = session.get(Fencer, int(payload["sub"]))
    if fencer is None:
        raise HTTPException(status_code=401, detail="unknown_account")
    return fencer


def is_deployment_owner(fencer: Fencer) -> bool:
    return bool(settings.owner_email) and fencer.email == settings.owner_email


_RANK = {Role.FENCER: 0, Role.ORGANIZER: 1, Role.ADMIN: 2}


def has_role(fencer: Fencer, minimum: Role) -> bool:
    """Rank check on the global ladder; the deployment Owner outranks all."""
    return is_deployment_owner(fencer) or _RANK[fencer.role] >= _RANK[minimum]


def require_role(fencer: Fencer, minimum: Role) -> None:
    if not has_role(fencer, minimum):
        raise HTTPException(status_code=403, detail="insufficient_role")


def require_console_access(session: Session, tournament: Tournament, fencer: Fencer) -> None:
    """Tournament Owner or team member; no global role bypasses this."""
    if tournament.owner_id == fencer.id:
        return
    member = session.scalar(
        select(TournamentOrganizer.id).where(
            TournamentOrganizer.tournament_id == tournament.id,
            TournamentOrganizer.fencer_id == fencer.id,
        )
    )
    if member is None:
        raise HTTPException(status_code=403, detail="not_an_organizer")


def require_tournament_owner(tournament: Tournament, fencer: Fencer) -> None:
    if tournament.owner_id != fencer.id:
        raise HTTPException(status_code=403, detail="not_tournament_owner")
