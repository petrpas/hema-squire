"""Setup completeness: the single source of truth for which mandatory Setup
items a tournament is still missing. Drives the PUBLISH tab and is the
precondition for publication; the registration gate reads the publication
record instead, since a published tournament is guaranteed complete (see
guard_published_completeness)."""

import datetime

from fastapi import HTTPException

from app.models import DisciplineKind, PaymentMode, Tournament

# distinct 4xx reasons a registration submission can be rejected with
NOT_PUBLISHED = "not_published"
NOT_YET_OPEN = "not_yet_open"
CLOSED = "closed"

# stable item keys, referenced by the frontend checklist and i18n catalogues
MISSING_LOCATION = "location"
MISSING_ORGANIZERS = "organizers"
MISSING_DISCIPLINES = "disciplines"
MISSING_DISCIPLINE_PRICES = "discipline_prices"
MISSING_EXTRA_ITEM_PRICES = "extra_item_prices"
MISSING_DISCOUNT_PRICES = "discount_prices"
# a tournament still pricing through the legacy fixed weapon-rental/
# afterparty parameters cannot enable EUR — those parameters are
# single-currency and gain no EUR counterpart (design Decision 9)
MISSING_LEGACY_BLOCKS_EUR = "legacy_fixed_fees_block_eur"
# a team discipline lacking valid roster bounds (design team-disciplines 3.2)
MISSING_TEAM_BOUNDS = "team_bounds"
# the account payments are collected into, mandatory only once the
# tournament can produce a nonzero total (design Decision 2)
MISSING_BANK_ACCOUNT = "bank_account"
# the flat deposit, mandatory only in deposit mode — where it is a price like
# any other, EUR figure included (design add-payment-modes D4)
MISSING_DEPOSIT_AMOUNT = "deposit_amount"


def uses_legacy_fixed_fees(tournament: Tournament) -> bool:
    """Whether pricing still depends on the fixed weapon-rental/afterparty
    parameters — incompatible with EUR because they carry no EUR column."""
    return (
        bool(tournament.weapon_rental_fee)
        or tournament.weapon_rental_fee_early is not None
        or bool(tournament.afterparty_fee)
        or tournament.afterparty_fee_early is not None
    )


def charges_money(tournament: Tournament) -> bool:
    """Whether the tournament can produce a nonzero total from any priced
    field, in either currency — the bank account is mandatory only when this
    is true (design Decision 2). Discounts are excluded: they only reduce a
    total, so they cannot make a free tournament charge."""
    if any(
        (d.fee or 0) > 0
        or (d.fee_early or 0) > 0
        or (d.fee_eur or 0) > 0
        or (d.fee_early_eur or 0) > 0
        for d in tournament.disciplines
    ):
        return True
    if any(
        (item.price or 0) > 0 or (item.price_eur or 0) > 0
        for item in tournament.extra_items
    ):
        return True
    return (
        (tournament.weapon_rental_fee or 0) > 0
        or (tournament.weapon_rental_fee_early or 0) > 0
        or (tournament.afterparty_fee or 0) > 0
        or (tournament.afterparty_fee_early or 0) > 0
    )


def setup_missing(tournament: Tournament) -> list[str]:
    missing = []
    if not (tournament.location or "").strip():
        missing.append(MISSING_LOCATION)
    if not tournament.organizers:
        missing.append(MISSING_ORGANIZERS)
    if not tournament.disciplines:
        missing.append(MISSING_DISCIPLINES)
    else:
        incomplete = any(d.fee is None for d in tournament.disciplines)
        if tournament.shows_eur:
            incomplete = incomplete or any(
                d.fee_eur is None for d in tournament.disciplines
            )
        if incomplete:
            missing.append(MISSING_DISCIPLINE_PRICES)
        if any(
            d.kind == DisciplineKind.TEAM
            and (
                d.team_min is None
                or d.team_max is None
                or d.team_min < 1
                or d.team_max < d.team_min
            )
            for d in tournament.disciplines
        ):
            missing.append(MISSING_TEAM_BOUNDS)

    # the composition deadline checks, it never enforces (design D7): a
    # tournament may offer team disciplines with no deadline set, so it is
    # deliberately not a completeness item

    # completeness follows from the form: a rendered price field left empty is
    # incomplete, whether it belongs to an extra item or a fixed discount
    # (design Decision 2) — no separate EUR-completeness rule
    if tournament.shows_eur:
        if any(item.price_eur is None for item in tournament.extra_items):
            missing.append(MISSING_EXTRA_ITEM_PRICES)
        if any(
            (discount.get("effect") or {}).get("kind") == "fixed"
            and (discount.get("effect") or {}).get("value_eur") is None
            for discount in (tournament.discounts or [])
        ):
            missing.append(MISSING_DISCOUNT_PRICES)
        if uses_legacy_fixed_fees(tournament):
            missing.append(MISSING_LEGACY_BLOCKS_EUR)

    if tournament.payment_mode == PaymentMode.DEPOSIT and (
        not tournament.deposit_amount
        or (tournament.shows_eur and not tournament.deposit_amount_eur)
    ):
        missing.append(MISSING_DEPOSIT_AMOUNT)

    if charges_money(tournament) and not (tournament.bank_account or "").strip():
        missing.append(MISSING_BANK_ACCOUNT)
    return missing


def guard_published_completeness(tournament: Tournament) -> None:
    """Raise 422 when a save would leave a published tournament missing a
    mandatory item (design D3): called after the mutation is applied to the
    ORM objects and before commit, so the session rolls back and nothing is
    written. No-op on a draft, which stays freely editable into
    incompleteness."""
    if tournament.published_at is None:
        return
    missing = setup_missing(tournament)
    if missing:
        raise HTTPException(
            status_code=422, detail={"reason": "setup_incomplete", "missing": missing}
        )


def registration_availability(tournament: Tournament, today: datetime.date) -> str | None:
    """None when a new registration submission may proceed; otherwise the
    reason it is rejected (gate order: cancelled -> published -> opens ->
    closes — design D2 of add-explicit-publishing). Completeness is not
    re-checked here: a published tournament is guaranteed complete by
    guard_published_completeness.

    Applies only to new submissions — never to cancellation, payment
    matching, or admission of substitutes on existing registrations.
    """
    if tournament.cancelled_at is not None:
        return CLOSED
    if tournament.published_at is None:
        return NOT_PUBLISHED
    if tournament.registration_opens is not None and today < tournament.registration_opens:
        return NOT_YET_OPEN
    closes = tournament.registration_closes or tournament.date
    if today > closes:
        return CLOSED
    return None


def seating_deadline_for(tournament: Tournament) -> datetime.date:
    """The date this tournament's seating settles on. Unset, `seating_deadline`
    resolves to `registration_closes`, which itself resolves to the tournament
    date (Decision 7) — a tournament with no explicit deadline settles when
    registration closes and has no organizer-managed tail. The chain lives
    here alone; no caller spells it out a second time."""
    if tournament.seating_deadline is not None:
        return tournament.seating_deadline
    return tournament.registration_closes or tournament.date


def seating_has_settled(tournament: Tournament, today: datetime.date) -> bool:
    """Whether seating is closed — asked by post-deadline registration, the
    reminder anchor, and the expiry branch alike (Decision 6a).

    Both disjuncts are needed. The stamp alone leaves the gap between the
    deadline passing at midnight and the next scheduler tick, during which
    registrations would still be seated; the deadline alone ignores an
    organizer who settled early by hand."""
    return (
        tournament.seating_settled_at is not None
        or today > seating_deadline_for(tournament)
    )


def amendment_availability(tournament: Tournament, today: datetime.date) -> str | None:
    """None when an amendment submission may proceed; otherwise the reason it
    is rejected. Amendment is closed by every reason registration is, plus its
    own `amendments_close` boundary when set — unset means "same window as
    registration" (Decision 4), which this reduces to exactly."""
    reason = registration_availability(tournament, today)
    if reason is not None:
        return reason
    if tournament.amendments_close is not None and today > tournament.amendments_close:
        return CLOSED
    return None
