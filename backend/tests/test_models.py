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
    RegistrationDiscipline,
    RegistrationState,
    Tournament,
    UnpaidListTreatment,
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


def test_registration_roundtrip(session):
    tournament = make_tournament()
    discipline = Discipline(
        tournament=tournament, code="LS", name="Longsword Open Steel", capacity=32, fee=800
    )
    fencer = Fencer(email="jan@example.com", display_name="Jan Novák", hr_id=1234)
    registration = Registration(
        tournament=tournament, fencer=fencer, vs=26001, total_amount=800
    )
    session.add(RegistrationDiscipline(registration=registration, discipline=discipline))
    session.commit()

    saved = session.get(Registration, registration.id)
    assert saved.state == RegistrationState.RESERVED
    assert saved.fencer.hr_id == 1234
    assert [e.discipline.code for e in saved.entries] == ["LS"]
    assert saved.tournament.unpaid_list_treatment == UnpaidListTreatment.GREYED


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


def test_discipline_code_unique_per_tournament_only(session):
    first = make_tournament()
    second = make_tournament(slug="jindra-cup-2026", display_name="Jindra Cup", vs_series=2)
    session.add(Discipline(tournament=first, code="LS", name="Longsword", capacity=32, fee=800))
    session.add(Discipline(tournament=second, code="LS", name="Longsword", capacity=16, fee=500))
    session.commit()

    session.add(Discipline(tournament=first, code="LS", name="Duplicate", capacity=8, fee=100))
    with pytest.raises(IntegrityError):
        session.commit()
