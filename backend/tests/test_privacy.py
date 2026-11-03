"""The account's own data and the organizer data terms (spec privacy): the
export holds what is the account's and nothing that is someone else's or a
credential; the terms are due from an owner, once per version."""

import datetime
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import privacy
from app.models import (
    BankTransaction,
    Discipline,
    Fencer,
    FencerProfileAudit,
    Registration,
    Role,
    Team,
    TeamMember,
)
from tests.conftest import credit_registration, enable_payments, publish

PAYER = "Cizí Plátce"
PAYER_ACCOUNT = "123456789/0800"
TEAMMATE = "Tomáš Spoluhráč"


def make_cup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")


def test_the_export_holds_the_accounts_own_data_and_nobody_elses(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="me@example.com", name="Petra Mine", role=Role.FENCER)
    other = auth_headers(email="other@example.com", name="Olga Other", role=Role.FENCER)
    client.patch("/api/account", json={"club": "Klub A"}, headers=me)
    client.patch("/api/account", json={"club": "Klub Jiný"}, headers=other)
    for headers in (me, other):
        response = client.post(
            "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=headers
        )
        assert response.status_code == 201, response.text

    with Session(engine) as session:
        mine = session.scalars(
            select(Registration).join(Fencer).where(Fencer.email == "me@example.com")
        ).one()
        # paid by someone else, from their own account
        transaction = BankTransaction(
            tournament_id=mine.tournament_id,
            external_id="tx-1",
            source="csv",
            date=datetime.date(2099, 11, 1),
            amount_cents=80000,
            currency="CZK",
            vs=mine.vs,
            message=f"za {PAYER}",
            payer_name=PAYER,
            payer_account=PAYER_ACCOUNT,
        )
        session.add(transaction)
        session.flush()
        credit_registration(session, mine, 80000, source_id=transaction.id)
        longsword = session.scalars(select(Discipline)).one()
        discipline_name = longsword.name
        team = Team(
            tournament_id=mine.tournament_id,
            discipline_id=longsword.id,
            registration_id=mine.id,
            name="Vlci",
            waitlisted_since=datetime.datetime.now(datetime.UTC),
        )
        session.add(team)
        session.flush()
        session.add(TeamMember(team_id=team.id, ordinal=1, name=TEAMMATE))
        session.commit()

    response = client.get("/api/account/export", headers=me)
    assert response.status_code == 200, response.text
    data = response.json()
    raw = json.dumps(data, ensure_ascii=False)

    assert data["profile"]["display_name"] == "Petra Mine"
    assert [(a["field"], a["new_value"]) for a in data["profile"]["audit"]] == [("club", "Klub A")]
    (registration,) = data["registrations"]
    assert registration["tournament"] == "Cup"
    assert [d["discipline"] for d in registration["disciplines"]] == [discipline_name]
    assert [t["name"] for t in registration["teams"]] == ["Vlci"]
    assert [(c["amount_cents"], c["currency"]) for c in registration["credits"]] == [(80000, "CZK")]

    # another person's data, and anything that is a credential, stays out
    for absent in (PAYER, PAYER_ACCOUNT, TEAMMATE, "Olga Other", "Klub Jiný", "password", "scrypt"):
        assert absent not in raw, absent


def test_the_export_needs_an_account(client):
    assert client.get("/api/account/export").status_code == 401


def test_the_terms_are_due_from_an_owner_once_per_version(client, auth_headers, engine):
    owner = auth_headers()
    assert client.get("/api/account", headers=owner).json()["organizer_terms_due"] is False

    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=owner,
    )
    assert client.get("/api/account", headers=owner).json()["organizer_terms_due"] is True

    accepted = client.post("/api/account/organizer-terms", headers=owner)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["organizer_terms_due"] is False
    with Session(engine) as session:
        fencer = session.scalars(
            select(Fencer).where(Fencer.email == "organizer@example.com")
        ).one()
        assert fencer.organizer_terms_version == privacy.ORGANIZER_TERMS_VERSION
        assert fencer.organizer_terms_accepted_at is not None
        # a new version asks again
        fencer.organizer_terms_version = "2000-01-01"
        session.commit()
    assert client.get("/api/account", headers=owner).json()["organizer_terms_due"] is True


def test_a_team_member_owning_nothing_is_not_asked(client, auth_headers):
    owner = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2099-12-05"},
        headers=owner,
    )
    helper = auth_headers(email="helper@example.com", name="Helper")
    client.post("/api/tournaments/cup/team", json={"email": "helper@example.com"}, headers=owner)

    assert client.get("/api/account", headers=helper).json()["organizer_terms_due"] is False


def test_an_audit_entry_of_another_account_stays_out(client, auth_headers, engine):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    auth_headers(email="other@example.com", name="Other", role=Role.FENCER)
    with Session(engine) as session:
        other = session.scalars(select(Fencer).where(Fencer.email == "other@example.com")).one()
        session.add(
            FencerProfileAudit(fencer_id=other.id, field="club", old_value=None, new_value="Tajný")
        )
        session.commit()

    data = client.get("/api/account/export", headers=me).json()
    assert data["profile"]["audit"] == []
