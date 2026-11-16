"""A discipline tab states whose ratings are not fetched (spec export-tables):
when the latest snapshot was taken, and how many of the tab's bound fighters
it holds no fetch for — a team member bound after it among them, a fighter
asked and unrated in the category not."""

from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hr_sync import get_hr_fetcher
from app.main import app
from app.models import HRRatingSnapshot
from tests.test_sheets_export import FakeHRFetcher, fighter_page
from tests.test_team_sheet_export import enter, make_cup

SABRE = "Mixed & Men's Steel Sabre"


@pytest.fixture
def fetcher() -> Iterator[FakeHRFetcher]:
    fetcher = FakeHRFetcher()
    app.dependency_overrides[get_hr_fetcher] = lambda: fetcher
    yield fetcher
    app.dependency_overrides.pop(get_hr_fetcher, None)


def statement(client, organizer):
    table = client.get(
        "/api/tournaments/cup/export/table?kind=discipline&key=SA", headers=organizer
    ).json()
    return table["ratings_fetched_at"], table["ratings_missing"]


def snapshot(client, organizer):
    response = client.post("/api/tournaments/cup/ratings/snapshot", headers=organizer)
    assert response.status_code == 200, response.text


def team_of(client, auth_headers, members):
    organizer = auth_headers()
    make_cup(client, organizer)
    captain = auth_headers(email="a@example.com", name="Ann A")
    enter(client, captain, "Wolves", members)
    return organizer, captain


def test_no_snapshot_counts_every_bound_fighter(client, auth_headers, fetcher):
    organizer, _ = team_of(
        client,
        auth_headers,
        [{"name": "Ann A", "hr_id": 1}, {"name": "Bob B", "hr_id": 2}, {"name": "Cid C"}],
    )

    assert statement(client, organizer) == (None, 2)


def test_asked_and_unrated_is_not_missing(client, auth_headers, fetcher):
    organizer, _ = team_of(
        client, auth_headers, [{"name": "Ann A", "hr_id": 1}, {"name": "Bob B", "hr_id": 2}]
    )
    fetcher.pages[1] = fighter_page([(SABRE, 1400.0, 12)])
    # Bob's page holds no sabre rating: HEMA Ratings was asked
    fetcher.pages[2] = fighter_page([("Mixed & Men's Longsword", 1200.0, 30)])

    snapshot(client, organizer)

    taken_at, missing = statement(client, organizer)
    assert taken_at is not None
    assert missing == 0


def test_a_member_bound_after_the_snapshot_is_missing(client, auth_headers, fetcher):
    organizer, captain = team_of(client, auth_headers, [{"name": "Ann A", "hr_id": 1}])
    fetcher.pages[1] = fighter_page([(SABRE, 1400.0, 12)])
    snapshot(client, organizer)

    own = client.get("/api/tournaments/cup/my-registration", headers=captain).json()
    team = own["teams"][0]
    members = team["members"]
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team['id']}/roster",
        json={
            "members": [
                {"id": members[0]["id"], "name": "Ann A", "hr_id": 1},
                {"name": "Bob B", "hr_id": 2},
            ]
        },
        headers=captain,
    )
    assert response.status_code == 200, response.text

    assert statement(client, organizer)[1] == 1


def test_an_old_snapshot_counts_by_what_it_rated(client, auth_headers, fetcher, engine):
    organizer, _ = team_of(
        client, auth_headers, [{"name": "Ann A", "hr_id": 1}, {"name": "Bob B", "hr_id": 2}]
    )
    fetcher.pages[1] = fighter_page([(SABRE, 1400.0, 12)])
    fetcher.pages[2] = fighter_page([("Mixed & Men's Longsword", 1200.0, 30)])
    snapshot(client, organizer)
    # a snapshot taken before it recorded whom it asked
    with Session(engine) as session:
        for row in session.scalars(select(HRRatingSnapshot)):
            row.hr_ids = None
        session.commit()

    # Ann has a rating in it; Bob has none, and the old record cannot say he
    # was asked
    assert statement(client, organizer)[1] == 1
