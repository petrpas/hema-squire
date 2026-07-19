"""Fee computation. Prices are a pure function of (tournament, item, as-of date),
so amounts frozen at registration time are reproducible instead of stored.

Two pricing worlds exist:

- Itemized (tournaments with extra_items or discounts): categorized item
  prices, then an ordered discount list — all applicable fixed discounts
  first, then percentage discounts sequentially, each within its category
  scope — rounded half-up to a whole currency unit exactly once at the end.
- Legacy (everything else): per-discipline fees plus the fixed
  weapon-rental/afterparty parameters, with per-item early-bird variants.
  Kept verbatim so historical totals and the pilot replay stay reproducible.
"""

import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.models import Discipline, Registration, Tournament

# the implicit category of discipline entries; extras carry ExtraCategory values
DISCIPLINE_CATEGORY = "discipline"
# canonical order in which a multi-category fixed discount consumes subtotals
_CATEGORY_ORDER = [DISCIPLINE_CATEGORY, "seminar", "rental", "afterparty", "merch"]


def _early(tournament: Tournament, at: datetime.date) -> bool:
    return tournament.early_bird_until is not None and at <= tournament.early_bird_until


def discipline_fee(tournament: Tournament, discipline: Discipline, at: datetime.date) -> int:
    if _early(tournament, at) and discipline.fee_early is not None:
        return discipline.fee_early
    return discipline.fee or 0


def weapon_rental_fee(tournament: Tournament, at: datetime.date) -> int:
    if _early(tournament, at) and tournament.weapon_rental_fee_early is not None:
        return tournament.weapon_rental_fee_early
    return tournament.weapon_rental_fee


def afterparty_fee(tournament: Tournament, at: datetime.date) -> int:
    if _early(tournament, at) and tournament.afterparty_fee_early is not None:
        return tournament.afterparty_fee_early
    return tournament.afterparty_fee


def uses_itemized_pricing(tournament: Tournament) -> bool:
    return bool(tournament.extra_items) or bool(tournament.discounts)


def _condition_met(
    condition: dict, *, discipline_count: int, at: datetime.date
) -> bool:
    kind = condition.get("kind")
    if kind == "discipline_count":
        return discipline_count == condition.get("count")
    if kind == "early":
        until = condition.get("until")
        return until is not None and at <= datetime.date.fromisoformat(until)
    # unknown kinds are unreachable through schema validation; fail closed
    return False


def _apply_fixed(subtotals: dict[str, Decimal], scope: list[str], value: int) -> None:
    """Subtract up to `value` from the scoped subtotals, floored at zero,
    consuming categories in canonical order so the result is deterministic."""
    remaining = Decimal(value)
    for category in _CATEGORY_ORDER:
        if category not in scope or remaining <= 0:
            continue
        take = min(subtotals.get(category, Decimal(0)), remaining)
        if take > 0:
            subtotals[category] -= take
            remaining -= take


def _itemized_total(registration: Registration, tournament: Tournament) -> int:
    at = registration.registered_at.date()
    active = [e for e in registration.entries if not e.is_substitute]
    if not active:
        return 0

    subtotals: dict[str, Decimal] = {
        DISCIPLINE_CATEGORY: Decimal(sum(e.discipline.fee or 0 for e in active))
    }
    for selection in registration.extra_selections:
        category = selection.item.category.value
        amount = Decimal(selection.item.price * selection.qty)
        subtotals[category] = subtotals.get(category, Decimal(0)) + amount

    applicable = [
        d
        for d in (tournament.discounts or [])
        if _condition_met(d.get("condition", {}), discipline_count=len(active), at=at)
    ]
    for discount in applicable:
        effect = discount.get("effect", {})
        if effect.get("kind") == "fixed":
            scope = discount.get("scope") or [DISCIPLINE_CATEGORY]
            _apply_fixed(subtotals, scope, effect.get("value", 0))
    for discount in applicable:
        effect = discount.get("effect", {})
        if effect.get("kind") == "percent":
            scope = discount.get("scope") or [DISCIPLINE_CATEGORY]
            factor = (Decimal(100) - Decimal(effect.get("value", 0))) / Decimal(100)
            for category in scope:
                if category in subtotals:
                    subtotals[category] *= factor

    total = sum(subtotals.values(), Decimal(0))
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def registration_total(registration: Registration, tournament: Tournament) -> int:
    """Amount due now: non-substitute discipline entries plus extras.

    Extras are billed only when at least one discipline entry is active
    (a fully-queued substitute registration owes nothing until admission).
    """
    if uses_itemized_pricing(tournament):
        return _itemized_total(registration, tournament)

    at = registration.registered_at.date()
    active = [e for e in registration.entries if not e.is_substitute]
    if not active:
        return 0
    total = sum(discipline_fee(tournament, e.discipline, at) for e in active)
    total += len(registration.weapon_rentals) * weapon_rental_fee(tournament, at)
    if registration.afterparty:
        total += afterparty_fee(tournament, at)
    return total
