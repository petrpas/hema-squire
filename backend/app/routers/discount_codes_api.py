"""The organizer's side of discount codes (spec discount-codes).

Everything here is behind console access: a code's text, name and effect appear
on no public response, which is why they have endpoints of their own rather than
a place on the tournament (design add-discount-codes D1).
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import discount_codes, money_bounds, pricing
from app.auth import require_console_access
from app.errors import FieldValidationError
from app.fieldtypes import RowId
from app.models import DiscountCode, Registration, RegistrationState, Tournament
from app.routers.tournaments import FencerDep, SessionDep, TournamentDep
from app.schemas import (
    DiscountCodeIn,
    DiscountCodeOut,
    DiscountCodeRedemptionOut,
    DiscountCodeRedemptionsOut,
    DiscountCodeUsesOut,
    DiscountEffect,
)

router = APIRouter(prefix="/api/tournaments/{slug}/discount-codes", tags=["discount-codes"])


def _out(session: Session, code: DiscountCode) -> DiscountCodeOut:
    return DiscountCodeOut(
        id=code.id,
        code=code.code,
        name=code.name,
        max_uses=code.max_uses,
        effect=DiscountEffect.model_validate(code.effect),
        scope=code.scope,
        uses=discount_codes.uses(session, code),
        locked=discount_codes.carried(session, code),
    )


def _code(session: Session, tournament: Tournament, code_id: int) -> DiscountCode:
    code = session.get(DiscountCode, code_id)
    if code is None or code.tournament_id != tournament.id:
        raise HTTPException(status_code=404, detail="discount_code_not_found")
    return code


def _field_errors(
    session: Session, tournament: Tournament, data: DiscountCodeIn, code: DiscountCode | None
) -> list[dict]:
    errors = []
    if data.effect.kind == "fixed":
        error = money_bounds.local_money_error(tournament, "effect.value", data.effect.value)
        if error:
            errors.append(error)
    duplicate = session.scalar(
        select(DiscountCode.id).where(
            DiscountCode.tournament_id == tournament.id,
            DiscountCode.code == data.code,
        )
    )
    if duplicate is not None and (code is None or duplicate != code.id):
        errors.append({"field": "code", "code": "code_taken"})
    if code is not None and discount_codes.carried(session, code):
        if data.code != code.code:
            errors.append({"field": "code", "code": "code_in_use"})
        if data.effect.model_dump() != _stored_effect(code) or data.scope != code.scope:
            errors.append({"field": "effect", "code": "code_in_use"})
    if code is not None and data.max_uses is not None:
        used = discount_codes.uses(session, code)
        if data.max_uses < used:
            errors.append(
                {"field": "max_uses", "code": "below_uses", "params": {"min": used}},
            )
    return errors


def _stored_effect(code: DiscountCode) -> dict:
    return {"value_eur": None, **code.effect}


def _write(code: DiscountCode, data: DiscountCodeIn) -> None:
    code.code = data.code
    code.name = data.name
    code.max_uses = data.max_uses
    code.effect = data.effect.model_dump()
    code.scope = list(data.scope)


@router.get("", response_model=list[DiscountCodeOut])
def list_codes(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> list[DiscountCodeOut]:
    require_console_access(session, tournament, fencer)
    return [_out(session, code) for code in tournament.discount_codes]


@router.post("", response_model=DiscountCodeOut, status_code=201)
def create_code(
    data: DiscountCodeIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> DiscountCodeOut:
    require_console_access(session, tournament, fencer)
    if not discount_codes.takes_codes(tournament):
        raise HTTPException(status_code=409, detail="manual_tournament_takes_no_codes")
    errors = _field_errors(session, tournament, data, None)
    if errors:
        raise FieldValidationError(errors)
    code = DiscountCode(tournament_id=tournament.id)
    _write(code, data)
    session.add(code)
    session.commit()
    return _out(session, code)


@router.put("/{code_id}", response_model=DiscountCodeOut)
def update_code(
    code_id: RowId,
    data: DiscountCodeIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
) -> DiscountCodeOut:
    require_console_access(session, tournament, fencer)
    code = _code(session, tournament, code_id)
    errors = _field_errors(session, tournament, data, code)
    if errors:
        raise FieldValidationError(errors)
    _write(code, data)
    session.commit()
    return _out(session, code)


@router.delete("/{code_id}", status_code=204)
def delete_code(
    code_id: RowId, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> None:
    require_console_access(session, tournament, fencer)
    code = _code(session, tournament, code_id)
    if discount_codes.carried(session, code):
        raise HTTPException(status_code=409, detail="code_in_use")
    session.delete(code)
    session.commit()


@router.get("/redemptions", response_model=DiscountCodeRedemptionsOut)
def redemptions(
    tournament: TournamentDep, session: SessionDep, fencer: FencerDep
) -> DiscountCodeRedemptionsOut:
    """Who holds which code: live registrations only, so that the rows always
    agree with the uses stated beside them (spec payments-console)."""
    require_console_access(session, tournament, fencer)
    used = discount_codes.uses_by_code(session, tournament)
    holders = session.scalars(
        select(Registration)
        .where(
            Registration.tournament_id == tournament.id,
            Registration.discount_code_id.is_not(None),
            Registration.state == RegistrationState.RESERVED,
        )
        .order_by(Registration.registered_at, Registration.id)
    ).all()
    rows = []
    for registration in holders:
        code = registration.discount_code
        breakdown = pricing.registration_code(registration, tournament)
        if code is None or breakdown is None:
            continue
        rows.append(
            DiscountCodeRedemptionOut(
                registration_id=registration.id,
                fencer=registration.fencer.display_name,
                name=code.name,
                code=code.code,
                deducted=breakdown.deducted or 0,
                currency=tournament.local_currency,
                paid=registration.settled,
            )
        )
    return DiscountCodeRedemptionsOut(
        codes=[
            DiscountCodeUsesOut(
                id=code.id,
                name=code.name,
                max_uses=code.max_uses,
                uses=used.get(code.id, 0),
            )
            for code in tournament.discount_codes
        ],
        rows=rows,
    )
