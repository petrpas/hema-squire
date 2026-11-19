"""Teams gone with their registrations stay in the organizer's sight (spec
team-disciplines, Organizer's teams view; seating-queue, The team waitlist in
the Queue phase) and their fighters leave the start field (etl-console, The
fencer list is the tournament's start field)."""

import datetime
from datetime import UTC, timedelta

from sqlalchemy import select

from app.models import PaymentEvent, Registration, RegistrationState
from tests.conftest import credit_registration
from tests.test_demotion import db_session
from tests.test_team_disciplines import set_roster, sheet_rows
from tests.test_team_queue import cup, enter, mailbox, roster, team_of

__all__ = ["mailbox"]  # the fixture, re-exported so pytest finds it here


def lapse(client, organizer, vs, *, hours_ago=1):
    """Let a reservation's window run out and the lifecycle expire it, as the
    scheduler would."""
    db = db_session()
    registration = db.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    registration.expires_at = datetime.datetime.now(UTC) - timedelta(hours=hours_ago)
    db.commit()
    response = client.post("/api/tournaments/cup/payments/process", headers=organizer)
    assert response.status_code == 200, response.text


def teams_view(client, organizer):
    response = client.get("/api/tournaments/cup/teams", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()[0]


def queue_lapsed(client, organizer):
    response = client.get("/api/tournaments/cup/queue/teams/LS-T/lapsed", headers=organizer)
    assert response.status_code == 200, response.text
    return response.json()


def test_lapsed_teams_are_listed_apart_and_hold_no_place(client, auth_headers, mailbox):
    organizer = auth_headers()
    # two slots: Seated and Gone take them, Quitter and Waiting wait. A
    # waitlisted team is demoted rather than expired, so the one that expires
    # is seated
    cup(client, organizer, slots=2)
    enter(client, auth_headers, "Seated")
    _, gone = enter(client, auth_headers, "Gone")
    quitter, _ = enter(client, auth_headers, "Quitter")
    _, waiting = enter(client, auth_headers, "Waiting")
    client.post("/api/tournaments/cup/my-registration/cancel", headers=quitter)
    # the cancellation a day back, so the expiry after it is legibly later
    db = db_session()
    cancelled = db.scalar(
        select(Registration).where(Registration.state == RegistrationState.CANCELLED)
    )
    assert cancelled is not None and cancelled.cancelled_at is not None
    cancelled.cancelled_at = cancelled.cancelled_at - timedelta(days=1)
    db.commit()
    lapse(client, organizer, gone)

    view = teams_view(client, organizer)
    assert [(t["name"], t["waitlist_position"]) for t in view["teams"]] == [
        ("Seated", None),
        ("Waiting", 1),
    ]
    # the latest lapse first: the expiry ran after the cancellation
    assert [(t["name"], t["reason"]) for t in view["lapsed"]] == [
        ("Gone", "expired"),
        ("Quitter", "cancelled"),
    ]
    assert all(t["lapsed_at"] is not None for t in view["lapsed"])

    rows = roster(client, organizer)
    assert [(r["name"], r["waitlist_position"]) for r in rows] == [
        ("Seated", None),
        ("Waiting", 1),
    ]
    assert [t["name"] for t in queue_lapsed(client, organizer)] == ["Gone", "Quitter"]
    assert team_of(waiting).waitlisted


def test_the_moment_is_the_latest_expiry(client, auth_headers, mailbox):
    """Reinstated by a late payment and expired again, the team lapsed the
    second time (design show-lapsed-teams D2)."""
    organizer = auth_headers()
    cup(client, organizer, slots=2)
    _, vs = enter(client, auth_headers, "Twice")
    lapse(client, organizer, vs)
    # the first expiry an hour back, so the second is legibly later
    db = db_session()
    for event in db.scalars(select(PaymentEvent).where(PaymentEvent.kind == "reservation_expired")):
        event.created_at = event.created_at - timedelta(hours=1)
    db.commit()
    first = teams_view(client, organizer)["lapsed"][0]["lapsed_at"]

    db = db_session()
    registration = db.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    registration.state = RegistrationState.RESERVED
    db.commit()
    assert teams_view(client, organizer)["lapsed"] == []
    lapse(client, organizer, vs)

    again = teams_view(client, organizer)["lapsed"]
    assert len(again) == 1
    assert again[0]["lapsed_at"] > first


def test_an_expiry_without_an_event_reads_its_window(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, slots=2)
    _, vs = enter(client, auth_headers, "Quiet")
    db = db_session()
    registration = db.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    ended = datetime.datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    registration.expires_at = ended
    registration.state = RegistrationState.EXPIRED
    db.commit()

    lapsed = teams_view(client, organizer)["lapsed"]
    assert [t["reason"] for t in lapsed] == ["expired"]
    assert datetime.datetime.fromisoformat(lapsed[0]["lapsed_at"]) == ended


def test_money_still_held_is_stated(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, slots=2)
    _, vs = enter(client, auth_headers, "Partial")
    db = db_session()
    registration = db.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    credit_registration(db, registration, 50000)
    db.commit()
    lapse(client, organizer, vs)

    [team] = teams_view(client, organizer)["lapsed"]
    assert team["held_amount"] == "500.00"
    assert team["held_currency"] == "CZK"


def test_a_lapsed_teams_fighters_leave_the_start_field(client, auth_headers, mailbox):
    organizer = auth_headers()
    cup(client, organizer, slots=2)
    fencer, vs = enter(client, auth_headers, "Entrant")
    set_roster(client, fencer, team_of(vs).id, ["Member One", "Member Two"])
    before = sheet_rows(client, organizer)
    numbers = {name: before[name]["number"] for name in ("Member One", "Member Two")}

    lapse(client, organizer, vs)
    rows = sheet_rows(client, organizer)
    assert "Member One" not in rows
    assert "Member Two" not in rows
    assert rows["Entrant"]["state"] == "expired"

    # reinstated, the fighters return under the numbers they held
    db = db_session()
    registration = db.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    registration.state = RegistrationState.RESERVED
    db.commit()
    back = sheet_rows(client, organizer)
    assert {name: back[name]["number"] for name in numbers} == numbers
