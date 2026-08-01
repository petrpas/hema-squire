"""Setup completeness: the single source of truth for which mandatory Setup
items a tournament is still missing. Drives the console checklist and the
registration gate — a tournament with a non-empty result must not accept
registrations."""

import datetime

from app.models import Tournament

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


def uses_legacy_fixed_fees(tournament: Tournament) -> bool:
    """Whether pricing still depends on the fixed weapon-rental/afterparty
    parameters — incompatible with EUR because they carry no EUR column."""
    return (
        bool(tournament.weapon_rental_fee)
        or tournament.weapon_rental_fee_early is not None
        or bool(tournament.afterparty_fee)
        or tournament.afterparty_fee_early is not None
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
    return missing


def registration_availability(tournament: Tournament, today: datetime.date) -> str | None:
    """None when a new registration submission may proceed; otherwise the
    reason it is rejected (D6 gate order: setup complete -> opens -> closes).

    Applies only to new submissions — never to cancellation, payment
    matching, or admission of substitutes on existing registrations.
    """
    if tournament.cancelled_at is not None:
        return CLOSED
    if setup_missing(tournament):
        return NOT_PUBLISHED
    if tournament.registration_opens is not None and today < tournament.registration_opens:
        return NOT_YET_OPEN
    closes = tournament.registration_closes or tournament.date
    if today > closes:
        return CLOSED
    return None


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
