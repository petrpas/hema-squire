"""The public aggregates a list entry states (spec public-browsing, A list
entry states its public aggregates): seated fencers counted once across
disciplines, clubs compared loosely, the queue left out, and the closing day
resolved as the registration gate resolves it."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fencer
from tests.conftest import publish, today_utc


def make_cup(client, organizer, **patch):
    date = today_utc() + timedelta(days=30)
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": str(date)},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}], **patch},
        headers=organizer,
    )
    for slug, capacity in (("LS", 2), ("SB", 5)):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": slug, "weapon": slug, "capacity": capacity, "fee": 500},
            headers=organizer,
        )
    publish(client, organizer, "cup")
    return date


def fencer_with_club(auth_headers, engine, email, club):
    headers = auth_headers(email=email, name=email.split("@")[0])
    with Session(engine) as session:
        fencer = session.scalars(select(Fencer).where(Fencer.email == email)).one()
        fencer.club = club
        session.commit()
    return headers


def cup_entry(client):
    return next(t for t in client.get("/api/tournaments/open").json() if t["slug"] == "cup")


def test_a_fencer_in_two_disciplines_counts_once(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    both = fencer_with_club(auth_headers, engine, "a@example.com", "Šermířský klub Brno")
    one = fencer_with_club(auth_headers, engine, "b@example.com", "sermirsky  KLUB brno ")
    other = fencer_with_club(auth_headers, engine, "c@example.com", None)
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS", "SB"]}, headers=both)
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=one)
    client.post("/api/tournaments/cup/register", json={"disciplines": ["SB"]}, headers=other)

    entry = cup_entry(client)
    assert (entry["entrant_count"], entry["club_count"]) == (3, 1)


def test_queued_and_cancelled_do_not_count(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    seated = [
        fencer_with_club(auth_headers, engine, f"s{i}@example.com", f"Klub {i}") for i in range(2)
    ]
    for headers in seated:
        client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=headers)
    # LS holds two: this one waits in its queue
    queued = fencer_with_club(auth_headers, engine, "q@example.com", "Klub Q")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=queued)
    gone = fencer_with_club(auth_headers, engine, "x@example.com", "Klub X")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["SB"]}, headers=gone)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=gone)

    entry = cup_entry(client)
    assert (entry["entrant_count"], entry["club_count"]) == (2, 2)
    assert entry["disciplines"][0]["queue_length"] == 1


def test_closing_day_falls_back_to_the_tournament_date(client, auth_headers):
    organizer = auth_headers()
    date = make_cup(client, organizer)
    assert cup_entry(client)["registration_closes_on"] == str(date)


def test_closing_day_is_the_one_set(client, auth_headers):
    organizer = auth_headers()
    closes = today_utc() + timedelta(days=20)
    make_cup(client, organizer, registration_closes=str(closes))
    assert cup_entry(client)["registration_closes_on"] == str(closes)
