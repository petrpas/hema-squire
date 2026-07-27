import io
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app import setup, taxonomy
from app.auth import (
    current_fencer,
    require_console_access,
    require_role,
    require_tournament_owner,
)
from app.availability import queue_length, taken_seats
from app.db import get_session
from app.models import (
    BankTransaction,
    Discipline,
    ExtraItem,
    Fencer,
    HRRatingSnapshot,
    HRSnapshotRating,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    PaymentEvent,
    Registration,
    RegistrationState,
    Role,
    Rule,
    RuleJournalEntry,
    Tournament,
    TournamentOrganizer,
)
from app.schemas import (
    AdminOwnerAssignIn,
    DisciplineIn,
    DisciplineOut,
    ExtraItemIn,
    ExtraItemOut,
    OpenDisciplineOut,
    OpenTournamentOut,
    OwnerTransferIn,
    PastTournamentOut,
    TeamAdd,
    TeamMemberOut,
    TournamentCreate,
    TournamentOut,
    TournamentUpdate,
)

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])

SessionDep = Annotated[Session, Depends(get_session)]
FencerDep = Annotated[Fencer, Depends(current_fencer)]


def get_tournament(session: SessionDep, slug: str) -> Tournament:
    tournament = session.scalar(
        select(Tournament)
        .where(Tournament.slug == slug)
        .options(
            selectinload(Tournament.disciplines), selectinload(Tournament.extra_items)
        )
    )
    if tournament is None:
        raise HTTPException(status_code=404, detail="tournament_not_found")
    return tournament


TournamentDep = Annotated[Tournament, Depends(get_tournament)]


@router.post("", response_model=TournamentOut, status_code=201)
def create_tournament(data: TournamentCreate, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ORGANIZER)
    if session.scalar(select(Tournament.id).where(Tournament.slug == data.slug)):
        raise HTTPException(status_code=409, detail="slug_taken")
    # the creator becomes the Tournament Owner; ownership implies console
    # access, so no team row is added
    tournament = Tournament(**data.model_dump(), owner=fencer)
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


@router.get("", response_model=list[TournamentOut])
def list_tournaments(session: SessionDep):
    # cancelled tournaments are retired: hidden from public listings, but
    # their detail/console stay reachable by slug (design D5)
    return session.scalars(
        select(Tournament)
        .where(Tournament.cancelled_at.is_(None))
        .options(
            selectinload(Tournament.disciplines), selectinload(Tournament.extra_items)
        )
        .order_by(Tournament.date)
    ).all()


@router.get("/open", response_model=list[OpenTournamentOut])
def open_tournaments(session: SessionDep, fencer: FencerDep):
    """Published, non-cancelled, upcoming tournaments for the fencer-facing
    home list (design D1) — a trimmed DTO so drafts and organizer-only
    config never leak, with per-discipline counts and the caller's own
    registration state folded in to avoid N+1 calls from the frontend."""
    today = datetime.now(UTC).date()
    rows = session.scalars(
        select(Tournament)
        .where(Tournament.cancelled_at.is_(None), Tournament.date >= today)
        .options(selectinload(Tournament.disciplines))
        .order_by(Tournament.date)
    ).all()

    result = []
    for tournament in rows:
        if setup.setup_missing(tournament):
            continue

        reason = setup.registration_availability(tournament, today)
        if reason == setup.NOT_YET_OPEN:
            status_, opens_on = "opens_on", tournament.registration_opens
        elif reason == setup.CLOSED:
            status_, opens_on = "closed", None
        else:
            status_, opens_on = "open", None

        disciplines = [
            OpenDisciplineOut(
                code=d.code,
                name=d.name,
                fee=d.fee,
                taken=taken_seats(session, d),
                capacity=d.capacity,
                queue_length=queue_length(session, d),
            )
            for d in tournament.disciplines
        ]

        registration = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id,
                Registration.fencer_id == fencer.id,
            )
        )
        my_state = "none"
        if registration is not None:
            if registration.state == RegistrationState.PAID:
                my_state = "paid"
            elif registration.state == RegistrationState.RESERVED:
                active = any(not e.is_substitute for e in registration.entries)
                my_state = "reserved" if active else "substitute"
            else:  # CANCELLED, or a scheduler-expired reservation
                my_state = "cancelled"

        result.append(
            OpenTournamentOut(
                slug=tournament.slug,
                display_name=tournament.display_name,
                subtitle=tournament.subtitle,
                has_logo=tournament.has_logo,
                date=tournament.date,
                location=tournament.location,
                organizer_names=tournament.organizer_names,
                registration_status=status_,
                registration_opens_on=opens_on,
                disciplines=disciplines,
                my_registration_state=my_state,
            )
        )
    return result


@router.get("/mine/past", response_model=list[PastTournamentOut])
def past_tournaments(session: SessionDep, fencer: FencerDep):
    """Personal history for the Past tab (design D1): non-cancelled tournaments
    before today where the caller held a non-cancelled registration or
    organized (owner or team member), newest first. Declared ahead of
    `/{slug}` so "mine" is never captured as a slug."""
    today = datetime.now(UTC).date()

    organizer_tournament_ids = set(
        session.scalars(
            select(TournamentOrganizer.tournament_id).where(
                TournamentOrganizer.fencer_id == fencer.id
            )
        ).all()
    )
    participated_tournament_ids = set(
        session.scalars(
            select(Registration.tournament_id).where(
                Registration.fencer_id == fencer.id,
                Registration.state.in_(
                    [RegistrationState.PAID, RegistrationState.RESERVED]
                ),
            )
        ).all()
    )

    rows = session.scalars(
        select(Tournament)
        .where(Tournament.cancelled_at.is_(None), Tournament.date < today)
        .options(selectinload(Tournament.disciplines))
        .order_by(Tournament.date.desc())
    ).all()

    result = []
    for tournament in rows:
        if setup.setup_missing(tournament):
            continue

        organized = tournament.owner_id == fencer.id or tournament.id in organizer_tournament_ids
        participated = tournament.id in participated_tournament_ids
        if not organized and not participated:
            continue

        disciplines = [
            OpenDisciplineOut(
                code=d.code,
                name=d.name,
                fee=d.fee,
                taken=taken_seats(session, d),
                capacity=d.capacity,
                queue_length=queue_length(session, d),
            )
            for d in tournament.disciplines
        ]

        my_state = "none"
        if participated:
            registration = session.scalar(
                select(Registration).where(
                    Registration.tournament_id == tournament.id,
                    Registration.fencer_id == fencer.id,
                )
            )
            if registration.state == RegistrationState.PAID:
                my_state = "paid"
            elif registration.state == RegistrationState.RESERVED:
                active = any(not e.is_substitute for e in registration.entries)
                my_state = "reserved" if active else "substitute"

        result.append(
            PastTournamentOut(
                slug=tournament.slug,
                display_name=tournament.display_name,
                subtitle=tournament.subtitle,
                has_logo=tournament.has_logo,
                date=tournament.date,
                location=tournament.location,
                organizer_names=tournament.organizer_names,
                registration_status="closed",
                registration_opens_on=None,
                disciplines=disciplines,
                my_registration_state=my_state,
                organized=organized,
            )
        )
    return result


@router.get("/{slug}", response_model=TournamentOut)
def tournament_detail(tournament: TournamentDep):
    out = TournamentOut.model_validate(tournament)
    out.setup_missing = setup.setup_missing(tournament)
    return out


@router.patch("/{slug}", response_model=TournamentOut)
def update_tournament(
    data: TournamentUpdate, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tournament, field, value)
    session.commit()
    session.refresh(tournament)
    return tournament


# logo upload bounds: reject oversized inputs, then re-encode to a bounded PNG
# so the stored blob stays small (design D1)
LOGO_MAX_UPLOAD_BYTES = 512 * 1024
LOGO_MAX_DIMENSION = 512


@router.post("/{slug}/logo", response_model=TournamentOut)
async def upload_logo(
    tournament: TournamentDep, file: UploadFile, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    raw = await file.read()
    if len(raw) > LOGO_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="logo_too_large")
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="logo_not_an_image")
    image = image.convert("RGBA")
    # downscale in place so the longest side is at most LOGO_MAX_DIMENSION
    image.thumbnail((LOGO_MAX_DIMENSION, LOGO_MAX_DIMENSION))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    tournament.logo_bytes = buffer.getvalue()
    tournament.logo_mime = "image/png"
    session.commit()
    session.refresh(tournament)
    out = TournamentOut.model_validate(tournament)
    out.setup_missing = setup.setup_missing(tournament)
    return out


@router.delete("/{slug}/logo", status_code=204)
def delete_logo(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    tournament.logo_bytes = None
    tournament.logo_mime = None
    session.commit()


@router.get("/{slug}/logo")
def get_logo(tournament: TournamentDep):
    # public so plain <img src> tags (which cannot send the auth header) can
    # display it; a tournament logo is public-facing information
    if tournament.logo_mime is None or tournament.logo_bytes is None:
        raise HTTPException(status_code=404, detail="no_logo")
    return Response(content=tournament.logo_bytes, media_type=tournament.logo_mime)


@router.post("/{slug}/disciplines", response_model=DisciplineOut, status_code=201)
def add_discipline(
    data: DisciplineIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    if not taxonomy.is_valid_code(data.code):
        raise HTTPException(status_code=422, detail="unknown_discipline_code")
    if any(d.code == data.code for d in tournament.disciplines):
        raise HTTPException(status_code=409, detail="discipline_exists")
    discipline = Discipline(
        tournament=tournament,
        code=data.code,
        name=data.name or taxonomy.default_name(data.code),
        capacity=data.capacity,
        fee=data.fee,
        fee_early=data.fee_early,
        schedule_when=data.schedule_when,
        schedule_where=data.schedule_where,
        ruleset_name=data.ruleset_name,
        ruleset_url=data.ruleset_url,
    )
    session.add(discipline)
    session.commit()
    session.refresh(discipline)
    return discipline


@router.patch("/{slug}/disciplines/{code}", response_model=DisciplineOut)
def update_discipline(
    code: str,
    data: DisciplineIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    discipline = next((d for d in tournament.disciplines if d.code == code), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    if data.code != code:
        raise HTTPException(status_code=422, detail="code_is_immutable")
    discipline.name = data.name or discipline.name
    discipline.capacity = data.capacity
    discipline.fee = data.fee
    discipline.fee_early = data.fee_early
    discipline.schedule_when = data.schedule_when
    discipline.schedule_where = data.schedule_where
    discipline.ruleset_name = data.ruleset_name
    discipline.ruleset_url = data.ruleset_url
    session.commit()
    session.refresh(discipline)
    return discipline


@router.delete("/{slug}/disciplines/{code}", status_code=204)
def delete_discipline(
    code: str, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    discipline = next((d for d in tournament.disciplines if d.code == code), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    session.delete(discipline)
    session.commit()


@router.post("/{slug}/extra-items", response_model=ExtraItemOut, status_code=201)
def add_extra_item(
    data: ExtraItemIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    item = ExtraItem(tournament=tournament, **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.patch("/{slug}/extra-items/{item_id}", response_model=ExtraItemOut)
def update_extra_item(
    item_id: int,
    data: ExtraItemIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    item = next((i for i in tournament.extra_items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="extra_item_not_found")
    item.name = data.name
    item.category = data.category
    item.price = data.price
    item.max_qty = data.max_qty
    item.schedule_when = data.schedule_when
    item.schedule_where = data.schedule_where
    item.remark = data.remark
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{slug}/extra-items/{item_id}", status_code=204)
def delete_extra_item(
    item_id: int, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    item = next((i for i in tournament.extra_items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="extra_item_not_found")
    session.delete(item)
    session.commit()


@router.get("/{slug}/team", response_model=list[TeamMemberOut])
def list_team(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_tournament_owner(tournament, fencer)
    rows = session.scalars(
        select(TournamentOrganizer)
        .where(TournamentOrganizer.tournament_id == tournament.id)
        .options(selectinload(TournamentOrganizer.fencer))
    ).all()
    return [
        TeamMemberOut(
            fencer_id=row.fencer_id, email=row.fencer.email, display_name=row.fencer.display_name
        )
        for row in rows
    ]


@router.post("/{slug}/team", response_model=TeamMemberOut, status_code=201)
def add_team_member(
    data: TeamAdd, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_tournament_owner(tournament, fencer)
    new_member = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if new_member is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    already = session.scalar(
        select(TournamentOrganizer.id).where(
            TournamentOrganizer.tournament_id == tournament.id,
            TournamentOrganizer.fencer_id == new_member.id,
        )
    )
    if already:
        raise HTTPException(status_code=409, detail="already_organizer")
    session.add(TournamentOrganizer(tournament=tournament, fencer=new_member))
    session.commit()
    return TeamMemberOut(
        fencer_id=new_member.id, email=new_member.email, display_name=new_member.display_name
    )


@router.delete("/{slug}/team/{fencer_id}", status_code=204)
def remove_team_member(
    fencer_id: int, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_tournament_owner(tournament, fencer)
    row = session.scalar(
        select(TournamentOrganizer).where(
            TournamentOrganizer.tournament_id == tournament.id,
            TournamentOrganizer.fencer_id == fencer_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="not_a_team_member")
    session.delete(row)
    session.commit()


@router.post("/{slug}/transfer-ownership", response_model=TournamentOut)
def transfer_ownership(
    data: OwnerTransferIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    """Owner-initiated handover to an existing team member; the previous
    owner joins the team so they keep access (design D3)."""
    require_tournament_owner(tournament, fencer)
    target = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if target is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    membership = session.scalar(
        select(TournamentOrganizer).where(
            TournamentOrganizer.tournament_id == tournament.id,
            TournamentOrganizer.fencer_id == target.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=409, detail="not_a_team_member")
    previous_owner_id = tournament.owner_id
    session.delete(membership)
    tournament.owner_id = target.id
    if previous_owner_id is not None:
        session.add(TournamentOrganizer(tournament_id=tournament.id, fencer_id=previous_owner_id))
    session.commit()
    session.refresh(tournament)
    return tournament


@router.post("/{slug}/assign-owner", response_model=TournamentOut)
def assign_owner(
    data: AdminOwnerAssignIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    """Global-Admin fallback: assign/reassign a tournament's owner outright —
    for a departed owner or a NULL owner left by the migration backfill."""
    require_role(fencer, Role.ADMIN)
    target = session.scalar(select(Fencer).where(Fencer.email == data.email))
    if target is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    tournament.owner_id = target.id
    session.commit()
    session.refresh(tournament)
    return tournament


@router.post("/{slug}/cancel", response_model=TournamentOut)
def cancel_tournament(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Retire a tournament with history: hidden from public listings,
    registration gate rejects (closed), console and data remain (design D5)."""
    require_tournament_owner(tournament, fencer)
    tournament.cancelled_at = datetime.now(UTC)
    session.commit()
    session.refresh(tournament)
    return tournament


def _cascade_delete(session: Session, tournament: Tournament) -> None:
    """Remove every child row of a tournament with zero registrations.
    SQLite has no ON DELETE CASCADE here, so children are deleted explicitly,
    in dependency order, before the tournament itself."""
    tid = tournament.id
    snapshot_ids = select(HRRatingSnapshot.id).where(HRRatingSnapshot.tournament_id == tid)
    session.execute(delete(HRSnapshotRating).where(HRSnapshotRating.snapshot_id.in_(snapshot_ids)))
    session.execute(delete(HRRatingSnapshot).where(HRRatingSnapshot.tournament_id == tid))
    batch_ids = select(ImportBatch.id).where(ImportBatch.tournament_id == tid)
    session.execute(delete(ImportedRow).where(ImportedRow.batch_id.in_(batch_ids)))
    session.execute(delete(ImportDecision).where(ImportDecision.tournament_id == tid))
    session.execute(delete(ImportBatch).where(ImportBatch.tournament_id == tid))
    session.execute(delete(PaymentEvent).where(PaymentEvent.tournament_id == tid))
    session.execute(delete(BankTransaction).where(BankTransaction.tournament_id == tid))
    session.execute(delete(RuleJournalEntry).where(RuleJournalEntry.tournament_id == tid))
    session.execute(delete(Rule).where(Rule.tournament_id == tid))
    session.execute(delete(TournamentOrganizer).where(TournamentOrganizer.tournament_id == tid))
    session.execute(delete(ExtraItem).where(ExtraItem.tournament_id == tid))
    session.execute(delete(Discipline).where(Discipline.tournament_id == tid))
    session.delete(tournament)


@router.delete("/{slug}", status_code=204)
def delete_tournament(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Hard delete only while empty (design D5); once registrations exist the
    owner must cancel instead — financial history is never deletable."""
    require_tournament_owner(tournament, fencer)
    has_registrations = session.scalar(
        select(Registration.id).where(Registration.tournament_id == tournament.id)
    )
    if has_registrations:
        raise HTTPException(status_code=409, detail="has_registrations")
    _cascade_delete(session, tournament)
    session.commit()
