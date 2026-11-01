"""Admin panel API: account list, role management, plea queue, audited HR
unbinding, and the tournament list with its delete. Every endpoint requires the Admin role or higher
(the deployment Owner outranks Admin — see app.auth.has_role)."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import tournament_delete
from app.auth import current_fencer, is_deployment_owner, require_role
from app.db import get_session
from app.fieldtypes import RowId
from app.models import (
    Fencer,
    OrganizerRequest,
    PaymentCredit,
    Registration,
    RequestState,
    Role,
    Tournament,
)
from app.routers.accounts import audit_change
from app.schemas import (
    AdminAccountOut,
    AdminCreditedOut,
    AdminTournamentOut,
    AdminTournamentOwnerOut,
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
    # the `isnot(None)` above already excluded them; the filter is what says so
    return {hr_id for hr_id in rows if hr_id is not None}


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
def set_role(fencer_id: RowId, data: RoleUpdateIn, session: SessionDep, fencer: FencerDep):
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
def hr_unbind(fencer_id: RowId, session: SessionDep, fencer: FencerDep):
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
def grant_plea(plea_id: RowId, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    plea = _get_pending_plea(session, plea_id)
    plea.state = RequestState.GRANTED
    plea.decided_at = datetime.now(UTC)
    plea.decided_by = fencer.id
    plea.fencer.role = Role.ORGANIZER
    session.commit()
    return PleaDecisionOut(id=plea.id, state=plea.state)


@router.post("/pleas/{plea_id}/deny", response_model=PleaDecisionOut)
def deny_plea(plea_id: RowId, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ADMIN)
    plea = _get_pending_plea(session, plea_id)
    plea.state = RequestState.DENIED
    plea.decided_at = datetime.now(UTC)
    plea.decided_by = fencer.id
    session.commit()
    return PleaDecisionOut(id=plea.id, state=plea.state)


def _tournament_state(tournament: Tournament) -> Literal["draft", "published", "cancelled"]:
    # cancelled wins: a tournament is cancelled after it was published
    if tournament.cancelled_at is not None:
        return "cancelled"
    return "draft" if tournament.published_at is None else "published"


@router.get("/tournaments", response_model=list[AdminTournamentOut])
def list_tournaments(session: SessionDep, fencer: FencerDep) -> list[AdminTournamentOut]:
    """Every tournament, drafts and cancelled ones included (spec user-roles,
    Admin panel). Counts and credited sums come from one grouped query each
    rather than a query per row (design D4)."""
    require_role(fencer, Role.ADMIN)
    tournaments = session.scalars(select(Tournament).order_by(Tournament.date.desc())).all()
    counts: dict[int, int] = dict(
        session.execute(
            select(Registration.tournament_id, func.count(Registration.id)).group_by(
                Registration.tournament_id
            )
        )
        .tuples()
        .all()
    )
    credited: dict[int, list[AdminCreditedOut]] = {}
    for tournament_id, currency, amount in session.execute(
        select(
            PaymentCredit.tournament_id,
            PaymentCredit.currency,
            func.sum(PaymentCredit.amount_cents),
        )
        .where(PaymentCredit.reversed_at.is_(None))
        .group_by(PaymentCredit.tournament_id, PaymentCredit.currency)
        .order_by(PaymentCredit.currency)
    ).tuples():
        credited.setdefault(tournament_id, []).append(
            AdminCreditedOut(currency=currency, amount_cents=amount)
        )
    owner_ids = {t.owner_id for t in tournaments if t.owner_id is not None}
    owners = {
        owner.id: owner for owner in session.scalars(select(Fencer).where(Fencer.id.in_(owner_ids)))
    }
    rows: list[AdminTournamentOut] = []
    for tournament in tournaments:
        owner = owners.get(tournament.owner_id) if tournament.owner_id is not None else None
        rows.append(
            AdminTournamentOut(
                slug=tournament.slug,
                display_name=tournament.display_name,
                date=tournament.date,
                state=_tournament_state(tournament),
                owner=(
                    AdminTournamentOwnerOut(
                        id=owner.id, display_name=owner.display_name, email=owner.email
                    )
                    if owner is not None
                    else None
                ),
                registration_count=counts.get(tournament.id, 0),
                credited=credited.get(tournament.id, []),
            )
        )
    return rows


@router.delete("/tournaments/{slug}", status_code=204)
def delete_tournament(
    slug: str, session: SessionDep, fencer: FencerDep, confirm: bool = False
) -> None:
    """An Admin's hard delete, in any state and without team membership (spec
    tournament-admin, Tournament deletion and cancellation). Registrations,
    and the money recorded against them, go too — but only on `confirm`, read
    against the count at this moment, so a registration that arrived after the
    list was loaded still stops an unconfirmed delete. Sends no mail."""
    require_role(fencer, Role.ADMIN)
    tournament = session.scalar(select(Tournament).where(Tournament.slug == slug))
    if tournament is None:
        raise HTTPException(status_code=404, detail="tournament_not_found")
    has_registrations = session.scalar(
        select(Registration.id).where(Registration.tournament_id == tournament.id).limit(1)
    )
    if has_registrations is not None and not confirm:
        raise HTTPException(status_code=409, detail="has_registrations")
    tournament_delete.delete_tournament(session, tournament)
    session.commit()
