"""Familiar faces on a list entry (spec public-browsing, A signed-in caller is
shown familiar entrants): clubmates before compatriots, never the caller,
never the queue, nothing for an anonymous caller, and a ranking claimed only
where a rating snapshot orders it."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fencer, HRRatingSnapshot, HRSnapshotRating, Tournament
from tests.conftest import publish, today_utc


def make_cup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": str(today_utc() + timedelta(days=30))},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 4, "fee": 500},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def fencer(auth_headers, engine, email, name, club=None, nationality=None):
    headers = auth_headers(email=email, name=name)
    with Session(engine) as session:
        row = session.scalars(select(Fencer).where(Fencer.email == email)).one()
        row.club = club
        row.nationality = nationality
        session.commit()
    return headers


def enter(client, headers):
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=headers
    )
    assert response.status_code == 201, response.text


def familiar(client, headers=None):
    listed = client.get("/api/tournaments/open", headers=headers or {}).json()
    return next(t for t in listed if t["slug"] == "cup").get("familiar")


def test_clubmates_beat_compatriots_and_the_caller_is_left_out(client, auth_headers, engine):
    make_cup(client, auth_headers())
    me = fencer(auth_headers, engine, "me@example.com", "Petr Novák", "Šermířský klub Brno", "CZ")
    enter(client, me)
    for i, (club, nationality) in enumerate(
        [("sermirsky  KLUB brno", "Czech Republic"), (None, "CZ")]
    ):
        enter(
            client,
            fencer(auth_headers, engine, f"o{i}@example.com", f"Eva Malá{i}", club, nationality),
        )

    found = familiar(client, me)
    assert (found["basis"], found["total"], found["ranked"]) == ("club", 1, False)
    assert found["people"] == [{"initials": "EM", "label": "Eva M."}]


def test_compatriots_when_no_clubmate_is_seated(client, auth_headers, engine):
    make_cup(client, auth_headers())
    me = fencer(auth_headers, engine, "me@example.com", "Petr Novák", "Klub A", "Czech Republic")
    for i in range(4):
        enter(
            client, fencer(auth_headers, engine, f"o{i}@example.com", f"Jan K{i}", "Klub B", "CZ")
        )

    found = familiar(client, me)
    assert (found["basis"], found["country"], found["total"]) == ("country", "CZ", 4)
    assert len(found["people"]) == 3


def test_the_queue_does_not_count(client, auth_headers, engine):
    make_cup(client, auth_headers())
    me = fencer(auth_headers, engine, "me@example.com", "Petr Novák", "Klub A")
    for i in range(4):
        enter(client, fencer(auth_headers, engine, f"s{i}@example.com", f"Jan S{i}", "Klub B"))
    # the discipline holds four: the clubmate waits in its queue
    enter(client, fencer(auth_headers, engine, "q@example.com", "Eva Q", "Klub A"))

    assert familiar(client, me) is None


def test_no_nationality_no_country_step(client, auth_headers, engine):
    make_cup(client, auth_headers())
    me = fencer(auth_headers, engine, "me@example.com", "Petr Novák", "Klub A")
    enter(client, fencer(auth_headers, engine, "o@example.com", "Jan K", "Klub B", "CZ"))

    assert familiar(client, me) is None


def test_anonymous_caller_sees_no_faces(client, auth_headers, engine):
    make_cup(client, auth_headers())
    enter(client, fencer(auth_headers, engine, "o@example.com", "Jan K", "Klub A", "CZ"))

    listed = client.get("/api/tournaments/open").json()
    assert "familiar" not in next(t for t in listed if t["slug"] == "cup")


def test_a_rating_snapshot_orders_and_is_claimed(client, auth_headers, engine):
    make_cup(client, auth_headers())
    me = fencer(auth_headers, engine, "me@example.com", "Petr Novák", "Klub A", "CZ")
    ratings = {"Low Rated": 1200.0, "High Rated": 1700.0, "Mid Rated": 1450.0, "No Rating": None}
    for i, name in enumerate(ratings):
        enter(client, fencer(auth_headers, engine, f"o{i}@example.com", name, "Klub B", "CZ"))
    with Session(engine) as session:
        cup = session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
        snapshot = HRRatingSnapshot(tournament_id=cup.id, fencer_count=len(ratings))
        session.add(snapshot)
        session.flush()
        code = cup.disciplines[0].taxonomy_code
        for i, rating in enumerate(ratings.values()):
            row = session.scalars(select(Fencer).where(Fencer.email == f"o{i}@example.com")).one()
            row.hr_id = 100 + i
            session.add(
                HRSnapshotRating(
                    snapshot_id=snapshot.id, hr_id=100 + i, discipline_code=code, rating=rating
                )
            )
        session.commit()

    found = familiar(client, me)
    assert found["ranked"] is True
    assert [p["label"] for p in found["people"]] == ["High R.", "Mid R.", "Low R."]
