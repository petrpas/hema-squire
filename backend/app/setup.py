"""Setup completeness: the single source of truth for which mandatory Setup
items a tournament is still missing. Drives the console checklist and the
registration gate — a tournament with a non-empty result must not accept
registrations."""

import datetime

from app.models import Currency, Tournament

# distinct 4xx reasons a registration submission can be rejected with
NOT_PUBLISHED = "not_published"
NOT_YET_OPEN = "not_yet_open"
CLOSED = "closed"

# stable item keys, referenced by the frontend checklist and i18n catalogues
MISSING_LOCATION = "location"
MISSING_ORGANIZERS = "organizers"
MISSING_DISCIPLINES = "disciplines"
MISSING_DISCIPLINE_PRICES = "discipline_prices"
MISSING_EUR_RATE = "eur_rate"


def setup_missing(tournament: Tournament) -> list[str]:
    missing = []
    if not (tournament.location or "").strip():
        missing.append(MISSING_LOCATION)
    if not tournament.organizers:
        missing.append(MISSING_ORGANIZERS)
    if not tournament.disciplines:
        missing.append(MISSING_DISCIPLINES)
    elif any(d.fee is None for d in tournament.disciplines):
        missing.append(MISSING_DISCIPLINE_PRICES)
    # a tournament that promises EUR payments without a rate would quote a EUR
    # amount it cannot compute, so it must not take registrations
    if (
        tournament.eur_payments_enabled
        and tournament.primary_currency != Currency.EUR
        and not (tournament.eur_rate and tournament.eur_rate > 0)
    ):
        missing.append(MISSING_EUR_RATE)
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
