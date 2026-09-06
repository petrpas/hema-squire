from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    Discipline,
    Fencer,
    Registration,
    Tournament,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="na-duel-2026",
        display_name="Na Duel!",
        date=date(2026, 10, 3),
        vs_year=2026,
        vs_series=1,
    )
    return Tournament(**{**defaults, **kwargs})



def test_hr_id_not_unique_across_accounts(session):
    """Claims are non-exclusive (design D3): multiple accounts may share an hr_id."""
    session.add(Fencer(email="a@example.com", display_name="A", hr_id=7))
    session.add(Fencer(email="b@example.com", display_name="B", hr_id=7))
    session.commit()


def test_vs_unique(session):
    tournament = make_tournament()
    fencer_a = Fencer(email="a@example.com", display_name="A")
    fencer_b = Fencer(email="b@example.com", display_name="B")
    session.add(Registration(tournament=tournament, fencer=fencer_a, vs=1))
    session.add(Registration(tournament=tournament, fencer=fencer_b, vs=1))
    with pytest.raises(IntegrityError):
        session.commit()


def test_one_registration_per_fencer_per_tournament(session):
    tournament = make_tournament()
    fencer = Fencer(email="a@example.com", display_name="A")
    session.add(Registration(tournament=tournament, fencer=fencer, vs=1))
    session.add(Registration(tournament=tournament, fencer=fencer, vs=2))
    with pytest.raises(IntegrityError):
        session.commit()


def test_discipline_slug_unique_per_tournament_only(session):
    first = make_tournament()
    second = make_tournament(slug="jindra-cup-2026", display_name="Jindra Cup", vs_series=2)
    session.add(
        Discipline(
            tournament=first, slug="LS", name="Longsword",
            weapon="LS", gender="", material="", capacity=32, fee=800,
        )
    )
    session.add(
        Discipline(
            tournament=second, slug="LS", name="Longsword",
            weapon="LS", gender="", material="", capacity=16, fee=500,
        )
    )
    session.commit()

    session.add(
        Discipline(
            tournament=first, slug="LS", name="Duplicate",
            weapon="LS", gender="", material="", capacity=8, fee=100,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
