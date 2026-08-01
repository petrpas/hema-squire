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

A tournament prices in its local currency and, optionally, in EUR as a second
currency — two independent, organizer-typed figures per item (design Decision
1). Every computation here takes `which` to say which currency's column to
read; the two totals are computed by the same pipeline over different inputs
and are never expected to correspond at any exchange rate. No rate is read
anywhere in this module — `Tournament.eur_rate` is a Setup convenience
consulted only by the frontend's recalculate-missing action.
"""

import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, NamedTuple

from app.models import Discipline, ExtraItem, Registration, Tournament

# which currency column a computation reads: the tournament's local currency,
# or its optional second, EUR-denominated one
PriceColumn = Literal["local", "eur"]

# the implicit category of discipline entries; extras carry ExtraCategory values
DISCIPLINE_CATEGORY = "discipline"
# canonical order in which a multi-category fixed discount consumes subtotals
_CATEGORY_ORDER = [
    DISCIPLINE_CATEGORY,
    "seminar",
    "rental",
    "afterparty",
    "merch",
    "other_action",
    "other_item",
]


class Totals(NamedTuple):
    """A registration's or a hypothetical selection's total(s). `local` is
    always present; `eur` is None when the tournament does not price in EUR."""

    local: int
    eur: int | None


def _early(tournament: Tournament, at: datetime.date) -> bool:
    return tournament.early_bird_until is not None and at <= tournament.early_bird_until


def discipline_fee(
    tournament: Tournament, discipline: Discipline, at: datetime.date, which: PriceColumn = "local"
) -> int:
    early = _early(tournament, at)
    if which == "eur":
        if early and discipline.fee_early_eur is not None:
            return discipline.fee_early_eur
        return discipline.fee_eur or 0
    if early and discipline.fee_early is not None:
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
    which: PriceColumn,
) -> int:
    subtotals: dict[str, Decimal] = {
        DISCIPLINE_CATEGORY: Decimal(sum(discipline_fee(tournament, d, at, which) for d in disciplines))
    }
    for item, qty in extras:
        category = item.category.value
        price = (item.price_eur if which == "eur" else item.price) or 0
        amount = Decimal(price * qty)
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
            value = (effect.get("value_eur") if which == "eur" else effect.get("value")) or 0
            _apply_fixed(subtotals, scope, value)
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
    which: PriceColumn = "local",
) -> int:
    """Amount due, in one currency, for a set of active (non-substitute)
    picks, independent of whether they're persisted — the pricing entry point
    shared by a saved registration's total and the unsaved price preview.

    Extras are billed only when at least one discipline is active (a
    fully-queued substitute registration owes nothing until admission). The
    legacy weapon-rental/afterparty parameters are single-currency (design
    Decision 9) and contribute only to the local total.
    """
    if not disciplines:
        return 0
    if uses_itemized_pricing(tournament):
        return _itemized_selection_total(tournament, disciplines, extras, at, which)
    total = sum(discipline_fee(tournament, d, at, which) for d in disciplines)
    if which == "local":
        total += len(weapon_rentals) * weapon_rental_fee(tournament, at)
        if afterparty:
            total += afterparty_fee(tournament, at)
    return total


def selection_totals(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
) -> Totals:
    """Both currencies' totals for a selection, each independently computed
    and summed from its own column (design Decision 1) — the totals need not
    and are not expected to correspond at any exchange rate."""
    local = selection_total(
        tournament,
        disciplines=disciplines,
        extras=extras,
        weapon_rentals=weapon_rentals,
        afterparty=afterparty,
        at=at,
        which="local",
    )
    eur = None
    if tournament.shows_eur:
        eur = selection_total(
            tournament,
            disciplines=disciplines,
            extras=extras,
            weapon_rentals=weapon_rentals,
            afterparty=afterparty,
            at=at,
            which="eur",
        )
    return Totals(local=local, eur=eur)


def registration_total(registration: Registration, tournament: Tournament) -> Totals:
    """Amount(s) due now for a persisted registration; delegates to
    `selection_totals`."""
    active = [e.discipline for e in registration.entries if not e.is_substitute]
    extras = [(s.item, s.qty) for s in registration.extra_selections]
    return selection_totals(
        tournament,
        disciplines=active,
        extras=extras,
        weapon_rentals=registration.weapon_rentals,
        afterparty=registration.afterparty,
        at=registration.registered_at.date(),
    )
