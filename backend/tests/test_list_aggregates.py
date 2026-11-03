"""The public aggregates a list entry states (spec public-browsing, A list
entry states its public aggregates): seated fencers counted once across
disciplines, clubs compared loosely, the queue left out, and the closing day
resolved as the registration gate resolves it."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fencer, Rule, Tournament
from tests.conftest import publish, set_features, today_utc


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


# ------------------------------------------------------------------ events


def make_event(client, organizer, items):
    """A record with no discipline offering `items`, (name, category,
    capacity) each, published; their ids in that order."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": str(today_utc() + timedelta(days=30))},
        headers=organizer,
    )
    set_features(client, organizer, "cup", feature_extras=True)
    ids = []
    for name, category, capacity in items:
        response = client.post(
            "/api/tournaments/cup/extra-items",
            json={"name": name, "category": category, "price": 300, "capacity": capacity},
            headers=organizer,
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    publish(client, organizer, "cup")
    return ids


def take(client, headers, *items):
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": [], "extras": [{"extra_item_id": item} for item in items]},
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_an_event_counts_its_program_once_and_not_the_party(client, auth_headers, engine):
    organizer = auth_headers()
    seminar, tour, party, shirt = make_event(
        client,
        organizer,
        [
            ("Seminář", "seminar", None),
            ("Prohlídka", "other_action", None),
            ("Afterparty", "afterparty", None),
            ("Tričko", "merch", None),
        ],
    )
    take(client, fencer_with_club(auth_headers, engine, "a@example.com", "Klub A"), seminar, tour)
    take(client, fencer_with_club(auth_headers, engine, "b@example.com", "klub a"), seminar, party)
    take(client, fencer_with_club(auth_headers, engine, "c@example.com", "Klub C"), party, shirt)

    entry = cup_entry(client)
    assert (entry["entrant_count"], entry["club_count"]) == (2, 1)


def test_an_event_meters_its_capped_program_only(client, auth_headers, engine):
    organizer = auth_headers()
    seminar, _workshop, _party, tour = make_event(
        client,
        organizer,
        [
            ("Seminář", "seminar", 20),
            ("Workshop", "other_action", None),
            ("Afterparty", "afterparty", 50),
            ("Prohlídka", "other_action", 2),
        ],
    )
    for i in range(3):
        take(client, auth_headers(email=f"f{i}@example.com", name=f"F{i}"), seminar)
    take(client, auth_headers(email="t@example.com", name="T"), seminar, tour)

    meters = cup_entry(client)["program_meters"]
    assert [(m["id"], m["name"], m["entered"], m["capacity"]) for m in meters] == [
        (seminar, "Seminář", 4, 20),
        (tour, "Prohlídka", 1, 2),
    ]


def test_a_removed_row_leaves_the_event_figures(client, auth_headers, engine):
    organizer = auth_headers()
    (seminar,) = make_event(client, organizer, [("Seminář", "seminar", 20)])
    take(client, auth_headers(email="a@example.com", name="Adéla"), seminar)
    take(client, auth_headers(email="b@example.com", name="Boris"), seminar)
    rows = {
        row["name"]: row["id"]
        for row in client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    }
    with Session(engine) as session:
        cup = session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
        session.add(
            Rule(
                tournament_id=cup.id,
                phase="fencers",
                kind="row_delete",
                target=rows["Boris"],
                payload={},
                created_by=1,
            )
        )
        session.commit()

    entry = cup_entry(client)
    assert entry["entrant_count"] == 1
    assert [m["entered"] for m in entry["program_meters"]] == [1]


def test_a_tournament_ignores_its_seminar(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    set_features(client, organizer, "cup", feature_extras=True)
    seminar = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": "Seminář", "category": "seminar", "price": 300, "capacity": 20},
        headers=organizer,
    ).json()["id"]
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=auth_headers(email="a@example.com", name="Adéla"),
    )
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["SB"], "extras": [{"extra_item_id": seminar}]},
        headers=auth_headers(email="b@example.com", name="Boris"),
    )

    entry = cup_entry(client)
    assert entry["entrant_count"] == 2
    assert entry["program_meters"] == []
