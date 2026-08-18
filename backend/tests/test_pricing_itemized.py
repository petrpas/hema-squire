"""Unit tests for the itemized pricing engine (items + ordered scoped
discounts) and its dispatch against the legacy per-discipline path."""

from datetime import date, datetime

from app import pricing
from app.models import (
    Discipline,
    ExtraCategory,
    ExtraItem,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    Tournament,
)

REGISTERED_AT = datetime(2026, 5, 1, 12, 0)


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        discounts=[],
        organizers=[],
        vs_year=2026,
        vs_series=1,
    )
    return Tournament(**{**defaults, **kwargs})


def make_registration(tournament, fees, extras=(), registered_at=REGISTERED_AT):
    """Registration with one active entry per fee and given (item, qty) extras."""
    entries = [
        RegistrationDiscipline(
            discipline=Discipline(
                tournament=tournament, slug=f"D{i}", name=f"D{i}",
                weapon=f"D{i}", gender="", material="", capacity=10, fee=fee,
            ),
            is_substitute=False,
        )
        for i, fee in enumerate(fees)
    ]
    selections = [RegistrationExtra(item=item, qty=qty) for item, qty in extras]
    return Registration(
        tournament=tournament,
        registered_at=registered_at,
        entries=entries,
        extra_selections=selections,
        weapon_rentals=[],
    )


def count_discount(count, value):
    return {
        "name": f"{count} disciplines",
        "condition": {"kind": "discipline_count", "count": count},
        "effect": {"kind": "fixed", "value": value},
        "scope": ["discipline"],
    }


def early_percent(until, value, scope=("discipline",)):
    return {
        "name": "early bird",
        "condition": {"kind": "early", "until": until},
        "effect": {"kind": "percent", "value": value},
        "scope": list(scope),
    }


def rental_item(tournament, price=2, max_qty=4):
    return ExtraItem(
        tournament=tournament,
        name="weapon rental",
        category=ExtraCategory.RENTAL,
        price=price,
        max_qty=max_qty,
    )


def test_count_discount_applies_only_at_matching_count():
    tournament = make_tournament(discounts=[count_discount(2, 10)])
    two = make_registration(tournament, [30, 30])
    one = make_registration(tournament, [30])
    assert pricing.registration_total(two, tournament).local == 50
    assert pricing.registration_total(one, tournament).local == 30


def test_spec_scenario_fixed_then_percent_rounds_half_up():
    # (60 − 10) × 0.85 = 42.5 → 43 (the normative scenario from the spec)
    tournament = make_tournament(
        discounts=[count_discount(2, 10), early_percent("2026-06-01", 15)]
    )
    registration = make_registration(tournament, [30, 30])
    assert pricing.registration_total(registration, tournament).local == 43


def test_early_condition_expires():
    tournament = make_tournament(discounts=[early_percent("2026-04-30", 15)])
    registration = make_registration(tournament, [30, 30])  # registered 2026-05-01
    assert pricing.registration_total(registration, tournament).local == 60


def test_extra_quantity_billed():
    tournament = make_tournament()
    item = rental_item(tournament)
    tournament.extra_items = [item]
    registration = make_registration(tournament, [30], extras=[(item, 2)])
    assert pricing.registration_total(registration, tournament).local == 34


def test_percent_scope_leaves_other_categories_untouched():
    tournament = make_tournament()
    shirt = ExtraItem(
        tournament=tournament,
        name="t-shirt",
        category=ExtraCategory.MERCH,
        price=10,
        max_qty=2,
    )
    tournament.extra_items = [shirt]
    tournament.discounts = [early_percent("2026-06-01", 50, scope=("discipline",))]
    registration = make_registration(tournament, [30, 30], extras=[(shirt, 1)])
    assert pricing.registration_total(registration, tournament).local == 40  # 60/2 + 10


def test_fixed_discount_floors_at_zero_within_scope():
    tournament = make_tournament(discounts=[count_discount(1, 100)])
    item = rental_item(tournament, price=5)
    tournament.extra_items = [item]
    registration = make_registration(tournament, [30], extras=[(item, 1)])
    # discipline subtotal 30 floors at 0; rental 5 is outside the scope
    assert pricing.registration_total(registration, tournament).local == 5


def test_fixed_multi_scope_consumes_categories_in_canonical_order():
    tournament = make_tournament()
    item = rental_item(tournament, price=5)
    tournament.extra_items = [item]
    tournament.discounts = [
        {
            "name": "combo",
            "condition": {"kind": "discipline_count", "count": 1},
            "effect": {"kind": "fixed", "value": 32},
            "scope": ["discipline", "rental"],
        }
    ]
    registration = make_registration(tournament, [30], extras=[(item, 1)])
    # 32 eats all 30 discipline, then 2 of 5 rental → 3
    assert pricing.registration_total(registration, tournament).local == 3


def test_percent_discounts_stack_sequentially():
    tournament = make_tournament(
        discounts=[
            early_percent("2026-06-01", 10),
            early_percent("2026-06-01", 50),
        ]
    )
    registration = make_registration(tournament, [100])
    assert pricing.registration_total(registration, tournament).local == 45  # 100×0.9×0.5


def test_fully_queued_substitute_owes_nothing():
    tournament = make_tournament(discounts=[count_discount(1, 5)])
    registration = make_registration(tournament, [30])
    registration.entries[0].is_substitute = True
    assert pricing.registration_total(registration, tournament).local == 0


def test_count_condition_counts_active_entries_only():
    tournament = make_tournament(discounts=[count_discount(1, 5)])
    registration = make_registration(tournament, [30, 30])
    registration.entries[1].is_substitute = True
    assert pricing.registration_total(registration, tournament).local == 25


def test_generic_categories_price_and_scope_like_their_models():
    """other_action must total and discount-scope exactly as afterparty/seminar
    do, and other_item exactly as merch does (design D4)."""

    def total_for(action_category, item_category):
        tournament = make_tournament(
            discounts=[
                {
                    "name": "combo",
                    "condition": {"kind": "discipline_count", "count": 1},
                    "effect": {"kind": "percent", "value": 10},
                    "scope": [action_category, item_category],
                }
            ]
        )
        action = ExtraItem(
            tournament=tournament, name="action", category=action_category, price=15, max_qty=1
        )
        item = ExtraItem(
            tournament=tournament, name="item", category=item_category, price=15, max_qty=1
        )
        tournament.extra_items = [action, item]
        registration = make_registration(tournament, [30], extras=[(action, 1), (item, 1)])
        return pricing.registration_total(registration, tournament).local

    afterparty_and_merch = total_for(ExtraCategory.AFTERPARTY, ExtraCategory.MERCH)
    other_action_and_item = total_for(ExtraCategory.OTHER_ACTION, ExtraCategory.OTHER_ITEM)
    # discipline 30 (out of scope) + 15×0.9 + 15×0.9 = 57
    assert afterparty_and_merch == other_action_and_item == 57


def test_unpriced_discipline_counts_as_zero():
    tournament = make_tournament(discounts=[count_discount(2, 10)])
    registration = make_registration(tournament, [30, None])
    assert pricing.registration_total(registration, tournament).local == 20


def test_legacy_path_unchanged_without_items_or_discounts():
    tournament = make_tournament(
        early_bird_until=date(2026, 5, 15),
        weapon_rental_fee=100,
        weapon_rental_fee_early=80,
        afterparty_fee=250,
        afterparty_fee_early=None,
    )
    registration = make_registration(tournament, [800])
    registration.entries[0].discipline.fee_early = 700
    registration.weapon_rentals = ["LS", "SA"]
    registration.afterparty = True
    # early window active: 700 + 2×80 + 250
    assert pricing.registration_total(registration, tournament).local == 1110
    tournament.early_bird_until = None
    assert pricing.registration_total(registration, tournament).local == 1250


# --- 8.3 each currency totals independently, including fixed discounts -----


def test_eur_fixed_discount_and_percent_apply_per_currency():
    """A fixed discount carries an independent EUR amount; a percent effect
    is currency-neutral and applies identically to both totals (design
    Decision 1)."""
    tournament = make_tournament(
        local_currency="CZK",
        eur_payments_enabled=True,
        discounts=[
            {
                "name": "combo",
                "condition": {"kind": "discipline_count", "count": 2},
                "effect": {"kind": "fixed", "value": 200, "value_eur": 8},
                "scope": ["discipline"],
            },
            {
                "name": "early",
                "condition": {"kind": "discipline_count", "count": 2},
                "effect": {"kind": "percent", "value": 10},
                "scope": ["discipline"],
            },
        ],
    )
    registration = make_registration(tournament, [800, 700])
    registration.entries[0].discipline.fee_eur = 32
    registration.entries[1].discipline.fee_eur = 28

    totals = pricing.registration_total(registration, tournament)
    # local: (1500 - 200) × 0.9 = 1170; eur: (60 - 8) × 0.9 = 46.8 -> 47
    assert totals.local == 1170
    assert totals.eur == 47


def test_eur_extra_item_price_is_independent_of_local():
    tournament = make_tournament(local_currency="CZK", eur_payments_enabled=True)
    item = rental_item(tournament, price=100)
    item.price_eur = 3
    tournament.extra_items = [item]
    registration = make_registration(tournament, [800], extras=[(item, 2)])
    registration.entries[0].discipline.fee_eur = 32

    totals = pricing.registration_total(registration, tournament)
    assert totals.local == 1000  # 800 + 2×100
    assert totals.eur == 38  # 32 + 2×3


def test_no_eur_total_when_tournament_does_not_price_in_eur():
    tournament = make_tournament(discounts=[count_discount(2, 10)])
    registration = make_registration(tournament, [30, 30])
    totals = pricing.registration_total(registration, tournament)
    assert totals.local == 50
    assert totals.eur is None


# --- per-discount breakdown -------------------------------------------------


def test_breakdown_lists_applied_and_unapplied_in_configured_order():
    tournament = make_tournament(
        discounts=[count_discount(2, 10), count_discount(3, 20)]
    )
    breakdown = pricing.selection_discounts(
        tournament,
        disciplines=[Discipline(fee=30), Discipline(fee=30)],
        extras=[],
        at=REGISTERED_AT.date(),
    )
    assert [d.applied for d in breakdown] == [True, False]
    assert [d.name for d in breakdown] == ["2 disciplines", "3 disciplines"]
    assert breakdown[0].deducted == 10
    assert breakdown[1].deducted is None


def test_breakdown_reports_floored_fixed_deduction_as_taken():
    tournament = make_tournament(discounts=[count_discount(1, 100)])
    breakdown = pricing.selection_discounts(
        tournament, disciplines=[Discipline(fee=30)], extras=[], at=REGISTERED_AT.date()
    )
    assert breakdown[0].applied is True
    assert breakdown[0].deducted == 30


def test_breakdown_reports_percent_deduction_realized():
    tournament = make_tournament(discounts=[early_percent("2026-06-01", 15)])
    breakdown = pricing.selection_discounts(
        tournament, disciplines=[Discipline(fee=60)], extras=[], at=REGISTERED_AT.date()
    )
    assert breakdown[0].applied is True
    assert breakdown[0].deducted == 9  # 60 * 0.15


def test_breakdown_per_currency_deductions_read_from_their_own_pass():
    tournament = make_tournament(
        local_currency="CZK",
        eur_payments_enabled=True,
        discounts=[
            {
                "name": "combo",
                "condition": {"kind": "discipline_count", "count": 2},
                "effect": {"kind": "fixed", "value": 200, "value_eur": 8},
                "scope": ["discipline"],
            }
        ],
    )
    disciplines = [Discipline(fee=800, fee_eur=32), Discipline(fee=700, fee_eur=28)]
    breakdown = pricing.selection_discounts(
        tournament, disciplines=disciplines, extras=[], at=REGISTERED_AT.date()
    )
    assert breakdown[0].applied is True
    assert breakdown[0].deducted == 200
    assert breakdown[0].deducted_eur == 8


def test_breakdown_percent_deduction_carries_no_eur_figure():
    tournament = make_tournament(
        local_currency="CZK",
        eur_payments_enabled=True,
        discounts=[early_percent("2026-06-01", 10)],
    )
    disciplines = [Discipline(fee=100, fee_eur=4)]
    breakdown = pricing.selection_discounts(
        tournament, disciplines=disciplines, extras=[], at=REGISTERED_AT.date()
    )
    assert breakdown[0].applied is True
    assert breakdown[0].deducted == 10
    assert breakdown[0].deducted_eur is None


def test_breakdown_early_bird_applicability_judged_by_at_date():
    tournament = make_tournament(discounts=[early_percent("2026-04-30", 15)])
    breakdown = pricing.selection_discounts(
        tournament, disciplines=[Discipline(fee=60)], extras=[], at=REGISTERED_AT.date()
    )
    assert breakdown[0].applied is False
    assert breakdown[0].deducted is None


def test_breakdown_empty_for_legacy_tournament():
    tournament = make_tournament()
    breakdown = pricing.selection_discounts(
        tournament, disciplines=[Discipline(fee=30)], extras=[], at=REGISTERED_AT.date()
    )
    assert breakdown == []
