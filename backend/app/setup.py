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


def setup_missing(tournament: Tournament) -> list[str]:
    missing = []
    if not (tournament.location or "").strip():
        missing.append(MISSING_LOCATION)
    if not tournament.organizer_names:
        missing.append(MISSING_ORGANIZERS)
    if not tournament.disciplines:
        missing.append(MISSING_DISCIPLINES)
    elif any(d.fee is None for d in tournament.disciplines):
        missing.append(MISSING_DISCIPLINE_PRICES)
    return missing


def registration_availability(tournament: Tournament, today: datetime.date) -> str | None:
    """None when a new registration submission may proceed; otherwise the
    reason it is rejected (D6 gate order: setup complete -> opens -> closes).

    Applies only to new submissions — never to cancellation, payment
    matching, or admission of substitutes on existing registrations.
    """
    if setup_missing(tournament):
        return NOT_PUBLISHED
    if tournament.registration_opens is not None and today < tournament.registration_opens:
        return NOT_YET_OPEN
    closes = tournament.registration_closes or tournament.date
    if today > closes:
        return CLOSED
    return None
