"""Redeeming a discount code (spec discount-codes).

How a code prices is `pricing`'s. What is here is whether a typed string is a
code anyone may use, and taking one of its uses.

**Every way of not being usable answers the same.** Unknown, another
tournament's and exhausted are one refusal, so that no answer discloses that a
code ever existed.

**Uses are counted, not kept.** They are the live registrations carrying the
code, so a cancellation or an expiry gives one back by leaving the count, and
there is no figure to keep right (design add-discount-codes D3).
"""

import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import (
    DiscountCode,
    Registration,
    RegistrationsKeptBy,
    RegistrationState,
    Tournament,
)

UNAVAILABLE = "code_unavailable"


def normalize(typed: str) -> str:
    """A code as it is stored: lower case, no diacritics, hyphens for spaces,
    so ` ŠKOLA` finds `skola` and `Trenéři HEMA` finds `treneri-hema`."""
    decomposed = unicodedata.normalize("NFKD", typed.strip())
    bare = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", "-", bare.casefold())


def uses(session: Session, code: DiscountCode) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.discount_code_id == code.id,
                Registration.state == RegistrationState.RESERVED,
            )
        )
        or 0
    )


def uses_by_code(session: Session, tournament: Tournament) -> dict[int, int]:
    rows = session.execute(
        select(Registration.discount_code_id, func.count())
        .where(
            Registration.tournament_id == tournament.id,
            Registration.discount_code_id.is_not(None),
            Registration.state == RegistrationState.RESERVED,
        )
        .group_by(Registration.discount_code_id)
    ).all()
    return {code_id: count for code_id, count in rows if code_id is not None}


def carried(session: Session, code: DiscountCode) -> bool:
    """Whether any registration row carries the code, live or not: what locks
    it (design add-discount-codes D5). An expired row can come back."""
    return (
        session.scalar(select(Registration.id).where(Registration.discount_code_id == code.id))
        is not None
    )


def _has_room(code: DiscountCode, used: int) -> bool:
    return code.max_uses is None or used < code.max_uses


def takes_codes(tournament: Tournament) -> bool:
    """A manual tournament has no form to type one into."""
    return tournament.registrations_kept_by == RegistrationsKeptBy.SQUIRE


def accepts_codes(session: Session, tournament: Tournament) -> bool:
    """Whether any code is usable now, which is all the public learns."""
    if not takes_codes(tournament) or not tournament.discount_codes:
        return False
    used = uses_by_code(session, tournament)
    return any(_has_room(code, used.get(code.id, 0)) for code in tournament.discount_codes)


def find_usable(session: Session, tournament: Tournament, typed: str) -> DiscountCode:
    """The tournament's code `typed` names, or the one refusal."""
    code = None
    if takes_codes(tournament):
        code = session.scalar(
            select(DiscountCode).where(
                DiscountCode.tournament_id == tournament.id,
                DiscountCode.code == normalize(typed),
            )
        )
    if code is None or not _has_room(code, uses(session, code)):
        raise HTTPException(status_code=422, detail=UNAVAILABLE)
    return code


def claim(session: Session, code: DiscountCode) -> None:
    """Take a use for a registration already flushed carrying `code`.

    Touching the code's row is the lock: it holds SQLite's write lock and
    Postgres's row lock, so two registrations racing for the last use are
    counted one after the other and the second sees the first (design
    add-discount-codes D3). The count then includes the registration itself.
    Refusing rolls back, so the submission creates nothing."""
    session.execute(
        update(DiscountCode).where(DiscountCode.id == code.id).values(name=DiscountCode.name)
    )
    if code.max_uses is not None and uses(session, code) > code.max_uses:
        session.rollback()
        raise HTTPException(status_code=422, detail=UNAVAILABLE)
