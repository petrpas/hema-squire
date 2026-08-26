"""The opening moment: date + time-of-day + zone folded into one instant, and
the gate that compares against it (change add-registration-open-time).

The two edges are measured differently on purpose (design D3): opening is an
instant, closing is the whole of its local day. These are unit tests over
`app.setup` — the HTTP-level gating lives in `test_registration_gating.py`.
"""

import datetime
from datetime import UTC

import pytest

from app import setup
from app.models import Tournament

PRAGUE = "Europe/Prague"
# Europe/Prague, 2026: clocks go forward 29 March (02:00 -> 03:00) and back
# 25 October (03:00 -> 02:00). 02:30 does not exist on the first and occurs
# twice on the second.
SPRING_FORWARD = datetime.date(2026, 3, 29)
AUTUMN_BACK = datetime.date(2026, 10, 25)


def tournament(**kwargs) -> Tournament:
    """A tournament far enough along to reach the window checks: published,
    not cancelled. Unattached, so column defaults do not run — the zone is set
    here rather than left to the ORM."""
    fields = {
        "date": datetime.date(2026, 12, 5),
        "timezone": PRAGUE,
        "published_at": datetime.datetime(2026, 1, 1, tzinfo=UTC),
        "cancelled_at": None,
        "registration_opens": None,
        "registration_opens_time": None,
        "registration_closes": None,
        "amendments_close": None,
    }
    fields.update(kwargs)
    return Tournament(**fields)


def utc(year, month, day, hour=0, minute=0, second=0) -> datetime.datetime:
    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=UTC)


# ---- registration_opens_at (task 2.1) ----


def test_no_opening_date_has_no_opening_instant():
    """No date means registration opens on publication — there is no moment to
    resolve, and None is that answer rather than a fabricated one."""
    assert setup.registration_opens_at(tournament()) is None


def test_opening_time_resolves_to_the_named_hour():
    t = tournament(
        registration_opens=datetime.date(2026, 9, 1),
        registration_opens_time=datetime.time(18, 0),
    )
    # 1 September is CEST (UTC+2), so 18:00 local is 16:00Z
    assert setup.registration_opens_at(t) == utc(2026, 9, 1, 16, 0)


def test_unset_time_is_the_start_of_the_local_day():
    """What a tournament carrying only a date has always meant — but the start
    of the day *where it is held*, which is what changes here."""
    t = tournament(registration_opens=datetime.date(2026, 9, 1))
    assert setup.registration_opens_at(t) == utc(2026, 8, 31, 22, 0)


def test_winter_opening_uses_the_winter_offset():
    """The offset is read per date, not fixed once: the same wall clock is a
    different instant in January than in September."""
    t = tournament(
        registration_opens=datetime.date(2026, 1, 15),
        registration_opens_time=datetime.time(18, 0),
    )
    assert setup.registration_opens_at(t) == utc(2026, 1, 15, 17, 0)


def test_zone_ahead_of_utc():
    t = tournament(
        timezone="Asia/Tokyo",
        registration_opens=datetime.date(2026, 9, 1),
        registration_opens_time=datetime.time(9, 0),
    )
    assert setup.registration_opens_at(t) == utc(2026, 9, 1, 0, 0)


def test_ambiguous_opening_takes_the_first_occurrence():
    """The autumn hour that happens twice (design D4): opening a little early
    is harmless, opening an hour late is the failure that matters."""
    t = tournament(
        registration_opens=AUTUMN_BACK,
        registration_opens_time=datetime.time(2, 30),
    )
    # the first 02:30 is still CEST (UTC+2) — the second would be 01:30Z
    assert setup.registration_opens_at(t) == utc(2026, 10, 25, 0, 30)


def test_unknown_zone_falls_back_rather_than_failing_the_read():
    """A stored zone the database no longer knows must not 500 every fencer's
    tournament list; the write path is what validates the name."""
    t = tournament(
        timezone="Mars/Olympus_Mons",
        registration_opens=datetime.date(2026, 9, 1),
        registration_opens_time=datetime.time(18, 0),
    )
    assert setup.registration_opens_at(t) == utc(2026, 9, 1, 16, 0)


# ---- local_date (task 2.2) ----


def test_local_date_is_the_tournaments_day_not_the_utc_day():
    t = tournament()
    # 22:30Z on 30 September is already 1 October in Prague
    assert setup.local_date(t, utc(2026, 9, 30, 22, 30)) == datetime.date(2026, 10, 1)
    assert setup.local_date(t, utc(2026, 9, 30, 21, 30)) == datetime.date(2026, 9, 30)


# ---- the opening edge as an instant (task 2.3) ----


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (utc(2026, 9, 1, 15, 59), setup.NOT_YET_OPEN),  # 17:59 Prague
        (utc(2026, 9, 1, 16, 0), None),  # 18:00 Prague, to the minute
        (utc(2026, 9, 1, 16, 1), None),  # 18:01 Prague
    ],
)
def test_gate_opens_at_the_named_minute(now, expected):
    t = tournament(
        registration_opens=datetime.date(2026, 9, 1),
        registration_opens_time=datetime.time(18, 0),
    )
    assert setup.registration_availability(t, now) is expected


def test_gate_opens_on_the_local_day_not_the_utc_day():
    """The drift this change fixes. Prague is ahead of UTC, so its day turns
    *first*: a date-only tournament used to stay shut until 00:00 UTC, which
    is 02:00 Prague, two hours after the day it named had begun."""
    t = tournament(registration_opens=datetime.date(2026, 9, 1))
    # 23:59 on 31 August in Prague — still shut
    assert setup.registration_availability(t, utc(2026, 8, 31, 21, 59)) == setup.NOT_YET_OPEN
    # 00:00 on 1 September in Prague — open, where the old gate held it shut
    # for two more hours
    assert setup.registration_availability(t, utc(2026, 8, 31, 22, 0)) is None


def test_gate_behind_utc_opens_later_than_it_used_to():
    """The shift runs the other way for a zone behind UTC, where the local day
    turns after the UTC one."""
    t = tournament(timezone="America/New_York", registration_opens=datetime.date(2026, 9, 1))
    # 20:00 on 31 August in New York — the UTC day has turned, the local one
    # has not, and the old gate would already have opened
    assert setup.registration_availability(t, utc(2026, 9, 1, 0, 0)) == setup.NOT_YET_OPEN
    assert setup.registration_availability(t, utc(2026, 9, 1, 4, 0)) is None


# ---- the closing edge as a whole local day (task 2.2) ----


def test_close_runs_to_the_end_of_the_local_day():
    t = tournament(
        registration_opens=datetime.date(2026, 9, 1),
        registration_closes=datetime.date(2026, 9, 30),
    )
    # 23:30 Prague on the closing date
    assert setup.registration_availability(t, utc(2026, 9, 30, 21, 30)) is None
    # 00:30 Prague the next day
    assert setup.registration_availability(t, utc(2026, 9, 30, 22, 30)) == setup.CLOSED


def test_amendments_close_is_also_a_local_day():
    t = tournament(
        registration_opens=datetime.date(2026, 9, 1),
        registration_closes=datetime.date(2026, 10, 30),
        amendments_close=datetime.date(2026, 9, 30),
    )
    assert setup.amendment_availability(t, utc(2026, 9, 30, 21, 30)) is None
    assert setup.amendment_availability(t, utc(2026, 9, 30, 22, 30)) == setup.CLOSED


# ---- gate order is unchanged (design D2 of add-explicit-publishing) ----


def test_cancelled_and_unpublished_still_outrank_the_window():
    opens = {
        "registration_opens": datetime.date(2026, 9, 1),
        "registration_opens_time": datetime.time(18, 0),
    }
    cancelled = tournament(cancelled_at=datetime.datetime(2026, 2, 1, tzinfo=UTC), **opens)
    assert setup.registration_availability(cancelled, utc(2026, 9, 2)) == setup.CLOSED
    draft = tournament(published_at=None, **opens)
    assert setup.registration_availability(draft, utc(2026, 9, 2)) == setup.NOT_PUBLISHED


# ---- the write path (tasks 3.1 - 3.4) ----
#
# These go through the API, because what is being checked is the refusal a
# client sees: a named field, a code, and nothing stored.


def setup_tournament(client, organizer, slug="cup", **patch):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    if patch:
        return client.patch(f"/api/tournaments/{slug}", json=patch, headers=organizer)
    return client.get(f"/api/tournaments/{slug}", headers=organizer)


def field_error(response) -> tuple[str, str]:
    errors = response.json()["detail"]["errors"]
    assert len(errors) == 1
    return errors[0]["field"], errors[0]["code"]


def test_new_tournament_carries_the_default_zone(client, auth_headers):
    organizer = auth_headers()
    response = setup_tournament(client, organizer)
    assert response.json()["timezone"] == PRAGUE


def test_opening_time_stored_with_its_date(client, auth_headers):
    organizer = auth_headers()
    response = setup_tournament(
        client,
        organizer,
        registration_opens="2026-09-01",
        registration_opens_time="18:00:00",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["registration_opens_time"] == "18:00:00"
    assert body["registration_opens_at"] == "2026-09-01T16:00:00Z"


def test_opening_time_without_a_date_is_refused(client, auth_headers):
    organizer = auth_headers()
    response = setup_tournament(client, organizer, registration_opens_time="18:00:00")
    assert response.status_code == 422
    assert field_error(response) == ("registration_opens_time", "opening_time_without_date")

    stored = client.get("/api/tournaments/cup", headers=organizer).json()
    assert stored["registration_opens_time"] is None
    assert stored["registration_opens"] is None


def test_clearing_the_date_clears_the_time(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(
        client,
        organizer,
        registration_opens="2026-09-01",
        registration_opens_time="18:00:00",
    )
    response = client.patch(
        "/api/tournaments/cup", json={"registration_opens": None}, headers=organizer
    )
    assert response.status_code == 200
    body = response.json()
    assert body["registration_opens"] is None
    assert body["registration_opens_time"] is None
    assert body["registration_opens_at"] is None


def test_time_left_standing_from_an_earlier_save_is_refused(client, auth_headers):
    """The rule is applied to the merged state, so a date and a time arriving
    in separate requests are still judged together."""
    organizer = auth_headers()
    setup_tournament(
        client,
        organizer,
        registration_opens="2026-09-01",
        registration_opens_time="18:00:00",
    )
    # a later save that touches neither, on a tournament that has both, must
    # still pass
    ok = client.patch("/api/tournaments/cup", json={"location": "Brno"}, headers=organizer)
    assert ok.status_code == 200
    assert ok.json()["registration_opens_time"] == "18:00:00"


def test_nonexistent_clock_time_is_refused(client, auth_headers):
    """02:30 does not occur in Prague on the spring-forward morning."""
    organizer = auth_headers()
    response = setup_tournament(
        client,
        organizer,
        registration_opens=str(SPRING_FORWARD),
        registration_opens_time="02:30:00",
    )
    assert response.status_code == 422
    assert field_error(response) == ("registration_opens_time", "opening_time_does_not_exist")


def test_ambiguous_clock_time_is_accepted_at_the_first_occurrence(client, auth_headers):
    """02:30 occurs twice on the autumn-back morning; the earlier one wins."""
    organizer = auth_headers()
    response = setup_tournament(
        client,
        organizer,
        registration_opens=str(AUTUMN_BACK),
        registration_opens_time="02:30:00",
    )
    assert response.status_code == 200
    assert response.json()["registration_opens_at"] == "2026-10-25T00:30:00Z"


def test_unknown_timezone_is_refused(client, auth_headers):
    organizer = auth_headers()
    response = setup_tournament(client, organizer, timezone="Mars/Olympus_Mons")
    assert response.status_code == 422
    assert field_error(response) == ("timezone", "unknown_timezone")
    assert client.get("/api/tournaments/cup", headers=organizer).json()["timezone"] == PRAGUE


def test_timezone_cannot_be_cleared(client, auth_headers):
    organizer = auth_headers()
    response = setup_tournament(client, organizer, timezone=None)
    assert response.status_code == 422
    assert field_error(response) == ("timezone", "unknown_timezone")


def test_known_timezone_is_stored_and_moves_the_moment(client, auth_headers):
    organizer = auth_headers()
    response = setup_tournament(
        client,
        organizer,
        timezone="Europe/London",
        registration_opens="2026-09-01",
        registration_opens_time="18:00:00",
    )
    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/London"
    # 18:00 BST is 17:00Z, an hour later than the same clock in Prague
    assert response.json()["registration_opens_at"] == "2026-09-01T17:00:00Z"


# ---- end to end (task 7.1) ----


def test_gate_opens_at_the_named_hour_end_to_end(client, auth_headers, monkeypatch):
    """The whole path, against a clock the test moves: an 18:00 Prague opening
    refuses at 17:59:59 local, accepts at 18:00:00 local, and is still shut at
    midnight UTC that day — the hour the pre-change gate would have opened at.
    """
    import datetime as dt

    from app.routers import registrations

    organizer = auth_headers()
    setup_tournament(
        client,
        organizer,
        location="Brno",
        organizers=[{"name": "Org", "link": None}],
        registration_opens="2026-09-01",
        registration_opens_time="18:00:00",
        timezone=PRAGUE,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    client.post("/api/tournaments/cup/publish", json={}, headers=organizer)
    fencer = auth_headers(email="f1@example.com", name="F1")

    def at(moment: dt.datetime):
        monkeypatch.setattr(registrations, "_now", lambda: moment)
        return client.post(
            "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
        )

    # 00:00 UTC on the opening date is 02:00 Prague — but the local day turned
    # two hours earlier, so this is *after* the opening date began and still
    # well before the hour the organizer named
    early = at(utc(2026, 9, 1, 0, 0))
    assert early.status_code == 403
    assert early.json()["detail"]["reason"] == "not_yet_open"

    # 17:59:59 Prague
    just_before = at(utc(2026, 9, 1, 15, 59, 59))
    assert just_before.status_code == 403
    assert just_before.json()["detail"]["reason"] == "not_yet_open"

    # 18:00:00 Prague, to the second
    assert at(utc(2026, 9, 1, 16, 0)).status_code == 201


def test_date_only_tournament_opens_at_the_start_of_its_local_day(client, auth_headers):
    """Task 7.2 — the shift this change makes to a tournament that carries no
    opening time: the start of the local day, which in Prague in summer is two
    hours *earlier* than the UTC day the old gate turned on. Its stored values
    are untouched."""
    organizer = auth_headers()
    response = setup_tournament(client, organizer, registration_opens="2026-09-01")
    body = response.json()
    assert body["registration_opens"] == "2026-09-01"
    assert body["registration_opens_time"] is None
    assert body["registration_opens_at"] == "2026-08-31T22:00:00Z"
