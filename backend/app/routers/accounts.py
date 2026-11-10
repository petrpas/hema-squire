from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import account_deletion, emails, privacy
from app.auth import current_fencer, is_deployment_owner, set_password, verify_password
from app.db import get_session
from app.hr_index import HRIndex, HRProfile, get_hr_index
from app.models import (
    Fencer,
    FencerProfileAudit,
    OrganizerRequest,
    RequestState,
    Tournament,
    TournamentOrganizer,
)
from app.outgoing import QueuedMailerDep
from app.ratelimit import limiter
from app.schemas import (
    AccountExportOut,
    AccountOut,
    AccountUpdate,
    DeletionBlockerOut,
    DeletionCancelledOut,
    DeletionCreditOut,
    DeletionImpactOut,
    DeletionIn,
    HRBindIn,
    PasswordChangeIn,
    PleaIn,
    PleaOut,
    TokenOut,
)

router = APIRouter(tags=["accounts"])

SessionDep = Annotated[Session, Depends(get_session)]
FencerDep = Annotated[Fencer, Depends(current_fencer)]
HRIndexDep = Annotated[HRIndex, Depends(get_hr_index)]


@router.get("/api/hr/search", response_model=list[HRProfile])
def hr_search(q: str, session: SessionDep, hr: HRIndexDep, nationality: str | None = None):
    results = hr.search(q, nationality)
    claimed_ids = set(
        session.scalars(
            select(Fencer.hr_id).where(
                Fencer.hr_id.in_([p.hr_id for p in results]),
                # a deleted record is nobody's account, so it claims nothing
                Fencer.deleted_at.is_(None),
            )
        )
    )
    for profile in results:
        profile.claimed = profile.hr_id in claimed_ids
    return results


@router.get("/api/hr/nationalities", response_model=list[str])
def hr_nationalities(hr: HRIndexDep):
    return hr.nationalities()


def account_out(session: Session, fencer: Fencer) -> AccountOut:
    out = AccountOut.model_validate(fencer)
    out.is_deployment_owner = is_deployment_owner(fencer)
    out.organized_count = _organized_count(session, fencer)
    out.organizer_terms_due = privacy.organizer_terms_due(session, fencer)
    out.deletion_effective_at = account_deletion.effective_on(fencer)
    return out


def _organized_count(session: Session, fencer: Fencer) -> int:
    """Tournaments the account may open the console of — owned or sat on the
    team of, cancelled ones excluded, which is exactly what the picker lists.
    The same pair of conditions as `require_console_access`, asked once for
    the whole set rather than per tournament."""
    organized = select(TournamentOrganizer.tournament_id).where(
        TournamentOrganizer.fencer_id == fencer.id
    )
    return (
        session.scalar(
            select(func.count())
            .select_from(Tournament)
            .where(
                Tournament.cancelled_at.is_(None),
                or_(Tournament.owner_id == fencer.id, Tournament.id.in_(organized)),
            )
        )
        or 0
    )


@router.get("/api/account", response_model=AccountOut)
def my_account(session: SessionDep, fencer: FencerDep):
    return account_out(session, fencer)


@router.post("/api/account/organizer-terms", response_model=AccountOut)
def accept_organizer_terms(session: SessionDep, fencer: FencerDep):
    """Record that the account accepts the current organizer data terms (spec
    `privacy`). Accepting again restamps the moment; nothing else changes."""
    privacy.accept_organizer_terms(fencer)
    session.commit()
    session.refresh(fencer)
    return account_out(session, fencer)


@router.get("/api/account/deletion", response_model=DeletionImpactOut)
def deletion_impact(session: SessionDep, fencer: FencerDep):
    """What deleting the account would do, and what stands in its way."""
    found = account_deletion.impact(session, fencer)
    return DeletionImpactOut(
        cancelled=[
            DeletionCancelledOut(
                tournament=entry.tournament,
                tournament_date=entry.tournament_date,
                variable_symbol=entry.vs,
                credited=[
                    DeletionCreditOut(amount_cents=cents, currency=currency)
                    for cents, currency in entry.credited
                ],
            )
            for entry in found.cancelled
        ],
        held_rosters=found.held_rosters,
        blockers=[
            DeletionBlockerOut(kind=blocker.kind, tournaments=blocker.tournaments)
            for blocker in found.blockers
        ],
    )


@router.post("/api/account/deletion", response_model=AccountOut)
@limiter.limit("5/minute")
def request_deletion(
    request: Request,
    data: DeletionIn,
    session: SessionDep,
    fencer: FencerDep,
    mailer: QueuedMailerDep,
):
    """Ask for the account to be deleted in seven days, confirmed by the
    password (spec `account-deletion`). Rate-limited as a password change is,
    since a session alone would let it be used to guess the password."""
    account_deletion.request_deletion(session, fencer, data.password, mailer)
    session.commit()
    session.refresh(fencer)
    return account_out(session, fencer)


@router.post("/api/account/deletion/withdraw", response_model=AccountOut)
def withdraw_deletion(session: SessionDep, fencer: FencerDep, mailer: QueuedMailerDep):
    account_deletion.withdraw_deletion(fencer, mailer)
    session.commit()
    session.refresh(fencer)
    return account_out(session, fencer)


@router.get("/api/account/export", response_model=AccountExportOut)
def export_my_data(session: SessionDep, fencer: FencerDep):
    """The account's own personal data, as a file it can keep (spec
    `privacy`, An account holder can download their own data)."""
    return privacy.account_export(session, fencer)


def audit_change(session: Session, fencer: Fencer, field: str, new_value: str | int | None) -> None:
    """Set one profile field and record the change. `hr_id` is the one integer
    field; the trail stores every value as text."""
    old_value = getattr(fencer, field)
    if old_value == new_value:
        return
    session.add(
        FencerProfileAudit(
            fencer_id=fencer.id,
            field=field,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
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
    return account_out(session, fencer)


@router.post("/api/account/password", response_model=TokenOut)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: PasswordChangeIn,
    session: SessionDep,
    fencer: FencerDep,
    mailer: QueuedMailerDep,
):
    """Change the password from the Profile page (spec profile-page, Password
    section): the current one is proof, every other session ends, and a notice
    goes to the account's address — anyone at a browser already signed in could
    otherwise change it unseen. Rate-limited as sign-in is, since a session
    alone would let it be used to guess the current password.

    A wrong current password is 403, not 401: the session is fine, and a 401
    would send the browser to sign in again."""
    if fencer.password_hash is None or not verify_password(
        data.current_password, fencer.password_hash
    ):
        raise HTTPException(status_code=403, detail="wrong_password")
    token = set_password(session, fencer, data.new_password)
    session.commit()
    emails.send_password_changed(mailer, fencer)
    return TokenOut(token=token)


def bind_profile(session: Session, fencer: Fencer, profile: HRProfile) -> None:
    """Apply an HR profile to an account: canonical name, HR nationality, club if empty.

    Claims are non-exclusive (design D2): another account may already hold
    this hr_id; that is surfaced as a warning in HR search, not enforced here.
    """
    audit_change(session, fencer, "hr_id", profile.hr_id)
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
    return account_out(session, fencer)


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


@router.post("/api/account/plea/cancel", response_model=PleaOut)
def cancel_plea(session: SessionDep, fencer: FencerDep):
    plea = session.scalar(
        select(OrganizerRequest).where(
            OrganizerRequest.fencer_id == fencer.id,
            OrganizerRequest.state == RequestState.PENDING,
        )
    )
    if plea is None:
        raise HTTPException(status_code=409, detail="plea_not_pending")
    plea.state = RequestState.CANCELLED
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
