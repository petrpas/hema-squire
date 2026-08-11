import io
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app import money_bounds, scheduler, setup, taxonomy
from app.auth import (
    current_fencer,
    require_console_access,
    require_role,
    require_tournament_owner,
)
from app.availability import (
    queue_length,
    taken_seats,
    taken_team_slots,
    team_queue_length,
)
from app.db import get_session
from app.errors import FieldValidationError
from app.models import (
    ACTION_CATEGORIES,
    BankTransaction,
    Currency,
    Discipline,
    DisciplineKind,
    ExtraItem,
    Fencer,
    HRRatingSnapshot,
    HRSnapshotRating,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    PaymentEvent,
    PaymentMode,
    Registration,
    RegistrationDiscipline,
    RegistrationState,
    Role,
    Rule,
    RuleJournalEntry,
    Team,
    Tournament,
    TournamentOrganizer,
)
from app.schemas import (
    AdminOwnerAssignIn,
    ConsoleTeamDisciplineOut,
    ConsoleTeamOut,
    DisciplineIn,
    DisciplineOut,
    ExtraItemIn,
    ExtraItemOut,
    OpenDisciplineOut,
    OpenTournamentOut,
    OwnerTransferIn,
    QueueDisciplineOut,
    QueueEntryOut,
    QueueOut,
    SettleSeatingOut,
    TeamAdd,
    TeamMemberOut,
    TournamentCreate,
    TournamentModeIn,
    TournamentModeOut,
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


def _lowest_free_series(session: Session, year: int) -> int:
    """The lowest 1..99 not already taken by another tournament in `year`
    (design Decision 2); a year needing a hundredth is refused outright."""
    taken = set(
        session.scalars(
            select(Tournament.vs_series).where(Tournament.vs_year == year)
        ).all()
    )
    for series in range(1, 100):
        if series not in taken:
            return series
    raise HTTPException(status_code=422, detail=f"vs_series_exhausted_for_year_{year}")


def _has_registrations(session: Session, tournament: Tournament) -> bool:
    return (
        session.scalar(
            select(Registration.id)
            .where(Registration.tournament_id == tournament.id)
            .limit(1)
        )
        is not None
    )


@router.post("", response_model=TournamentOut, status_code=201)
def create_tournament(data: TournamentCreate, session: SessionDep, fencer: FencerDep):
    require_role(fencer, Role.ORGANIZER)
    if session.scalar(select(Tournament.id).where(Tournament.slug == data.slug)):
        raise HTTPException(status_code=409, detail="slug_taken")
    # the VS year comes from the tournament date, not today (design Decision 1)
    vs_year = data.date.year
    # the creator becomes the Tournament Owner; ownership implies console
    # access, so no team row is added
    tournament = Tournament(
        **data.model_dump(),
        owner=fencer,
        vs_year=vs_year,
        vs_series=_lowest_free_series(session, vs_year),
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _open_discipline_out(session: Session, discipline: Discipline) -> OpenDisciplineOut:
    """Fencer-facing counts for one discipline. A team discipline counts teams,
    an individual one counts fencers (team-disciplines D1/2.6) — the counting
    pairs are mutually exclusive by kind and assert on the wrong kind, so the
    dispatch cannot be skipped."""
    if discipline.kind == DisciplineKind.TEAM:
        taken = taken_team_slots(session, discipline)
        queued = team_queue_length(session, discipline)
    else:
        taken = taken_seats(session, discipline)
        queued = queue_length(session, discipline)
    return OpenDisciplineOut(
        slug=discipline.slug,
        name=discipline.name,
        fee=discipline.fee,
        fee_eur=discipline.fee_eur,
        taken=taken,
        capacity=discipline.capacity,
        queue_length=queued,
    )


@router.get("", response_model=list[TournamentOut])
def list_tournaments(session: SessionDep):
    # cancelled tournaments are retired: hidden from public listings, but
    # their detail/console stay reachable by slug (design D5)
    tournaments = session.scalars(
        select(Tournament)
        .where(Tournament.cancelled_at.is_(None))
        .options(
            selectinload(Tournament.disciplines), selectinload(Tournament.extra_items)
        )
        .order_by(Tournament.date)
    ).all()
    outs = [TournamentOut.model_validate(tournament) for tournament in tournaments]
    for tournament, out in zip(tournaments, outs, strict=True):
        _apply_disciplines_frozen(session, tournament, out)
    return outs


def _my_registration_state(session: Session, tournament: Tournament, fencer: Fencer) -> str:
    """The caller's own standing on one tournament, as the fencer-facing lists
    report it. A reservation holding nothing but substitute entries reads as
    `substitute`; a cancelled or scheduler-expired one reads as `cancelled`."""
    registration = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == fencer.id,
        )
    )
    if registration is None:
        return "none"
    if registration.state == RegistrationState.PAID:
        return "paid"
    if registration.state == RegistrationState.RESERVED:
        active = any(not e.is_substitute for e in registration.entries)
        return "reserved" if active else "substitute"
    return "cancelled"


def _fencer_tournament_out(
    session: Session, tournament: Tournament, fencer: Fencer, *, organized: bool
) -> OpenTournamentOut:
    """One entry of a fencer-facing list. The three scopes (upcoming, held,
    own) share this body so their payloads cannot drift apart — a trimmed DTO
    so drafts and organizer-only config never leak, with per-discipline counts
    and the caller's own bonds folded in to avoid N+1 calls from the
    frontend."""
    today = datetime.now(UTC).date()
    reason = setup.registration_availability(tournament, today)
    if reason == setup.NOT_YET_OPEN:
        status_, opens_on = "opens_on", tournament.registration_opens
    elif reason == setup.CLOSED:
        status_, opens_on = "closed", None
    else:
        status_, opens_on = "open", None

    return OpenTournamentOut(
        slug=tournament.slug,
        display_name=tournament.display_name,
        subtitle=tournament.subtitle,
        has_logo=tournament.has_logo,
        date=tournament.date,
        location=tournament.location,
        description=tournament.description,
        qualification_open=tournament.qualification_open,
        qualification_criteria=tournament.qualification_criteria,
        local_currency=tournament.local_currency,
        organizers=tournament.organizers,
        registration_status=status_,
        registration_opens_on=opens_on,
        disciplines=[_open_discipline_out(session, d) for d in tournament.disciplines],
        my_registration_state=_my_registration_state(session, tournament, fencer),
        organized=organized,
    )


def _published_tournaments(session: Session, *, upcoming: bool | None) -> list[Tournament]:
    """Published, non-cancelled tournaments. `upcoming` True keeps those dated
    today or later (ascending), False those before today (descending), None
    every one of them (descending)."""
    today = datetime.now(UTC).date()
    conditions = [Tournament.cancelled_at.is_(None), Tournament.published_at.is_not(None)]
    if upcoming is True:
        conditions.append(Tournament.date >= today)
    elif upcoming is False:
        conditions.append(Tournament.date < today)
    order = Tournament.date if upcoming is True else Tournament.date.desc()
    return list(
        session.scalars(
            select(Tournament)
            .where(*conditions)
            .options(selectinload(Tournament.disciplines))
            .order_by(order)
        ).all()
    )


def _organized_tournament_ids(session: Session, fencer: Fencer) -> set[int]:
    """Tournaments the caller sits on the console team of. Ownership is held on
    the tournament itself and is checked alongside this set, never in it."""
    return set(
        session.scalars(
            select(TournamentOrganizer.tournament_id).where(
                TournamentOrganizer.fencer_id == fencer.id
            )
        ).all()
    )


@router.get("/open", response_model=list[OpenTournamentOut])
def open_tournaments(session: SessionDep, fencer: FencerDep):
    """Upcoming scope of the fencer-facing list: published, non-cancelled
    tournaments dated today or later, soonest first."""
    organizer_ids = _organized_tournament_ids(session, fencer)
    return [
        _fencer_tournament_out(
            session,
            tournament,
            fencer,
            organized=tournament.owner_id == fencer.id or tournament.id in organizer_ids,
        )
        for tournament in _published_tournaments(session, upcoming=True)
    ]


@router.get("/held", response_model=list[OpenTournamentOut])
def held_tournaments(session: SessionDep, fencer: FencerDep):
    """Held scope: every published, non-cancelled tournament dated before
    today, newest first, listed for every account whether or not it was
    involved — the Past tab is a public archive, not a personal history."""
    organizer_ids = _organized_tournament_ids(session, fencer)
    return [
        _fencer_tournament_out(
            session,
            tournament,
            fencer,
            organized=tournament.owner_id == fencer.id or tournament.id in organizer_ids,
        )
        for tournament in _published_tournaments(session, upcoming=False)
    ]


@router.get("/mine", response_model=list[OpenTournamentOut])
def my_tournaments(session: SessionDep, fencer: FencerDep):
    """Own scope: tournaments in either direction of today that the caller is
    bound to — holding or having held a registration in any state, cancelled
    included, or organizing it as owner or console team member. Newest first.
    Declared ahead of `/{slug}` so "mine" is never captured as a slug."""
    organizer_ids = _organized_tournament_ids(session, fencer)
    registered_ids = set(
        session.scalars(
            select(Registration.tournament_id).where(Registration.fencer_id == fencer.id)
        ).all()
    )

    result = []
    for tournament in _published_tournaments(session, upcoming=None):
        organized = tournament.owner_id == fencer.id or tournament.id in organizer_ids
        if not organized and tournament.id not in registered_ids:
            continue
        result.append(
            _fencer_tournament_out(session, tournament, fencer, organized=organized)
        )
    return result


@router.get("/{slug}", response_model=TournamentOut)
def tournament_detail(tournament: TournamentDep, session: SessionDep):
    out = TournamentOut.model_validate(tournament)
    out.setup_missing = setup.setup_missing(tournament)
    out.vs_series_editable = not _has_registrations(session, tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


def _apply_currency_invariants(tournament: Tournament) -> None:
    """Reconcile the currency fields after a patch has been merged, so the
    stored combination is always one of the three meaningful modes (design
    Decision 2). Runs on the merged state rather than the payload because
    enabling EUR payments in one request and switching local_currency in
    another must still be caught.

    eur_rate is a Setup convenience only and is never required to enable EUR
    (design Decision 3) — pydantic already rejects a non-positive one.
    A tournament still pricing through the legacy fixed weapon-rental/
    afterparty parameters cannot enable EUR, because those parameters carry
    no EUR column (design Decision 9)."""
    if tournament.local_currency == Currency.EUR:
        # an EUR-priced tournament's local figure already is the EUR one
        if setup.uses_legacy_fixed_fees(tournament):
            raise HTTPException(status_code=422, detail="legacy_fixed_fees_block_eur")
        tournament.eur_payments_enabled = True
        tournament.eur_rate = None
        return
    if not tournament.eur_payments_enabled:
        tournament.eur_rate = None
        return
    if setup.uses_legacy_fixed_fees(tournament):
        raise HTTPException(status_code=422, detail="legacy_fixed_fees_block_eur")


@router.patch("/{slug}", response_model=TournamentOut)
def update_tournament(
    data: TournamentUpdate, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    updates = data.model_dump(exclude_unset=True)
    requested_series = updates.pop("vs_series", None)
    has_registrations = _has_registrations(session, tournament)
    # the series is frozen from the first registration on: no explicit change,
    # and a date change never renumbers it (design Decision 2)
    if requested_series is not None:
        if has_registrations:
            raise HTTPException(status_code=409, detail="vs_series_frozen")
        if requested_series != tournament.vs_series:
            collision = session.scalar(
                select(Tournament.id).where(
                    Tournament.vs_year == tournament.vs_year,
                    Tournament.vs_series == requested_series,
                    Tournament.id != tournament.id,
                )
            )
            if collision is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"vs_series_taken: year {tournament.vs_year} series {requested_series}",
                )
            tournament.vs_series = requested_series
    elif not has_registrations and "date" in updates:
        new_year = updates["date"].year
        if new_year != tournament.vs_year:
            tournament.vs_year = new_year
            tournament.vs_series = _lowest_free_series(session, new_year)

    for field, value in updates.items():
        setattr(tournament, field, value)
    # reopening clears any previously recorded criteria (design D7)
    if updates.get("qualification_open") is True:
        tournament.qualification_criteria = None
    if not tournament.qualification_open and not (tournament.qualification_criteria or "").strip():
        raise HTTPException(status_code=422, detail="qualification_criteria_required")
    if (
        tournament.amendments_close is not None
        and tournament.registration_closes is not None
        and tournament.amendments_close > tournament.registration_closes
    ):
        # a later value would never be reached (registration itself closes first)
        raise HTTPException(status_code=422, detail="amendments_close_after_registration_closes")
    if (
        tournament.team_composition_deadline is not None
        and tournament.team_composition_deadline > tournament.date
    ):
        # deliberately no ordering constraint against registration_closes or
        # amendments_close in either direction (design team-disciplines D7) —
        # only the tournament date bounds it, since a deadline after the event
        # could never be meaningfully checked
        raise HTTPException(status_code=422, detail="composition_deadline_after_tournament_date")
    if tournament.seating_deadline is not None:
        # the seating deadline is a soft boundary *inside* the hard close: one
        # set later than registration_closes could never be reached, and the
        # two are easy to conflate (design Risks), so the message names both
        closes = tournament.registration_closes or tournament.date
        if tournament.seating_deadline > closes:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"seating_deadline_after_registration_closes: "
                    f"seating_deadline={tournament.seating_deadline} "
                    f"registration_closes={closes}"
                ),
            )
    if tournament.payment_mode == PaymentMode.DEPOSIT:
        # a deposit mode with no deposit holds seats with nothing while
        # claiming to hold them with money. The EUR figure is required
        # alongside it on the same terms as every other price — independent,
        # never derived (design D4)
        if not tournament.deposit_amount:
            raise HTTPException(status_code=422, detail="deposit_amount_required")
        if tournament.shows_eur and not tournament.deposit_amount_eur:
            raise HTTPException(status_code=422, detail="deposit_amount_eur_required")
    if updates.get("hr_category_map") is not None:
        team_codes = {
            d.taxonomy_code for d in tournament.disciplines if d.kind == DisciplineKind.TEAM
        }
        offending = team_codes & set(tournament.hr_category_map)
        if offending:
            # team disciplines carry no HR rating category (design
            # team-disciplines: "Team disciplines carry no HR rating category")
            raise HTTPException(status_code=422, detail="hr_category_map_excludes_team_disciplines")
    if tournament.reminder_day >= tournament.reservation_validity_days:
        # expiry runs before reminders (scheduler.run_tournament_tick): a
        # reservation would always be expired before its reminder was due,
        # and no reminder would ever be sent (design harden-payment-matching
        # Decision 8) — checked on every edit, whichever field changed
        raise HTTPException(
            status_code=422,
            detail=(
                f"reminder_day_not_before_validity: reminder_day={tournament.reminder_day} "
                f"reservation_validity_days={tournament.reservation_validity_days}"
            ),
        )
    _apply_currency_invariants(tournament)
    # local-currency money: ceiling resolved from the currency now in effect
    # (design 2.4a); checked only for fields this request actually touches —
    # an untouched stored value is never re-validated (design Risks)
    money_fields = {
        field: updates[field]
        for field in (
            "weapon_rental_fee",
            "weapon_rental_fee_early",
            "afterparty_fee",
            "afterparty_fee_early",
            "deposit_amount",
        )
        if field in updates
    }
    money_errors = money_bounds.collect_local_money_errors(tournament, money_fields)
    if "discounts" in updates:
        for index, discount in enumerate(updates["discounts"] or []):
            effect = discount.get("effect") or {}
            if effect.get("kind") == "fixed":
                error = money_bounds.local_money_error(
                    tournament, f"discounts.{index}.effect.value", effect.get("value")
                )
                if error:
                    money_errors.append(error)
    if money_errors:
        raise FieldValidationError(money_errors)
    setup.guard_published_completeness(tournament)
    session.commit()
    session.refresh(tournament)
    out = TournamentOut.model_validate(tournament)
    out.vs_series_editable = not _has_registrations(session, tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


@router.get("/{slug}/mode", response_model=TournamentModeOut)
def tournament_mode(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    require_console_access(session, tournament, fencer)
    return tournament


@router.patch("/{slug}/mode", response_model=TournamentOut)
def set_tournament_mode(
    data: TournamentModeIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    """Choose the tournament's mode. Writes the four features and nothing else:
    a feature turned off hides its settings and never clears, resets or deletes
    one (design tournament-modes D4), which is what makes the mode safe to
    experiment with.

    Completeness is deliberately not guarded here. Turning payments on for a
    published, priced tournament with no account recorded is accepted, and the
    account is then reported as missing on PUBLISH — the mode is how the
    organizer reaches the field that fixes it, so refusing the change would
    leave them nowhere to go."""
    require_console_access(session, tournament, fencer)
    tournament.feature_schedule = data.feature_schedule
    tournament.feature_payments = data.feature_payments
    tournament.feature_teams = data.feature_teams
    tournament.feature_extras = data.feature_extras
    session.commit()
    session.refresh(tournament)
    out = TournamentOut.model_validate(tournament)
    out.setup_missing = setup.setup_missing(tournament)
    out.vs_series_editable = not _has_registrations(session, tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


logger = logging.getLogger(__name__)

# logo upload bounds: reject oversized inputs, then re-encode to a bounded PNG
# so the stored blob stays small (design D1). The cap only needs to bound
# decode work since every accepted image is re-encoded to LOGO_MAX_DIMENSION.
LOGO_MAX_UPLOAD_BYTES = 8 * 1024 * 1024
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
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        logger.warning("logo upload could not be decoded as an image", exc_info=exc)
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
    _apply_disciplines_frozen(session, tournament, out)
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


def generate_slug(
    tournament: Tournament, kind: DisciplineKind, weapon: str, gender: str, material: str
) -> str:
    """The taxonomy code, `Team-`-prefixed for a team discipline so it is
    distinguishable from its individual counterpart, normalized, and
    disambiguated against the tournament's existing slugs with a `-2`, `-3`,
    ... suffix (design discipline-identity-modal D5, discipline-identity D3)."""
    base = taxonomy.normalize_slug(taxonomy.taxonomy_code(weapon, gender, material)) or "Discipline"
    if kind == DisciplineKind.TEAM:
        base = f"Team-{base}"
    existing = {d.slug for d in tournament.disciplines}
    if base not in existing:
        return base
    counter = 2
    while f"{base}-{counter}" in existing:
        counter += 1
    return f"{base}-{counter}"


@router.post("/{slug}/disciplines", response_model=DisciplineOut, status_code=201)
def add_discipline(
    data: DisciplineIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    money_errors = money_bounds.collect_local_money_errors(
        tournament, {"fee": data.fee, "fee_early": data.fee_early}
    )
    if money_errors:
        raise FieldValidationError(money_errors)
    if data.gender not in ("", "W", "M") or data.material not in ("", "Plastic"):
        # already enforced by the schema's Literal types; kept as a guard
        # since the closed sets are the domain invariant, not the schema
        raise HTTPException(status_code=422, detail="invalid_classification")
    name = data.name
    is_team = data.kind == DisciplineKind.TEAM
    if not taxonomy.is_taxonomy_weapon(data.weapon):
        if not name:
            raise HTTPException(status_code=422, detail="discipline_name_required")
    else:
        name = name or taxonomy.discipline_name(data.weapon, data.gender, data.material, is_team)
    if data.slug is None:
        # the schema's own BeforeValidator already normalized an override, and
        # maps an empty result to None (design D6, task 8a.1) — this branch is
        # therefore "no override given" or "override normalized to nothing"
        discipline_slug = generate_slug(tournament, data.kind, data.weapon, data.gender, data.material)
    else:
        if any(d.slug == data.slug for d in tournament.disciplines):
            raise HTTPException(status_code=409, detail=f"discipline_slug_taken: {data.slug}")
        discipline_slug = data.slug
    discipline = Discipline(
        tournament=tournament,
        slug=discipline_slug,
        name=name,
        weapon=data.weapon,
        gender=data.gender,
        material=data.material,
        kind=data.kind,
        team_min=data.team_min,
        team_max=data.team_max,
        capacity=data.capacity,
        fee=data.fee,
        fee_early=data.fee_early,
        fee_eur=data.fee_eur,
        fee_early_eur=data.fee_early_eur,
        schedule_when=data.schedule_when,
        schedule_where=data.schedule_where,
        ruleset_name=data.ruleset_name,
        ruleset_url=data.ruleset_url,
    )
    if data.ordinal is not None:
        discipline.ordinal = data.ordinal
    session.add(discipline)
    setup.guard_published_completeness(tournament)
    session.commit()
    session.refresh(discipline)
    # identity_frozen defaults to False (DisciplineOut) — correct here, since
    # nothing can reference a discipline created in this same request
    return discipline


def _discipline_referenced(session: Session, discipline: Discipline) -> bool:
    """Whether any registration already references this discipline, individual
    or team — a discipline's kind is frozen once this is true (design
    team-disciplines: "A discipline's kind SHALL NOT change once any
    registration references it")."""
    return (
        session.scalar(
            select(RegistrationDiscipline.id)
            .where(RegistrationDiscipline.discipline_id == discipline.id)
            .limit(1)
        )
        is not None
        or session.scalar(
            select(Team.id).where(Team.discipline_id == discipline.id).limit(1)
        )
        is not None
    )


def _disciplines_frozen(session: Session, tournament: Tournament) -> dict[int, bool]:
    """`_discipline_referenced`, for every discipline of the tournament at
    once: two grouped queries rather than two per discipline, so serializing
    a tournament detail does not cost 2N queries (design
    discipline-identity-modal D6)."""
    discipline_ids = [d.id for d in tournament.disciplines]
    if not discipline_ids:
        return {}
    referenced = set(
        session.scalars(
            select(RegistrationDiscipline.discipline_id).where(
                RegistrationDiscipline.discipline_id.in_(discipline_ids)
            )
        )
    ) | set(
        session.scalars(
            select(Team.discipline_id).where(Team.discipline_id.in_(discipline_ids))
        )
    )
    return {discipline_id: discipline_id in referenced for discipline_id in discipline_ids}


def _apply_disciplines_frozen(session: Session, tournament: Tournament, out: TournamentOut) -> None:
    frozen = _disciplines_frozen(session, tournament)
    for discipline, discipline_out in zip(tournament.disciplines, out.disciplines, strict=True):
        discipline_out.identity_frozen = frozen.get(discipline.id, False)


@router.patch("/{slug}/disciplines/{discipline_slug}", response_model=DisciplineOut)
def update_discipline(
    discipline_slug: str,
    data: DisciplineIn,
    tournament: TournamentDep,
    session: SessionDep,
    fencer: FencerDep,
):
    require_console_access(session, tournament, fencer)
    discipline = next((d for d in tournament.disciplines if d.slug == discipline_slug), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    money_errors = money_bounds.collect_local_money_errors(
        tournament, {"fee": data.fee, "fee_early": data.fee_early}
    )
    if money_errors:
        raise FieldValidationError(money_errors)
    # already normalized (and, if it normalized to nothing, mapped to None) by
    # the schema's own BeforeValidator (design D6, task 8a.1)
    normalized_slug = data.slug
    referenced = _discipline_referenced(session, discipline)
    slug_changed = normalized_slug is not None and normalized_slug != discipline.slug
    classification_changed = (
        data.weapon != discipline.weapon
        or data.gender != discipline.gender
        or data.material != discipline.material
    )
    if (slug_changed or classification_changed) and referenced:
        raise HTTPException(status_code=409, detail="discipline_slug_frozen")
    if data.kind != discipline.kind and referenced:
        raise HTTPException(status_code=409, detail="discipline_kind_frozen")
    if slug_changed:
        if any(d.slug == normalized_slug for d in tournament.disciplines if d.id != discipline.id):
            raise HTTPException(
                status_code=409, detail=f"discipline_slug_taken: {normalized_slug}"
            )
        discipline.slug = normalized_slug
    if not taxonomy.is_taxonomy_weapon(data.weapon) and not data.name:
        raise HTTPException(status_code=422, detail="discipline_name_required")
    discipline.weapon = data.weapon
    discipline.gender = data.gender
    discipline.material = data.material
    discipline.name = data.name or taxonomy.discipline_name(
        data.weapon, data.gender, data.material, data.kind == DisciplineKind.TEAM
    ) or discipline.name
    if data.ordinal is not None:
        discipline.ordinal = data.ordinal
    discipline.kind = data.kind
    discipline.team_min = data.team_min
    discipline.team_max = data.team_max
    discipline.capacity = data.capacity
    discipline.fee = data.fee
    discipline.fee_early = data.fee_early
    discipline.fee_eur = data.fee_eur
    discipline.fee_early_eur = data.fee_early_eur
    discipline.schedule_when = data.schedule_when
    discipline.schedule_where = data.schedule_where
    discipline.ruleset_name = data.ruleset_name
    discipline.ruleset_url = data.ruleset_url
    setup.guard_published_completeness(tournament)
    session.commit()
    session.refresh(discipline)
    out = DisciplineOut.model_validate(discipline)
    # `referenced` was computed above, before this edit — an edit changes
    # nothing about whether the discipline is referenced
    out.identity_frozen = referenced
    return out


@router.delete("/{slug}/disciplines/{discipline_slug}", status_code=204)
def delete_discipline(
    discipline_slug: str, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    discipline = next((d for d in tournament.disciplines if d.slug == discipline_slug), None)
    if discipline is None:
        raise HTTPException(status_code=404, detail="discipline_not_found")
    session.delete(discipline)
    # the in-memory collection does not drop the row on delete()/flush() alone
    # (only a commit + expire would); guard_published_completeness reads it
    # directly, so it must reflect the deletion before that check runs
    tournament.disciplines.remove(discipline)
    setup.guard_published_completeness(tournament)
    session.commit()


@router.get("/{slug}/teams", response_model=list[ConsoleTeamDisciplineOut])
def console_teams(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Read-only, per team discipline: every team with its entering fencer,
    ordered roster, member count, waitlist position, and below-minimum flag.
    Offers no action (spec: "Organizer's read-only teams view") — there is no
    admit/edit/cancel endpoint here or anywhere else for a team."""
    require_console_access(session, tournament, fencer)
    today = datetime.now(UTC).date()
    deadline = tournament.team_composition_deadline
    deadline_passed = deadline is not None and today > deadline

    result = []
    for discipline in tournament.disciplines:
        if discipline.kind != DisciplineKind.TEAM:
            continue
        teams = session.scalars(
            select(Team)
            .where(Team.discipline_id == discipline.id)
            .options(selectinload(Team.members), selectinload(Team.registration))
            .order_by(Team.created_at)
        ).all()
        waitlist_position = 0
        team_rows = []
        for team in teams:
            if team.waitlisted:
                waitlist_position += 1
                position = waitlist_position
            else:
                position = None
            team_rows.append(
                ConsoleTeamOut(
                    id=team.id,
                    name=team.name,
                    entering_fencer=team.registration.fencer.display_name,
                    waitlisted=team.waitlisted,
                    waitlist_position=position,
                    members=[
                        {
                            "name": m.name,
                            "hr_id": m.hr_id,
                            "club": m.club,
                            "nationality": m.nationality,
                        }
                        for m in team.members
                    ],
                    below_minimum=deadline_passed and len(team.members) < discipline.team_min,
                )
            )
        result.append(
            ConsoleTeamDisciplineOut(
                slug=discipline.slug,
                name=discipline.name,
                team_min=discipline.team_min,
                team_max=discipline.team_max,
                teams=team_rows,
            )
        )
    return result


@router.get("/{slug}/queue", response_model=QueueOut)
def console_queue(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Where the line falls in every individual discipline: who is seated, who
    is queued and in what order, and how many places are free.

    Nothing here promotes anyone. After the seating deadline the system shows
    the data and the organizer decides (design Non-Goals), so the view's job is
    to make the pending work obvious. A discipline with an empty queue is still
    listed, stated as empty rather than hidden."""
    require_console_access(session, tournament, fencer)
    result = []
    for discipline in tournament.disciplines:
        if discipline.kind != DisciplineKind.INDIVIDUAL:
            continue
        entries = session.scalars(
            select(RegistrationDiscipline)
            .join(Registration)
            .where(
                RegistrationDiscipline.discipline_id == discipline.id,
                Registration.state.in_(
                    [RegistrationState.RESERVED, RegistrationState.PAID]
                ),
            )
            .options(selectinload(RegistrationDiscipline.registration))
            .order_by(Registration.registered_at)
        ).all()
        seated, queued = [], []
        for entry in entries:
            registration = entry.registration
            row = QueueEntryOut(
                registration_id=registration.id,
                fencer=registration.fencer.display_name,
                club=registration.fencer.club,
                vs=registration.vs,
                registered_at=registration.registered_at,
                # the query is already ordered by registration time, which is
                # exactly what queue_position ranks by, so position is the
                # running count rather than a per-row subquery
                queue_position=len(queued) + 1 if entry.is_substitute else None,
            )
            (queued if entry.is_substitute else seated).append(row)
        taken = taken_seats(session, discipline)
        result.append(
            QueueDisciplineOut(
                slug=discipline.slug,
                name=discipline.name,
                capacity=discipline.capacity,
                taken=taken,
                free=max(discipline.capacity - taken, 0),
                seated=seated,
                queued=queued,
            )
        )
    return QueueOut(
        seating_deadline=setup.seating_deadline_for(tournament),
        seating_settled_at=tournament.seating_settled_at,
        pending_demotions=scheduler.pending_demotions(session, tournament),
        disciplines=result,
    )


@router.post("/{slug}/settle-seating", response_model=SettleSeatingOut)
def settle_seating(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Close seating early, once the roster looks the way the organizer wants
    it. The same pass the deadline runs, through the same stamp, so a manual
    settlement and a scheduled one can never both happen — whichever fires
    first is the one that ever runs (design D6).

    Available in every mode, including `immediate`, where it demotes nobody but
    still closes seating so later registrations join the queue instead of
    taking seats. Not reversible: the organizer's route to correct an
    individual case afterwards is promotion."""
    require_console_access(session, tournament, fencer)
    if tournament.seating_settled_at is not None:
        raise HTTPException(status_code=409, detail="seating_already_settled")
    demoted = scheduler.settle_seating(session, tournament)
    return SettleSeatingOut(
        demoted=demoted, seating_settled_at=tournament.seating_settled_at
    )


def _normalized_extra_item_fields(data: ExtraItemIn) -> dict:
    """Enforce the action/item kind split (design D4): action categories
    (seminar, afterparty, other_action) always store a max_qty of 1; item
    categories (rental, merch, other_item) carry no schedule fields."""
    fields = data.model_dump()
    if data.category in ACTION_CATEGORIES:
        fields["max_qty"] = 1
    elif data.schedule_when or data.schedule_where:
        raise HTTPException(status_code=422, detail="schedule_fields_not_allowed_for_item_category")
    return fields


@router.post("/{slug}/extra-items", response_model=ExtraItemOut, status_code=201)
def add_extra_item(
    data: ExtraItemIn, tournament: TournamentDep, session: SessionDep, fencer: FencerDep
):
    require_console_access(session, tournament, fencer)
    money_errors = money_bounds.collect_local_money_errors(tournament, {"price": data.price})
    if money_errors:
        raise FieldValidationError(money_errors)
    item = ExtraItem(tournament=tournament, **_normalized_extra_item_fields(data))
    session.add(item)
    setup.guard_published_completeness(tournament)
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
    money_errors = money_bounds.collect_local_money_errors(tournament, {"price": data.price})
    if money_errors:
        raise FieldValidationError(money_errors)
    fields = _normalized_extra_item_fields(data)
    item.name = fields["name"]
    item.category = fields["category"]
    item.price = fields["price"]
    item.price_eur = fields["price_eur"]
    item.max_qty = fields["max_qty"]
    item.schedule_when = fields["schedule_when"]
    item.schedule_where = fields["schedule_where"]
    item.remark = fields["remark"]
    item.option_label = fields["option_label"]
    item.option_choices = fields["option_choices"]
    setup.guard_published_completeness(tournament)
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
    tournament.extra_items.remove(item)
    setup.guard_published_completeness(tournament)
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
    out = TournamentOut.model_validate(tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


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
    out = TournamentOut.model_validate(tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


@router.post("/{slug}/cancel", response_model=TournamentOut)
def cancel_tournament(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """Retire a tournament with history: hidden from public listings,
    registration gate rejects (closed), console and data remain (design D5)."""
    require_tournament_owner(tournament, fencer)
    tournament.cancelled_at = datetime.now(UTC)
    session.commit()
    session.refresh(tournament)
    out = TournamentOut.model_validate(tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


@router.post("/{slug}/publish", response_model=TournamentOut)
def publish_tournament(tournament: TournamentDep, session: SessionDep, fencer: FencerDep):
    """One-time, irreversible: stamps the publication record so the
    tournament becomes visible to fencers and open within its registration
    window (design D4). Open to any console team member, not owner-only."""
    require_console_access(session, tournament, fencer)
    if tournament.published_at is not None:
        raise HTTPException(status_code=409, detail="already_published")
    if tournament.cancelled_at is not None:
        raise HTTPException(status_code=409, detail="cancelled")
    missing = setup.setup_missing(tournament)
    if missing:
        raise HTTPException(
            status_code=422, detail={"reason": "setup_incomplete", "missing": missing}
        )
    tournament.published_at = datetime.now(UTC)
    tournament.published_by_id = fencer.id
    session.commit()
    session.refresh(tournament)
    out = TournamentOut.model_validate(tournament)
    out.setup_missing = setup.setup_missing(tournament)
    _apply_disciplines_frozen(session, tournament, out)
    return out


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
