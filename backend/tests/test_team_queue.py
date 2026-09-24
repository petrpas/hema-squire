"""The team waitlist in the Queue phase (spec seating-queue, The team waitlist in
the Queue phase; team-disciplines): an organizer admits a waitlisted team into a
free slot and returns an unpaid one, on the same money and mail terms as an
individual promotion, and only teams on live registrations are listed or counted."""

import datetime
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

from app.mail import get_mailer
from app.main import app
from app.models import Registration, RegistrationState, Team
from tests.conftest import pay_registration
from tests.test_demotion import CollectingMailer, db_session, make_cup


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def cup(client, organizer, *, slots=1, mode="immediate"):
    make_cup(client, organizer, mode=mode, capacities={"LS": 5})
    response = client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "LS-T",
            "weapon": "LS",
            "kind": "team",
            "team_min": 1,
            "team_max": 3,
            "capacity": slots,
            "fee": 3000,
        },
        headers=organizer,
    )
    assert response.status_code == 201, response.text


def enter(client, auth_headers, name, disciplines=("LS",)):
    fencer = auth_headers(email=f"{name.lower()}@example.com", name=name)
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines), "teams": [{"slug": "LS-T", "name": name}]},
        headers=fencer,
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def team_of(vs) -> Team:
    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    return registration.teams[0]


def admit(client, organizer, vs, expect=200):
    team = team_of(vs)
    response = client.post(
        f"/api/tournaments/cup/registrations/{team.registration_id}/teams/{team.id}/admit",
        headers=organizer,
    )
    assert response.status_code == expect, response.text
    return response.json()


def give_back(client, organizer, vs, expect=200):
    team = team_of(vs)
    response = client.post(
        f"/api/tournaments/cup/registrations/{team.registration_id}/teams/{team.id}"
        "/return-to-waitlist",
        headers=organizer,
    )
    assert response.status_code == expect, response.text
    return response.json()


def roster(client, organizer):
    response = client.get("/api/tournaments/cup/queue/teams/LS-T", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()


def test_an_admitted_team_is_billed_and_its_entrant_told(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, slots=2)
    enter(client, auth_headers, "First")
    enter(client, auth_headers, "Second")
    _, vs = enter(client, auth_headers, "Third")
    assert team_of(vs).waitlisted
    # the second slot frees
    db = db_session()
    second = db.scalar(
        select(Registration).where(Registration.vs != vs).order_by(Registration.id.desc())
    )
    assert second is not None
    second.state = RegistrationState.CANCELLED
    db.commit()
    summary = client.get("/api/tournaments/cup/queue", headers=organizer).json()
    (slots,) = summary["team_disciplines"]
    assert (slots["taken"], slots["free"], slots["queued"]) == (1, 1, 1)
    mailbox.sent.clear()

    body = admit(client, organizer, vs)

    assert body["total_amount"] == 4000
    assert body["expires_at"] is not None
    team = team_of(vs)
    assert not team.waitlisted and team.promoted_unpaid
    (notice,) = mailbox.sent
    assert "tým Third" in notice.get_body(("plain",)).get_content()


def test_no_slot_refuses_the_admission(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer)
    enter(client, auth_headers, "First")
    _, vs = enter(client, auth_headers, "Second")

    refused = admit(client, organizer, vs, expect=409)

    assert refused["detail"] == "team_discipline_full"
    assert team_of(vs).waitlisted


def test_a_paid_registration_keeps_its_team(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer)
    _, vs = enter(client, auth_headers, "First")
    db = db_session()
    pay_registration(db, db.scalar(select(Registration).where(Registration.vs == vs)))

    refused = give_back(client, organizer, vs, expect=409)

    assert refused["detail"] == "registration_paid_cancel_instead"
    assert not team_of(vs).waitlisted


def test_an_unpaid_team_returned_keeps_its_moment(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer)
    _, vs = enter(client, auth_headers, "First")
    moment = team_of(vs).waitlisted_since
    mailbox.sent.clear()

    body = give_back(client, organizer, vs)

    team = team_of(vs)
    assert team.waitlisted and team.waitlisted_since == moment
    assert body["total_amount"] == 1000
    assert mailbox.sent == []


def test_a_lapsed_team_admission_takes_back_the_team_alone(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer)
    holder, _ = enter(client, auth_headers, "Holder")
    _, vs = enter(client, auth_headers, "Paid")
    db = db_session()
    pay_registration(db, db.scalar(select(Registration).where(Registration.vs == vs)))
    client.post("/api/tournaments/cup/my-registration/cancel", headers=holder)
    admit(client, organizer, vs)
    db = db_session()
    registration = db.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    registration.expires_at = datetime.datetime.now(UTC) - timedelta(hours=1)
    db.commit()

    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    kept = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert kept is not None
    assert kept.state is RegistrationState.RESERVED
    assert [e.is_substitute for e in kept.entries] == [False]
    assert kept.teams[0].waitlisted
    assert kept.settled


def test_a_dead_registrations_team_is_neither_listed_nor_counted(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer)
    enter(client, auth_headers, "Seated")
    _, gone = enter(client, auth_headers, "Gone")
    _, waiting = enter(client, auth_headers, "Waiting")
    db = db_session()
    expired = db.scalar(select(Registration).where(Registration.vs == gone))
    assert expired is not None
    expired.state = RegistrationState.EXPIRED
    db.commit()

    rows = roster(client, organizer)

    assert [(row["name"], row["waitlist_position"]) for row in rows] == [
        ("Seated", None),
        ("Waiting", 1),
    ]
    teams = client.get("/api/tournaments/cup/teams", headers=organizer).json()
    listed = [(t["name"], t["waitlist_position"]) for t in teams[0]["teams"]]
    assert listed == [("Seated", None), ("Waiting", 1)]
    assert rows[1]["demoted"] is False
    assert team_of(waiting).waitlisted
