import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import emails
from app.auth import create_token, hash_password, set_password, verify_password
from app.db import get_session
from app.hr_index import HRIndex, get_hr_index
from app.mail import Mailer, get_mailer
from app.models import Fencer, PasswordReset, PendingSignup, Registration
from app.ratelimit import limiter
from app.routers.accounts import audit_change
from app.schemas import (
    GuestCheckIn,
    LoginIn,
    PasswordResetConfirmIn,
    PasswordResetIn,
    PasswordResetKeyIn,
    PasswordResetOut,
    ResendVerificationIn,
    SignupIn,
    SignupPendingOut,
    TokenOut,
    VerifiedOut,
    VerifyIn,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]

# how long a verification link works (spec fencer-accounts, An account exists
# only once its address is verified)
VERIFICATION_TTL = timedelta(hours=48)
# how long a password-reset link works (spec password-reset)
PASSWORD_RESET_TTL = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(moment: datetime) -> datetime:
    # SQLite hands timestamps back naive; they were written in UTC
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def account_holding(session: Session, email: str) -> Fencer | None:
    """The account an address belongs to: a record holding it *and* credentials.
    A record without credentials holding the address is not an account — a
    signup takes it over, and a guest may be entered on it."""
    return session.scalar(
        select(Fencer).where(Fencer.email == email, Fencer.password_hash.is_not(None))
    )


def _issue_key(pending: PendingSignup) -> str:
    """A fresh verification key for the pending signup, replacing any earlier
    one: only the most recent link mailed works."""
    key = secrets.token_urlsafe(32)
    pending.key_hash = _key_hash(key)
    pending.created_at = _now()
    pending.expires_at = pending.created_at + VERIFICATION_TTL
    return key


@router.post("/signup", response_model=SignupPendingOut, status_code=202)
@limiter.limit("3/minute")
def signup(
    request: Request,
    data: SignupIn,
    session: SessionDep,
    hr: Annotated[HRIndex, Depends(get_hr_index)],
    mailer: MailerDep,
):
    """Record a pending signup and mail its verification link. Nothing exists
    that could be signed into until the link is followed (design
    guest-registration D9)."""
    if account_holding(session, data.email) is not None:
        raise HTTPException(status_code=409, detail="email_already_registered")

    if data.hr_id is not None:
        profile = hr.get(data.hr_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="hr_profile_not_found")
        display_name, nationality = profile.name, profile.nationality
        club = data.club if data.club is not None else profile.club
    else:
        if data.display_name is None:
            raise HTTPException(status_code=422, detail="display_name_required")
        display_name, nationality, club = data.display_name, None, data.club

    # one pending signup per address, the latest winning: an earlier one —
    # mistyped, or somebody else's — must not hold the address against its owner
    pending = session.scalar(select(PendingSignup).where(PendingSignup.email == data.email))
    if pending is None:
        pending = PendingSignup(email=data.email)
        session.add(pending)
    pending.password_hash = hash_password(data.password)
    pending.display_name = display_name
    pending.hr_id = data.hr_id
    pending.nationality = nationality
    pending.club = club
    pending.language = data.language
    pending.return_to = data.return_to
    key = _issue_key(pending)
    session.commit()
    emails.send_signup_verification(mailer, pending, key)
    return SignupPendingOut(email=pending.email)


def _take_over(session: Session, record: Fencer, pending: PendingSignup) -> None:
    """A verified signup on a record without credentials makes that record the
    account (spec fencer-accounts, A fencer record may exist without an
    account). Same record, same registrations; each changed field audited.

    Its HEMA Ratings binding stands where it has one — the binding is
    write-once from the fencer's side, and a takeover is the fencer's side. Its
    guest registrations stop being guests': the holder now signs in, and a link
    in a forwardable mail would grant the same thing to whoever receives the
    forward (spec guest-registration)."""
    record.password_hash = pending.password_hash
    audit_change(session, record, "display_name", pending.display_name)
    audit_change(session, record, "language", pending.language)
    if record.hr_id is None and pending.hr_id is not None:
        audit_change(session, record, "hr_id", pending.hr_id)
        audit_change(session, record, "nationality", pending.nationality)
    if pending.club is not None:
        audit_change(session, record, "club", pending.club)
    session.execute(
        update(Registration)
        .where(Registration.fencer_id == record.id)
        .values(manage_key_generation=None)
    )


@router.post("/verify", response_model=VerifiedOut)
@limiter.limit("10/minute")
def verify(request: Request, data: VerifyIn, session: SessionDep):
    """Follow a verification link: the account comes into existence, or the
    record without credentials on its address becomes it, and the fencer is
    signed in. A link works once and for 48 hours."""
    pending = session.scalar(
        select(PendingSignup).where(PendingSignup.key_hash == _key_hash(data.key))
    )
    if pending is None or _aware(pending.expires_at) <= _now():
        raise HTTPException(status_code=410, detail="verification_invalid")

    record = session.scalar(select(Fencer).where(Fencer.email == pending.email))
    if record is not None and record.password_hash is not None:
        # an account appeared on the address since the signup was recorded —
        # there is nothing left for this link to create
        session.delete(pending)
        session.commit()
        raise HTTPException(status_code=410, detail="verification_invalid")
    if record is not None:
        _take_over(session, record, pending)
        fencer = record
    else:
        fencer = Fencer(
            email=pending.email,
            password_hash=pending.password_hash,
            display_name=pending.display_name,
            hr_id=pending.hr_id,
            nationality=pending.nationality,
            club=pending.club,
            language=pending.language,
        )
        session.add(fencer)
    return_to = pending.return_to
    session.delete(pending)
    session.commit()
    return VerifiedOut(token=create_token(fencer), return_to=return_to)


@router.post("/resend-verification", status_code=204)
@limiter.limit("3/minute")
def resend_verification(
    request: Request, data: ResendVerificationIn, session: SessionDep, mailer: MailerDep
) -> Response:
    """Mail a fresh link for a pending signup. Asks for the password, as
    sign-in does, so the pending state is revealed only to whoever set it."""
    pending = session.scalar(select(PendingSignup).where(PendingSignup.email == data.email))
    if pending is None or not verify_password(data.password, pending.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    key = _issue_key(pending)
    session.commit()
    emails.send_signup_verification(mailer, pending, key)
    return Response(status_code=204)


@router.post("/guest-check", status_code=204)
@limiter.limit("10/minute")
def guest_check(request: Request, data: GuestCheckIn, session: SessionDep) -> Response:
    """Whether an address may register without an account, asked as the guest
    form is completed, so a visitor is not left to fill in a checklist they
    cannot submit (spec guest-registration). It reveals that an address has an
    account, which signup's own refusal already does."""
    if account_holding(session, data.email) is not None:
        raise HTTPException(status_code=409, detail="email_has_account")
    return Response(status_code=204)


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, data: LoginIn, session: SessionDep):
    fencer = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if fencer is not None and fencer.password_hash:
        if verify_password(data.password, fencer.password_hash):
            return TokenOut(token=create_token(fencer))
        raise HTTPException(status_code=401, detail="invalid_credentials")
    pending = session.scalar(select(PendingSignup).where(PendingSignup.email == data.email))
    # a pending signup is named only to whoever knows its password; to anyone
    # else the address reads exactly as one that never signed up
    if pending is not None and verify_password(data.password, pending.password_hash):
        raise HTTPException(status_code=403, detail="email_not_verified")
    raise HTTPException(status_code=401, detail="invalid_credentials")


def _live_reset(session: Session, key: str) -> PasswordReset:
    """The reset a mailed key names, while it still works. A key never issued,
    one replaced by a newer request, one used and one expired are refused alike:
    to the screen they are all a link that no longer works (spec
    password-reset, The reset link sets a new password once)."""
    reset = session.scalar(select(PasswordReset).where(PasswordReset.key_hash == _key_hash(key)))
    if reset is None or _aware(reset.expires_at) <= _now():
        raise HTTPException(status_code=410, detail="reset_invalid")
    return reset


@router.post("/password-reset", response_model=PasswordResetOut, status_code=202)
@limiter.limit("3/minute")
def request_password_reset(
    request: Request, data: PasswordResetIn, session: SessionDep, mailer: MailerDep
):
    """Mail a reset link to an account's address. Nothing about the account
    changes until the link is followed.

    An address with no account is told so rather than answered as if a link
    had gone out (owner decision 2026-10-25): signup's refusal already reveals
    which addresses have accounts, so a uniform answer would hide nothing and
    leave a person waiting for a mail that will not come. That includes a
    record without credentials and a signup still pending — neither is an
    account, and verified signup is what makes either one."""
    fencer = account_holding(session, data.email)
    if fencer is None:
        raise HTTPException(status_code=404, detail="no_account")
    # one row per account, the latest request winning: every earlier link dies
    reset = session.scalar(select(PasswordReset).where(PasswordReset.fencer_id == fencer.id))
    if reset is None:
        reset = PasswordReset(fencer_id=fencer.id)
        session.add(reset)
    key = secrets.token_urlsafe(32)
    reset.key_hash = _key_hash(key)
    reset.created_at = _now()
    reset.expires_at = reset.created_at + PASSWORD_RESET_TTL
    session.commit()
    emails.send_password_reset(mailer, fencer, key)
    return PasswordResetOut(email=data.email)


@router.post("/password-reset/inspect", response_model=PasswordResetOut)
@limiter.limit("10/minute")
def inspect_password_reset(request: Request, data: PasswordResetKeyIn, session: SessionDep):
    """The address a live link resets, consuming nothing (design password-reset
    D6). The reset screen states a dead link before anyone types a password,
    and fills the identifier a password manager files the new password under."""
    reset = _live_reset(session, data.key)
    email = reset.fencer.email
    if email is None:
        # a row is only ever made for an account, and an account holds an address
        raise HTTPException(status_code=410, detail="reset_invalid")
    return PasswordResetOut(email=email)


@router.post("/password-reset/confirm", response_model=TokenOut)
@limiter.limit("10/minute")
def confirm_password_reset(request: Request, data: PasswordResetConfirmIn, session: SessionDep):
    """Set the new password, end every other session and sign this browser in.
    A password too short is refused by validation before the key is looked at,
    so the link stays usable."""
    reset = _live_reset(session, data.key)
    token = set_password(session, reset.fencer, data.password)
    session.delete(reset)
    session.commit()
    return TokenOut(token=token)
