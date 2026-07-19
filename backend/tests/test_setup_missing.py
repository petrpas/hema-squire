"""Unit tests for the setup-completeness helper."""

from datetime import date

from app.models import Discipline, Tournament
from app.setup import setup_missing


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        location="Brno",
        organizer_names=["Duelanti od sv. Rocha"],
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
    assert setup_missing(make_tournament(organizer_names=[])) == ["organizers"]
    assert setup_missing(make_tournament(disciplines=[])) == ["disciplines"]


def test_unpriced_discipline_blocks():
    tournament = make_tournament()
    tournament.disciplines[0].fee = None
    assert setup_missing(tournament) == ["discipline_prices"]


def test_multiple_gaps_accumulate():
    tournament = make_tournament(location=None, organizer_names=[], disciplines=[])
    assert setup_missing(tournament) == ["location", "organizers", "disciplines"]
