"""Unit tests for the setup-completeness helper."""

from datetime import date
from decimal import Decimal

from app.models import Currency, Discipline, Tournament
from app.setup import setup_missing


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        location="Brno",
        organizers=[{"name": "Duelanti od sv. Rocha", "link": None}],
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


def test_eur_payments_without_a_rate_blocks():
    tournament = make_tournament(eur_payments_enabled=True)
    assert setup_missing(tournament) == ["eur_rate"]


def test_eur_payments_with_a_rate_is_complete():
    tournament = make_tournament(eur_payments_enabled=True, eur_rate=Decimal("25.5"))
    assert setup_missing(tournament) == []


def test_eur_priced_tournament_needs_no_rate():
    tournament = make_tournament(
        primary_currency=Currency.EUR, eur_payments_enabled=True, eur_rate=None
    )
    assert setup_missing(tournament) == []


def test_currency_untouched_tournament_is_complete():
    """The default combination must never appear in the checklist."""
    assert setup_missing(make_tournament()) == []
