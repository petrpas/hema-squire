"""Unit tests for the setup-completeness helper."""

from datetime import date

from app.models import Currency, Discipline, ExtraCategory, ExtraItem, Tournament
from app.setup import setup_missing


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        location="Brno",
        organizers=[{"name": "Duelanti od sv. Rocha", "link": None}],
        vs_year=2026,
        vs_series=1,
    )
    tournament = Tournament(**{**defaults, **kwargs})
    if "disciplines" not in kwargs:
        tournament.disciplines = [
            Discipline(tournament=tournament, code="LS", name="LS", capacity=32, fee=800)
        ]
    return tournament


def test_complete_setup_has_nothing_missing():
    assert setup_missing(make_tournament()) == []


def test_each_mandatory_item_reported():
    assert setup_missing(make_tournament(location=None)) == ["location"]
    assert setup_missing(make_tournament(location="  ")) == ["location"]
    assert setup_missing(make_tournament(organizers=[])) == ["organizers"]
    assert setup_missing(make_tournament(disciplines=[])) == ["disciplines"]


def test_unpriced_discipline_blocks():
    tournament = make_tournament()
    tournament.disciplines[0].fee = None
    assert setup_missing(tournament) == ["discipline_prices"]


def test_multiple_gaps_accumulate():
    tournament = make_tournament(location=None, organizers=[], disciplines=[])
    assert setup_missing(tournament) == ["location", "organizers", "disciplines"]


def test_eur_payments_without_a_rate_is_fine():
    """eur_rate is a Setup convenience only; completeness never requires it."""
    tournament = make_tournament(eur_payments_enabled=True)
    tournament.disciplines[0].fee_eur = 32
    assert setup_missing(tournament) == []


def test_eur_enabled_with_missing_eur_price_blocks():
    tournament = make_tournament(eur_payments_enabled=True)
    assert setup_missing(tournament) == ["discipline_prices"]


def test_eur_priced_tournament_needs_no_second_price():
    tournament = make_tournament(local_currency=Currency.EUR, eur_payments_enabled=True)
    assert setup_missing(tournament) == []


def test_eur_enabled_extra_item_missing_eur_price_blocks():
    tournament = make_tournament(eur_payments_enabled=True)
    tournament.disciplines[0].fee_eur = 32
    tournament.extra_items = [
        ExtraItem(
            tournament=tournament, name="t-shirt", category=ExtraCategory.MERCH, price=300
        )
    ]
    assert setup_missing(tournament) == ["extra_item_prices"]


def test_eur_enabled_extra_item_with_eur_price_is_complete():
    tournament = make_tournament(eur_payments_enabled=True)
    tournament.disciplines[0].fee_eur = 32
    tournament.extra_items = [
        ExtraItem(
            tournament=tournament,
            name="t-shirt",
            category=ExtraCategory.MERCH,
            price=300,
            price_eur=12,
        )
    ]
    assert setup_missing(tournament) == []


def test_eur_enabled_fixed_discount_missing_eur_amount_blocks():
    tournament = make_tournament(
        eur_payments_enabled=True,
        discounts=[
            {
                "name": "early",
                "condition": {"kind": "discipline_count", "count": 1},
                "effect": {"kind": "fixed", "value": 200},
                "scope": ["discipline"],
            }
        ],
    )
    tournament.disciplines[0].fee_eur = 32
    assert setup_missing(tournament) == ["discount_prices"]


def test_eur_enabled_percent_discount_needs_no_eur_amount():
    tournament = make_tournament(
        eur_payments_enabled=True,
        discounts=[
            {
                "name": "early",
                "condition": {"kind": "discipline_count", "count": 1},
                "effect": {"kind": "percent", "value": 15},
                "scope": ["discipline"],
            }
        ],
    )
    tournament.disciplines[0].fee_eur = 32
    assert setup_missing(tournament) == []


def test_legacy_fixed_fees_block_eur():
    tournament = make_tournament(eur_payments_enabled=True, weapon_rental_fee=50)
    tournament.disciplines[0].fee_eur = 32
    assert setup_missing(tournament) == ["legacy_fixed_fees_block_eur"]


def test_legacy_fixed_fees_do_not_block_single_currency():
    tournament = make_tournament(weapon_rental_fee=50)
    assert setup_missing(tournament) == []


def test_currency_untouched_tournament_is_complete():
    """The default combination must never appear in the checklist."""
    assert setup_missing(make_tournament()) == []
