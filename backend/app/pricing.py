"""Fee computation. Prices are a pure function of (tournament, item, as-of date),
so amounts frozen at registration time are reproducible instead of stored.

Two pricing worlds exist:

- Itemized (tournaments with extra_items or discounts): categorized item
  prices, then an ordered discount list — all applicable fixed discounts
  first, then percentage discounts sequentially, each within its category
  scope — rounded half-up to a whole currency unit exactly once at the end.
  A discount code runs in that list, last among its kind, in either world.
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
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, NamedTuple

from app.models import (
    Discipline,
    DiscountCode,
    ExtraCategory,
    ExtraItem,
    Registration,
    Tournament,
)
from app.setup import clocks_run, local_date

# which currency column a computation reads: the tournament's local currency,
# or its optional second, EUR-denominated one
PriceColumn = Literal["local", "eur"]

# the implicit category of discipline entries; extras carry ExtraCategory values
DISCIPLINE_CATEGORY = "discipline"
# the categories a legacy-priced tournament bills its flat-fee extras under,
# so that a reader groups them with the item categories they became
LEGACY_RENTAL = ExtraCategory.RENTAL.value
LEGACY_AFTERPARTY = ExtraCategory.AFTERPARTY.value
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
    single currency pass. `deducted` is 0 for a discount that did not apply.

    `by_category` is the same deduction split by the category it was taken
    from, unrounded: a fixed discount's take from each subtotal, a percentage
    one's `before − after` per category. Recorded in the pass that computes the
    total, so a per-category reading can never describe a different evaluation
    (design export-revenue D5)."""

    name: str
    effect: dict
    applied: bool
    deducted: int
    by_category: dict[str, Decimal]


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


def _condition_met(condition: dict, *, discipline_count: int, at: datetime.date) -> bool:
    kind = condition.get("kind")
    if kind == "discipline_count":
        return discipline_count == condition.get("count")
    if kind == "early":
        until = condition.get("until")
        return until is not None and at <= datetime.date.fromisoformat(until)
    # unknown kinds are unreachable through schema validation; fail closed
    return False


def _apply_fixed(subtotals: dict[str, Decimal], scope: list[str], value: int) -> dict[str, Decimal]:
    """Subtract up to `value` from the scoped subtotals, floored at zero,
    consuming categories in canonical order so the result is deterministic.
    Returns what was taken from each category; their sum is `value` unless the
    scoped subtotals floor it first."""
    remaining = Decimal(value)
    takes: dict[str, Decimal] = {}
    for category in _CATEGORY_ORDER:
        if category not in scope or remaining <= 0:
            continue
        take = min(subtotals.get(category, Decimal(0)), remaining)
        if take > 0:
            subtotals[category] -= take
            remaining -= take
            takes[category] = take
    return takes


def _code_discount(code: DiscountCode) -> dict:
    """A code in the shape the discount loop reads: always met, and reaching
    every category unless the organizer named some (design add-discount-codes
    D2)."""
    return {
        "name": code.name,
        "effect": code.effect,
        "scope": code.scope or _CATEGORY_ORDER,
    }


def _apply_discounts(
    subtotals: dict[str, Decimal], discounts: list[dict], met: list[bool], which: PriceColumn
) -> tuple[int, list[DiscountOutcome]]:
    """Run an ordered discount list over category subtotals: every fixed effect,
    then every percentage one, in list order within each. Returns the total,
    rounded once at the end, and one outcome per discount."""
    deducted: list[int] = [0] * len(discounts)
    by_category: list[dict[str, Decimal]] = [{} for _ in discounts]

    for i, discount in enumerate(discounts):
        if not met[i]:
            continue
        effect = discount.get("effect", {})
        if effect.get("kind") == "fixed":
            scope = discount.get("scope") or [DISCIPLINE_CATEGORY]
            value = (effect.get("value_eur") if which == "eur" else effect.get("value")) or 0
            by_category[i] = _apply_fixed(subtotals, scope, value)
            deducted[i] = int(sum(by_category[i].values(), Decimal(0)))
    for i, discount in enumerate(discounts):
        if not met[i]:
            continue
        effect = discount.get("effect", {})
        if effect.get("kind") == "percent":
            scope = discount.get("scope") or [DISCIPLINE_CATEGORY]
            factor = (Decimal(100) - Decimal(effect.get("value", 0))) / Decimal(100)
            for category in scope:
                if category in subtotals:
                    before = subtotals[category]
                    subtotals[category] *= factor
                    if before != subtotals[category]:
                        by_category[i][category] = before - subtotals[category]
            taken = sum(by_category[i].values(), Decimal(0))
            deducted[i] = int(taken.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    outcomes = [
        DiscountOutcome(
            name=discount.get("name", ""),
            effect=discount.get("effect", {}),
            applied=met[i],
            deducted=deducted[i],
            by_category=by_category[i],
        )
        for i, discount in enumerate(discounts)
    ]
    total = sum(subtotals.values(), Decimal(0))
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)), outcomes


def _itemized_selection_breakdown(
    tournament: Tournament,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    at: datetime.date,
    which: PriceColumn,
    team_disciplines: Sequence[Discipline] = (),
    code: DiscountCode | None = None,
) -> tuple[int, list[DiscountOutcome]]:
    """The total together with one `DiscountOutcome` per configured discount,
    in configured order — inactive discounts included, so a caller can report
    on the whole list, not just what applied — followed by the code's, where
    the selection carries one.

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

    discounts = list(tournament.discounts or [])
    met = [
        _condition_met(d.get("condition", {}), discipline_count=len(disciplines), at=at)
        for d in discounts
    ]
    if code is not None:
        discounts.append(_code_discount(code))
        met.append(True)
    return _apply_discounts(subtotals, discounts, met, which)


def _legacy_selection_breakdown(
    tournament: Tournament,
    disciplines: list[Discipline],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    which: PriceColumn,
    team_disciplines: Sequence[Discipline] = (),
    code: DiscountCode | None = None,
) -> tuple[int, list[DiscountOutcome]]:
    """The legacy total, and the code's outcome where there is one. A legacy
    tournament configures no discounts, so a code is the only one that can run.

    A code never moves a tournament off this path: `uses_itemized_pricing` does
    not know about codes, because the itemized path bills no flat fee and the
    first code an organizer added would stop billing them (design
    add-discount-codes D2). The flat fees are single-currency (design Decision
    9) and contribute only to the local total."""
    subtotals: dict[str, Decimal] = {
        DISCIPLINE_CATEGORY: Decimal(
            sum(discipline_fee(tournament, d, at, which) for d in disciplines)
            + sum(discipline_fee(tournament, d, at, which) for d in team_disciplines)
        )
    }
    if which == "local":
        subtotals[LEGACY_RENTAL] = Decimal(len(weapon_rentals) * weapon_rental_fee(tournament, at))
        if afterparty:
            subtotals[LEGACY_AFTERPARTY] = Decimal(afterparty_fee(tournament, at))
    discounts = [] if code is None else [_code_discount(code)]
    return _apply_discounts(subtotals, discounts, [True] * len(discounts), which)


def _selection_breakdown(
    tournament: Tournament,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    which: PriceColumn,
    team_disciplines: Sequence[Discipline] = (),
    code: DiscountCode | None = None,
) -> tuple[int, list[DiscountOutcome]]:
    """Either pricing world's total and outcomes, the code's last."""
    if uses_itemized_pricing(tournament):
        return _itemized_selection_breakdown(
            tournament, disciplines, extras, at, which, team_disciplines, code
        )
    return _legacy_selection_breakdown(
        tournament, disciplines, weapon_rentals, afterparty, at, which, team_disciplines, code
    )


def unpriced_rentals(tournament: Tournament, names: list[str]) -> list[str]:
    """The borrowed items in `names` this tournament lends nothing by that name.

    On a tournament that prices by items, a rental is billed through the item
    it names; a name matching none of them is billed nothing at all. The
    console states those names on the row rather than leaving the organizer to
    find a total that is quietly short (owner decision, 2026-09-06).

    Empty on a tournament priced the older way, where a rental is billed by the
    flat rental fee whatever it is called, so there is nothing for a name to
    fail to match.
    """
    if not uses_itemized_pricing(tournament):
        return []
    lent = {item.name for item in tournament.extra_items if item.category == ExtraCategory.RENTAL}
    return [name for name in names if name not in lent]


def selection_total(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    which: PriceColumn = "local",
    team_disciplines: Sequence[Discipline] = (),
    code: DiscountCode | None = None,
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
    total, _ = _selection_breakdown(
        tournament,
        disciplines,
        extras,
        weapon_rentals,
        afterparty,
        at,
        which,
        team_disciplines,
        code,
    )
    return total


def selection_totals(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    team_disciplines: Sequence[Discipline] = (),
    code: DiscountCode | None = None,
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
        code=code,
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
            code=code,
        )
    return Totals(local=local, eur=eur)


def _breakdowns(
    tournament: Tournament,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    team_disciplines: Sequence[Discipline],
    code: DiscountCode | None,
) -> list[DiscountBreakdown]:
    """One breakdown per discount of the selection, the code's last, read from
    the passes that price it. A fixed effect's deduction is read from its own
    currency's pass — local always, EUR only when the tournament shows one
    (design Decision 3); a percentage effect carries one currency-neutral
    figure, read from the local pass, since its condition can never differ
    between currencies."""

    def outcomes(which: PriceColumn) -> list[DiscountOutcome]:
        return _selection_breakdown(
            tournament,
            disciplines,
            extras,
            weapon_rentals,
            afterparty,
            at,
            which,
            team_disciplines,
            code,
        )[1]

    local_outcomes = outcomes("local")
    eur_outcomes = outcomes("eur") if tournament.shows_eur else None

    breakdown = []
    for i, outcome in enumerate(local_outcomes):
        is_fixed = outcome.effect.get("kind") == "fixed"
        deducted_eur = (
            eur_outcomes[i].deducted if outcome.applied and is_fixed and eur_outcomes else None
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


def selection_discounts(
    tournament: Tournament,
    *,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    at: datetime.date,
    team_disciplines: Sequence[Discipline] = (),
    code: DiscountCode | None = None,
) -> list[DiscountBreakdown]:
    """The per-discount breakdown for a selection, in configured order,
    reporting exactly what `selection_totals` applied rather than a separate
    evaluation. Empty for a legacy tournament or one with no discounts, and
    never holding the code, which `selection_code` reports: the code is passed
    only because a percentage evaluated after it deducts from what it left."""
    configured = len(tournament.discounts or [])
    if not configured:
        return []
    return _breakdowns(tournament, disciplines, extras, [], False, at, team_disciplines, code)[
        :configured
    ]


def selection_code(
    tournament: Tournament,
    *,
    code: DiscountCode,
    disciplines: list[Discipline],
    extras: list[tuple[ExtraItem, int]],
    weapon_rentals: list[str],
    afterparty: bool,
    at: datetime.date,
    team_disciplines: Sequence[Discipline] = (),
) -> DiscountBreakdown:
    """What the code took from a selection. A selection with nothing active is
    billed nothing, extras included (`selection_total`), so nothing was taken
    from it."""
    if not disciplines and not team_disciplines:
        return DiscountBreakdown(
            code.name,
            code.effect,
            True,
            0,
            0 if tournament.shows_eur and code.effect.get("kind") == "fixed" else None,
        )
    return _breakdowns(
        tournament, disciplines, extras, weapon_rentals, afterparty, at, team_disciplines, code
    )[-1]


def _registration_selection(
    registration: Registration,
) -> tuple[list[Discipline], list[tuple[ExtraItem, int]], list[Discipline]]:
    """What a persisted registration holds, in the shape the selection
    functions price. Waitlisted teams are excluded exactly as substitute
    discipline entries are (design team-disciplines D3)."""
    return (
        [e.discipline for e in registration.entries if not e.is_substitute],
        [(s.item, s.qty) for s in registration.extra_selections],
        [t.discipline for t in registration.teams if not t.waitlisted],
    )


def priced_on(registration: Registration, tournament: Tournament) -> datetime.date:
    """The day a persisted registration is priced by: the moment it was made,
    read where the tournament is held.

    Every date-valued price threshold — the legacy early-bird date and the
    `registered on or before` discount condition — is a date the organizer
    entered, so the early price runs to the end of that day there and no
    further. Reading the UTC day of `registered_at` instead gave the early
    price to a registration made in the first hours of the following local
    morning (design unify-day-boundary-clocks D5).

    SQLite drops tzinfo on round-trip even for a DateTime(timezone=True)
    column; every stored instant is UTC (matching.within_expiry_grace)."""
    made = registration.registered_at
    if made.tzinfo is None:
        made = made.replace(tzinfo=datetime.UTC)
    return local_date(tournament, made)


def registration_discounts(
    registration: Registration, tournament: Tournament
) -> list[DiscountBreakdown]:
    """The per-discount breakdown behind a persisted registration's stored
    total — the same selection `registration_total` priced, evaluated at the
    same date, so the two can never disagree about what applied."""
    active, extras, team_disciplines = _registration_selection(registration)
    return selection_discounts(
        tournament,
        disciplines=active,
        extras=extras,
        at=priced_on(registration, tournament),
        team_disciplines=team_disciplines,
        code=registration.discount_code,
    )


def registration_code(
    registration: Registration, tournament: Tournament
) -> DiscountBreakdown | None:
    """What the registration's code took off its stored total, or None where it
    carries none."""
    code = registration.discount_code
    if code is None:
        return None
    active, extras, team_disciplines = _registration_selection(registration)
    return selection_code(
        tournament,
        code=code,
        disciplines=active,
        extras=extras,
        weapon_rentals=registration.weapon_rentals,
        afterparty=registration.afterparty,
        at=priced_on(registration, tournament),
        team_disciplines=team_disciplines,
    )


class PricedPiece(NamedTuple):
    """Pieces of one thing a registration is billed for, at one unit price, in
    the local currency.

    `subject` is the discipline (an individual entry, or one team entered in a
    team discipline) or the extra item. It is None on a legacy tournament's
    flat-fee rental or afterparty, which bills no item; `category` then says
    which of the two it is."""

    category: str
    subject: Discipline | ExtraItem | None
    unit_price: int
    qty: int


class CategoryDeduction(NamedTuple):
    """What one configured discount took from one category of a registration,
    in whole local-currency units. `position` is the discount's place in the
    tournament's configured list, which is what tells two discounts apart.
    `code_id` is set instead where the deduction is a discount code's, which
    has no place in that list."""

    position: int
    category: str
    deducted: int
    code_id: int | None = None


class Breakdown(NamedTuple):
    pieces: list[PricedPiece]
    deductions: list[CategoryDeduction]


def _whole_deductions(
    outcomes: list[DiscountOutcome], target: int, code: DiscountCode | None = None
) -> list[CategoryDeduction]:
    """The per-category deductions in whole units, summing to `target`.

    A percentage leaves fractions in each category it reaches, and the total is
    rounded once, at the end. Rounding each fraction on its own could leave the
    lines a unit away from the total they explain, so the units are handed out
    by largest remainder: every cell is floored, and the units still missing go
    to the cells whose fractions were largest, earliest first on a tie.

    With a `code`, the last outcome is that code's."""
    cells = [
        (index, category, amount)
        for index, outcome in enumerate(outcomes)
        if outcome.applied
        for category, amount in outcome.by_category.items()
    ]
    floors = [int(amount) for _, _, amount in cells]
    missing = target - sum(floors)
    by_fraction = sorted(
        range(len(cells)), key=lambda cell: cells[cell][2] - floors[cell], reverse=True
    )
    for cell in by_fraction[: max(missing, 0)]:
        floors[cell] += 1
    code_at = len(outcomes) - 1 if code is not None else None
    return [
        CategoryDeduction(
            index, category, whole, code.id if code is not None and index == code_at else None
        )
        for (index, category, _), whole in zip(cells, floors, strict=True)
        if whole
    ]


def registration_breakdown(registration: Registration, tournament: Tournament) -> Breakdown:
    """What a persisted registration's local total is made of: the pieces it is
    billed for at their unit prices, and what each discount took from each
    category — evaluated at `priced_on`, over the selection
    `registration_total` prices, so that the pieces less the deductions are its
    local total.

    Local lane only: a line of the revenue values every registration at its
    local price, whatever lane it settled in (design export-revenue D4).

    Empty where the registration is billed nothing — every placement it holds
    sits in a queue, so its extras are not billed either."""
    active, extras, team_disciplines = _registration_selection(registration)
    if not active and not team_disciplines:
        return Breakdown([], [])
    at = priced_on(registration, tournament)
    pieces = [
        PricedPiece(DISCIPLINE_CATEGORY, d, discipline_fee(tournament, d, at), 1)
        for d in [*active, *team_disciplines]
    ]
    if uses_itemized_pricing(tournament):
        pieces += [
            PricedPiece(item.category.value, item, item.price or 0, qty) for item, qty in extras
        ]
    else:
        if registration.weapon_rentals:
            fee = weapon_rental_fee(tournament, at)
            pieces.append(PricedPiece(LEGACY_RENTAL, None, fee, len(registration.weapon_rentals)))
        if registration.afterparty:
            pieces.append(PricedPiece(LEGACY_AFTERPARTY, None, afterparty_fee(tournament, at), 1))
    code = registration.discount_code
    total, outcomes = _selection_breakdown(
        tournament,
        active,
        extras,
        registration.weapon_rentals,
        registration.afterparty,
        at,
        "local",
        team_disciplines,
        code,
    )
    gross = sum(piece.unit_price * piece.qty for piece in pieces)
    return Breakdown(pieces, _whole_deductions(outcomes, gross - total, code))


def registration_total(registration: Registration, tournament: Tournament) -> Totals:
    """Amount(s) due now for a persisted registration; delegates to
    `selection_totals`."""
    active, extras, team_disciplines = _registration_selection(registration)
    return selection_totals(
        tournament,
        disciplines=active,
        extras=extras,
        weapon_rentals=registration.weapon_rentals,
        afterparty=registration.afterparty,
        at=priced_on(registration, tournament),
        team_disciplines=team_disciplines,
        code=registration.discount_code,
    )


def claim_applies(registration: Registration, tournament: Tournament) -> bool:
    """Whether this registration has a claim: the tournament lets paying
    substitutes take free places, the registration waits wholly in the queue
    with at least one individual placement, and its clocks run — a dormant
    registration is offered nothing and seated by nothing (spec seating-queue,
    A paying substitute takes free places)."""
    if not (
        tournament.queue_payment_seats
        and bool(registration.entries)
        and registration.waiting_in_queue
        and clocks_run(tournament, registration)
    ):
        return False
    # a code that covers the claim leaves nothing to pay, so there is no payment
    # to take a place with: the registration waits for the organizer, as one on
    # a tournament without paying substitutes does
    if registration.discount_code is None:
        return True
    claim = claim_totals(registration, tournament)
    return claim.local > 0 and claim.eur != 0


def claim_totals(registration: Registration, tournament: Tournament) -> Totals:
    """What the registration would be priced at with every queued individual
    placement seated, at its own frozen prices. Its waitlisted teams are not
    part of it and stay waitlisted."""
    _active, extras, team_disciplines = _registration_selection(registration)
    return selection_totals(
        tournament,
        disciplines=[entry.discipline for entry in registration.entries],
        extras=extras,
        weapon_rentals=registration.weapon_rentals,
        afterparty=registration.afterparty,
        at=priced_on(registration, tournament),
        team_disciplines=team_disciplines,
        code=registration.discount_code,
    )


def _code_covers(registration: Registration, tournament: Tournament) -> bool:
    """Whether the registration's code brought a lane's total to zero. Either
    lane will do: the fencer chooses the lane, and one at zero leaves them
    owing nothing (design add-discount-codes D4)."""
    code = registration.discount_code
    active, extras, team_disciplines = _registration_selection(registration)
    if code is None or (not active and not team_disciplines):
        return False
    lanes: list[PriceColumn] = ["local", "eur"] if tournament.shows_eur else ["local"]
    for which in lanes:
        total, outcomes = _selection_breakdown(
            tournament,
            active,
            extras,
            registration.weapon_rentals,
            registration.afterparty,
            priced_on(registration, tournament),
            which,
            team_disciplines,
            code,
        )
        if total == 0 and outcomes[-1].deducted > 0:
            return True
    return False


def reprice(registration: Registration, tournament: Tournament) -> None:
    """Recompute and store the registration's totals, and its claim beside
    them — every place that reprices a registration does it through this, so
    the claim a fencer is told is never older than the totals it stands beside
    (design paying-substitutes D1)."""
    totals = registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    registration.code_covered = _code_covers(registration, tournament)
    if claim_applies(registration, tournament):
        claim = claim_totals(registration, tournament)
        registration.claim_total = claim.local
        registration.claim_total_eur = claim.eur
    else:
        registration.claim_total = None
        registration.claim_total_eur = None


def ensure_claim(registration: Registration, tournament: Tournament) -> bool:
    """Store the registration's claim where it applies and none is stored yet —
    the setting was turned on after it was last repriced — and say whether it
    has one. A claim is only ever computed when it is read or repriced, so
    turning the setting on needs no backfill (design paying-substitutes D1)."""
    if not claim_applies(registration, tournament):
        return False
    if registration.claim_total is None:
        claim = claim_totals(registration, tournament)
        registration.claim_total = claim.local
        registration.claim_total_eur = claim.eur
    return True


def claim_outstanding_cents(registration: Registration, which: str) -> int | None:
    """What is still to pay of the claim in one lane, in cents: the stored claim
    less what that lane has been credited (a forfeited deposit counts). None
    where the lane has no claim."""
    total = registration.claim_total if which == "local" else registration.claim_total_eur
    if total is None:
        return None
    return total * 100 - registration.credited_in(which)
