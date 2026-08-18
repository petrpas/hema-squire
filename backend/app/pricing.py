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


class DiscountOutcome(NamedTuple):
    """One configured discount's result against a priced selection, within a
    single currency pass. `deducted` is 0 for a discount that did not apply."""

    name: str
    effect: dict
    applied: bool
    deducted: int


class DiscountBreakdown(NamedTuple):
    """One configured discount's result across both currency passes of a
    selection (design Decision 3): a fixed effect carries both `deducted` and
    `deducted_eur`; a percentage effect, being currency-neutral, carries only
    `deducted`. Both are None when the discount did not apply."""

    name: str
    effect: dict
    applied: bool
    deducted: int | None
    deducted_eur: int | None


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


def _apply_fixed(subtotals: dict[str, Decimal], scope: list[str], value: int) -> int:
    """Subtract up to `value` from the scoped subtotals, floored at zero,
    consuming categories in canonical order so the result is deterministic.
    Returns the amount actually deducted, which is `value` unless the scoped
    subtotals floor it first."""
    remaining = Decimal(value)
    for category in _CATEGORY_ORDER:
        if category not in scope or remaining <= 0:
            continue
        take = min(subtotals.get(category, Decimal(0)), remaining)
        if take > 0:
            subtotals[category] -= take
            remaining -= take
    return value - int(remaining)


def _itemized_selection_breakdown(
    tournament: Tournament,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    at: datetime.date,
    which: PriceColumn,
    team_disciplines: list[Discipline] = (),
) -> tuple[int, list[DiscountOutcome]]:
    """The total together with one `DiscountOutcome` per configured discount,
    in configured order — inactive discounts included, so a caller can report
    on the whole list, not just what applied.

    `team_disciplines` carries one entry per priced team (a discipline
    repeated once per team entered into it — not a `Team` row, so a
    hypothetical price preview can price teams without persisting any). Each
    entry contributes its discipline's per-team fee to the DISCIPLINE
    subtotal once, regardless of roster size. Team entries are deliberately
    not added to `disciplines` — that list feeds
    `_condition_met(discipline_count=...)`, and a team entry must not trip a
    discount conditioned on how many disciplines the fencer themselves
    entered (design team-disciplines D1/D3).
    """
    subtotals: dict[str, Decimal] = {
        DISCIPLINE_CATEGORY: Decimal(
            sum(discipline_fee(tournament, d, at, which) for d in disciplines)
            + sum(discipline_fee(tournament, d, at, which) for d in team_disciplines)
        )
    }
    for item, qty in extras:
        category = item.category.value
        price = (item.price_eur if which == "eur" else item.price) or 0
        amount = Decimal(price * qty)
        subtotals[category] = subtotals.get(category, Decimal(0)) + amount

    discounts = tournament.discounts or []
    met = [
        _condition_met(d.get("condition", {}), discipline_count=len(disciplines), at=at)
        for d in discounts
    ]
    deducted: list[int] = [0] * len(discounts)

    for i, discount in enumerate(discounts):
        if not met[i]:
            continue
        effect = discount.get("effect", {})
        if effect.get("kind") == "fixed":
            scope = discount.get("scope") or [DISCIPLINE_CATEGORY]
            value = (effect.get("value_eur") if which == "eur" else effect.get("value")) or 0
            deducted[i] = _apply_fixed(subtotals, scope, value)
    for i, discount in enumerate(discounts):
        if not met[i]:
            continue
        effect = discount.get("effect", {})
        if effect.get("kind") == "percent":
            scope = discount.get("scope") or [DISCIPLINE_CATEGORY]
            factor = (Decimal(100) - Decimal(effect.get("value", 0))) / Decimal(100)
            before = sum((subtotals[c] for c in scope if c in subtotals), Decimal(0))
            for category in scope:
                if category in subtotals:
                    subtotals[category] *= factor
            after = sum((subtotals[c] for c in scope if c in subtotals), Decimal(0))
            deducted[i] = int((before - after).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    outcomes = [
        DiscountOutcome(
            name=discount.get("name", ""),
            effect=discount.get("effect", {}),
            applied=met[i],
            deducted=deducted[i],
        )
        for i, discount in enumerate(discounts)
    ]

    total = sum(subtotals.values(), Decimal(0))
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)), outcomes


def _itemized_selection_total(
    tournament: Tournament,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    at: datetime.date,
    which: PriceColumn,
    team_disciplines: list[Discipline] = (),
) -> int:
    total, _ = _itemized_selection_breakdown(
        tournament, disciplines, extras, at, which, team_disciplines
    )
    return total


def selection_total(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    which: PriceColumn = "local",
    team_disciplines: list[Discipline] = (),
) -> int:
    """Amount due, in one currency, for a set of active (non-substitute)
    picks, independent of whether they're persisted — the pricing entry point
    shared by a saved registration's total and the unsaved price preview.

    `team_disciplines` carries one entry per priced team, as
    `_itemized_selection_breakdown` does. Extras are billed only when at
    least one discipline or team is active (a fully-queued substitute
    registration owes nothing until admission). The legacy weapon-rental/
    afterparty parameters are single-currency (design Decision 9) and
    contribute only to the local total. A legacy (non-itemized) tournament
    still prices a team's fee from the discipline row (design task 2.4) —
    teams join the same per-discipline sum extras do not.
    """
    if not disciplines and not team_disciplines:
        return 0
    if uses_itemized_pricing(tournament):
        return _itemized_selection_total(
            tournament, disciplines, extras, at, which, team_disciplines
        )
    total = sum(discipline_fee(tournament, d, at, which) for d in disciplines)
    total += sum(discipline_fee(tournament, d, at, which) for d in team_disciplines)
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
    team_disciplines: list[Discipline] = (),
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
        team_disciplines=team_disciplines,
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
            team_disciplines=team_disciplines,
        )
    return Totals(local=local, eur=eur)


def selection_discounts(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    at: datetime.date,
    team_disciplines: list[Discipline] = (),
) -> list[DiscountBreakdown]:
    """The per-discount breakdown for a selection, in configured order,
    reporting exactly what `selection_totals` applied rather than a separate
    evaluation. A fixed effect's deduction is read from its own currency's
    pass — local always, EUR only when the tournament shows one (design
    Decision 3); a percentage effect carries one currency-neutral figure,
    read from the local pass, since its condition can never differ between
    currencies. Empty for a legacy tournament or one with no discounts."""
    if not tournament.discounts:
        return []
    _, local_outcomes = _itemized_selection_breakdown(
        tournament, disciplines, extras, at, "local", team_disciplines
    )
    eur_outcomes: list[DiscountOutcome] | None = None
    if tournament.shows_eur:
        _, eur_outcomes = _itemized_selection_breakdown(
            tournament, disciplines, extras, at, "eur", team_disciplines
        )

    breakdown = []
    for i, outcome in enumerate(local_outcomes):
        is_fixed = outcome.effect.get("kind") == "fixed"
        deducted_eur = (
            eur_outcomes[i].deducted
            if outcome.applied and is_fixed and eur_outcomes
            else None
        )
        breakdown.append(
            DiscountBreakdown(
                name=outcome.name,
                effect=outcome.effect,
                applied=outcome.applied,
                deducted=outcome.deducted if outcome.applied else None,
                deducted_eur=deducted_eur,
            )
        )
    return breakdown


def registration_total(registration: Registration, tournament: Tournament) -> Totals:
    """Amount(s) due now for a persisted registration; delegates to
    `selection_totals`. Waitlisted teams are excluded exactly as substitute
    discipline entries are (design team-disciplines D3)."""
    active = [e.discipline for e in registration.entries if not e.is_substitute]
    extras = [(s.item, s.qty) for s in registration.extra_selections]
    team_disciplines = [t.discipline for t in registration.teams if not t.waitlisted]
    return selection_totals(
        tournament,
        disciplines=active,
        extras=extras,
        weapon_rentals=registration.weapon_rentals,
        afterparty=registration.afterparty,
        at=registration.registered_at.date(),
        team_disciplines=team_disciplines,
    )
