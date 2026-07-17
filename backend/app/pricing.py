"""Fee computation. Prices are a pure function of (tournament, item, as-of date),
so amounts frozen at registration time are reproducible instead of stored."""

import datetime

from app.models import Discipline, Registration, Tournament


def _early(tournament: Tournament, at: datetime.date) -> bool:
    return tournament.early_bird_until is not None and at <= tournament.early_bird_until


def discipline_fee(tournament: Tournament, discipline: Discipline, at: datetime.date) -> int:
    if _early(tournament, at) and discipline.fee_early is not None:
        return discipline.fee_early
    return discipline.fee


def weapon_rental_fee(tournament: Tournament, at: datetime.date) -> int:
    if _early(tournament, at) and tournament.weapon_rental_fee_early is not None:
        return tournament.weapon_rental_fee_early
    return tournament.weapon_rental_fee


def afterparty_fee(tournament: Tournament, at: datetime.date) -> int:
    if _early(tournament, at) and tournament.afterparty_fee_early is not None:
        return tournament.afterparty_fee_early
    return tournament.afterparty_fee


def registration_total(registration: Registration, tournament: Tournament) -> int:
    """Amount due now: non-substitute discipline fees plus extras.

    Extras are billed only when at least one discipline entry is active
    (a fully-queued substitute registration owes nothing until admission).
    """
    at = registration.registered_at.date()
    active = [e for e in registration.entries if not e.is_substitute]
    if not active:
        return 0
    total = sum(discipline_fee(tournament, e.discipline, at) for e in active)
    total += len(registration.weapon_rentals) * weapon_rental_fee(tournament, at)
    if registration.afterparty:
        total += afterparty_fee(tournament, at)
    return total
