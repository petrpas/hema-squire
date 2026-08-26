"""Setup completeness: the single source of truth for which mandatory Setup
items a tournament is still missing. Drives the PUBLISH tab and is the
precondition for publication; the registration gate reads the publication
record instead, since a published tournament is guaranteed complete (see
guard_published_completeness)."""

import datetime
import zoneinfo

from fastapi import HTTPException

from app.constraints import DEFAULT_TIMEZONE
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

    # the deposit belongs to a payment mode, and no payment mode applies while
    # payments are off: the item could not be resolved (its editor is
    # concealed) and need not be, since nothing holds a seat with money that
    # is never requested (design tournament-modes D5, setup-navigation)
    if (
        tournament.feature_payments
        and tournament.payment_mode == PaymentMode.DEPOSIT
        and (
            not tournament.deposit_amount
            or (tournament.shows_eur and not tournament.deposit_amount_eur)
        )
    ):
        missing.append(MISSING_DEPOSIT_AMOUNT)

    # only a tournament Squire collects money for needs an account to collect
    # it into (design tournament-modes D5). Every other item above is
    # unaffected by the feature, because the rest of completeness is about what
    # the tournament offers rather than about collecting for it — a hidden team
    # discipline is still checked for roster bounds, an unpriced hidden extra
    # item is still reported (design D4)
    if (
        tournament.feature_payments
        and charges_money(tournament)
        and not (tournament.bank_account or "").strip()
    ):
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


def is_known_timezone(name: str | None) -> bool:
    """Whether the zone database knows this identifier. The write path's test
    (routers.tournaments); reads use `_zone`, which never rejects. A missing
    name is not known: the column is non-null, so clearing it is refused on
    the same terms as naming a zone that does not exist."""
    if not isinstance(name, str):
        return False
    try:
        zoneinfo.ZoneInfo(name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _zone(name: str | None) -> zoneinfo.ZoneInfo:
    """A zone to read a stored value in. Reads never fail on it: the write path
    is what validates the name (routers.tournaments), so an unresolvable one
    here means the zone database dropped an identifier that was valid when it
    was saved — a reason to fall back to the default and keep serving, not to
    fail every fencer's tournament list with a 500."""
    try:
        return zoneinfo.ZoneInfo(name or DEFAULT_TIMEZONE)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)


def zone_for(tournament: Tournament) -> zoneinfo.ZoneInfo:
    """This tournament's own zone."""
    return _zone(tournament.timezone)


def local_time_exists(timezone: str, day: datetime.date, clock: datetime.time) -> bool:
    """Whether that wall clock occurs at all on that day in that zone. False on
    the spring-forward morning for the hour the zone skips — the one case the
    write path refuses rather than resolving to an hour the organizer did not
    choose (design add-registration-open-time D4).

    A time that occurs *twice* (the autumn repeat) exists, and is accepted:
    `opening_instant` takes the first of the two.
    """
    zone = _zone(timezone)
    naive = datetime.datetime.combine(day, clock)
    aware = naive.replace(tzinfo=zone)
    # PEP 495: a skipped local time is exactly one that does not survive the
    # round trip through UTC
    return aware.astimezone(datetime.UTC).astimezone(zone).replace(tzinfo=None) == naive


def local_date(tournament: Tournament, now: datetime.datetime) -> datetime.date:
    """`now` as a calendar day in the tournament's own zone. Every whole-day
    boundary in the registration path is measured with this and never against
    a UTC day: a tournament that closes on the 30th is open until the end of
    the 30th where it is held (design add-registration-open-time D2)."""
    return now.astimezone(zone_for(tournament)).date()


def opening_instant(
    opens: datetime.date | None,
    opens_time: datetime.time | None,
    timezone: str,
) -> datetime.datetime | None:
    """The instant registration opens, in UTC — the single place the opening
    date, the opening time and the zone are folded together (design
    add-registration-open-time D1). None when no opening date is set, which
    means registration opens on publication.

    An unset time means the start of the local day, which is what a tournament
    carrying only a date has always meant. `fold=0` takes the *first* of an
    ambiguous local time (the hour the autumn clock change repeats): opening a
    little early is harmless, opening an hour after the announced time is the
    failure that matters (D4). A local time the zone skips cannot be stored —
    the write path rejects it — so this never has to resolve one.

    Takes the three values rather than a tournament so that the DTOs can fold
    their own fields with it (app.schemas) without a second implementation.
    """
    if opens is None:
        return None
    local = datetime.datetime.combine(
        opens, opens_time or datetime.time(0, 0), tzinfo=_zone(timezone)
    )
    return local.astimezone(datetime.UTC)


def registration_opens_at(tournament: Tournament) -> datetime.datetime | None:
    """This tournament's opening instant — `opening_instant` over its own
    stored values."""
    return opening_instant(
        tournament.registration_opens,
        tournament.registration_opens_time,
        tournament.timezone,
    )


def registration_availability(tournament: Tournament, now: datetime.datetime) -> str | None:
    """None when a new registration submission may proceed; otherwise the
    reason it is rejected (gate order: cancelled -> published -> opens ->
    closes — design D2 of add-explicit-publishing). Completeness is not
    re-checked here: a published tournament is guaranteed complete by
    guard_published_completeness.

    The two edges are measured differently, and the asymmetry is the point
    (design add-registration-open-time D3). Opening is a starting gun — an
    instant, to the minute the organizer named. Closing is a deadline — the
    whole of its local day, so every stored close keeps meaning what it meant
    before an opening time existed.

    Takes an instant rather than a date so that no caller can pass a UTC day
    and get the old, subtly-wrong answer.

    Applies only to new submissions — never to cancellation, payment
    matching, or admission of substitutes on existing registrations.
    """
    if tournament.cancelled_at is not None:
        return CLOSED
    if tournament.published_at is None:
        return NOT_PUBLISHED
    opens_at = registration_opens_at(tournament)
    if opens_at is not None and now < opens_at:
        return NOT_YET_OPEN
    closes = tournament.registration_closes or tournament.date
    if local_date(tournament, now) > closes:
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


def amendment_availability(tournament: Tournament, now: datetime.datetime) -> str | None:
    """None when an amendment submission may proceed; otherwise the reason it
    is rejected. Amendment is closed by every reason registration is, plus its
    own `amendments_close` boundary when set — unset means "same window as
    registration" (Decision 4), which this reduces to exactly.

    `amendments_close` stays a whole day, like the registration close it
    mirrors, and is measured in the tournament's own zone."""
    reason = registration_availability(tournament, now)
    if reason is not None:
        return reason
    if (
        tournament.amendments_close is not None
        and local_date(tournament, now) > tournament.amendments_close
    ):
        return CLOSED
    return None
