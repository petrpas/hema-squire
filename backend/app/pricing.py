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

from app.models import Discipline, ExtraItem, Registration, Tournament

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


def _itemized_selection_total(
    tournament: Tournament,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    at: datetime.date,
) -> int:
    subtotals: dict[str, Decimal] = {
        DISCIPLINE_CATEGORY: Decimal(sum(d.fee or 0 for d in disciplines))
    }
    for item, qty in extras:
        category = item.category.value
        amount = Decimal(item.price * qty)
        subtotals[category] = subtotals.get(category, Decimal(0)) + amount

    applicable = [
        d
        for d in (tournament.discounts or [])
        if _condition_met(d.get("condition", {}), discipline_count=len(disciplines), at=at)
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


def selection_total(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
) -> int:
    """Amount due for a set of active (non-substitute) picks, independent of
    whether they're persisted — the single pricing entry point shared by a
    saved registration's total and the unsaved price preview.

    Extras are billed only when at least one discipline is active (a
    fully-queued substitute registration owes nothing until admission).
    """
    if not disciplines:
        return 0
    if uses_itemized_pricing(tournament):
        return _itemized_selection_total(tournament, disciplines, extras, at)
    total = sum(discipline_fee(tournament, d, at) for d in disciplines)
    total += len(weapon_rentals) * weapon_rental_fee(tournament, at)
    if afterparty:
        total += afterparty_fee(tournament, at)
    return total


def registration_total(registration: Registration, tournament: Tournament) -> int:
    """Amount due now for a persisted registration; delegates to `selection_total`."""
    active = [e.discipline for e in registration.entries if not e.is_substitute]
    extras = [(s.item, s.qty) for s in registration.extra_selections]
    return selection_total(
        tournament,
        disciplines=active,
        extras=extras,
        weapon_rentals=registration.weapon_rentals,
        afterparty=registration.afterparty,
        at=registration.registered_at.date(),
    )
