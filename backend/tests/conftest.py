import os

os.environ["HEMA_SQUIRE_SCHEDULER_ENABLED"] = "false"
os.environ["HEMA_SQUIRE_HR_AUTO_REFRESH"] = "false"
# the app boots against the configured database while the tests run on an
# in-memory one; a startup sweep there would touch the developer's own file
os.environ["HEMA_SQUIRE_OPERATIONS_SWEEP_ENABLED"] = "false"
# every test boots the app through TestClient, which runs the lifespan; without
# this the dev-secret refusal in app.main fails the whole suite
os.environ["HEMA_SQUIRE_DEBUG"] = "true"
# the suite signs up and logs in far more often than a minute's throttle allows,
# all from one address; test_auth_throttle enables the limiter deliberately
os.environ["HEMA_SQUIRE_RATE_LIMIT_ENABLED"] = "false"

import datetime
import shutil
import zoneinfo
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import operations
from app.bank import get_fio_client
from app.constraints import DEFAULT_TIMEZONE
from app.db import Base, apply_sqlite_pragmas, get_session
from app.hr_index import get_hr_index, stub_index
from app.main import app
from app.models import Fencer, Role


def today_local() -> datetime.date:
    """Today where the tournament is, for the dates that are read there.

    The opening gate is resolved in the tournament's own timezone
    (`setup.start_of_local_day`), while `date.today()` answers in whatever
    timezone the process happens to run in. Those disagree for the last two
    hours of every UTC day, and CI runs in UTC: a test that sets "opens
    tomorrow" from the runner's clock is naming a Europe/Prague day that began
    an hour ago, and the tournament is open when it meant to be shut.

    Only for dates handed to that gate — the opening and closing of
    registration. The other deadlines are read in UTC; `today_utc` below is
    theirs. Nothing in the app reads a date from the server's own
    `date.today()` except `scheduler.settle_seating_if_due` and the Fio
    window, so a test that builds a date that way is naming whichever day the
    runner's timezone happens to be on and will be a day out for the hours the
    runner runs ahead of UTC.
    """
    return datetime.datetime.now(zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)).date()


def today_utc() -> datetime.date:
    """Today in UTC, for the deadlines the app compares in UTC.

    Those are the seating deadline (`setup.seating_has_settled` and
    `scheduler._reminder_due`, both asked with `_now().date()`), the team
    composition deadline (`routers/tournaments.py`), and the boundary the open
    tournaments listing splits upcoming from past on.

    A test that builds these from `date.today()` agrees with the app only while
    the runner's timezone is on the same day as UTC. On a runner ahead of UTC —
    anywhere in CET/CEST after midnight local — it names tomorrow's date and the
    deadline lands a day late.

    That the app reads day boundaries from three different clocks is a real
    inconsistency, not a test concern; it is written up in
    `openspec/changes/date-boundaries-read-three-clocks.md` and needs decisions
    that are not the tests' to make. This helper only keeps the tests honest
    about which clock they are asserting against today.
    """
    return datetime.datetime.now(datetime.UTC).date()


def deadline_passed(days_ago: int = 1) -> datetime.date:
    """A date every clock the app reads agrees is in the past.

    A deadline set here can be read by three different clocks. The server's
    `date.today()` decides whether seating settles
    (`scheduler.settle_seating_if_due`); `datetime.now(UTC).date()` decides
    whether seating *has* settled (`setup.seating_has_settled`) and whether a
    reminder is due (`scheduler._reminder_due`); the tournament's own timezone
    decides whether registration has closed (`setup.local_date`). And an unset
    seating deadline resolves to `registration_closes`
    (`setup.seating_deadline_for`), so one date can be read by all three at
    once.

    They sit on different days for the hours the server runs ahead of or behind
    UTC, and in that window no single date is "yesterday" for all of them — a
    test that picks any one clock passes on one path and fails on another.
    Taking the earliest makes the date unambiguously past for every reader.

    That one deadline is read from three clocks is the inconsistency written up
    in `openspec/changes/date-boundaries-read-three-clocks.md`. Until that is
    decided, a test that wants a passed deadline has to clear all of them, and
    this is where that knowledge lives rather than in each test.
    """
    earliest = min(today_utc(), today_local(), datetime.date.today())
    return earliest - datetime.timedelta(days=days_ago)


def deadline_ahead(days: int = 5) -> datetime.date:
    """A seating deadline `days` out on the clock the reminder is anchored to.

    Not the mirror of `deadline_passed`. A deadline still to come is only read
    by `scheduler._reminder_due`, which asks in UTC, so the distance that
    decides whether the reminder is due has to be measured from the UTC day —
    taking the later of the two clocks would push a `reminder_day` horizon one
    day out of the window and send nothing.

    The settlement path cannot fire on this date either way: the server clock is
    within a day of UTC, so a horizon of several days is ahead of both.
    """
    return today_utc() + datetime.timedelta(days=days)


@pytest.fixture
def migration_db_copy(tmp_path):
    """Hand a test its own copy of a database some module-scoped fixture built.

    The migration suites shell out to `alembic upgrade` to build their subject,
    which costs about a second. Built once per module and copied per test, each
    test still gets a database it may migrate, downgrade or corrupt freely,
    without paying for the build. Sidecars are copied where they exist: a clean
    subprocess exit checkpoints and removes them, but copying only the main file
    would silently lose data if one ever survived.
    """

    def _copy(template: Path) -> Path:
        db_path = tmp_path / template.name
        shutil.copy(template, db_path)
        for suffix in ("-wal", "-shm"):
            sidecar = template.with_name(template.name + suffix)
            if sidecar.exists():
                shutil.copy(sidecar, db_path.with_name(db_path.name + suffix))
        return db_path

    return _copy


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # the same pragmas production runs on — notably foreign_keys=ON, so an
    # orphan write fails here rather than on the deployment
    apply_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine, monkeypatch):
    def override_session():
        with Session(engine) as session:
            yield session

    # background operation work opens its own session — the request's is closed
    # long before it runs — so the runner's factory has to be pointed at the
    # test engine too, the way get_session is (app.operations.run_now)
    monkeypatch.setattr(
        operations,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )
    # ...and the work runs inline rather than on a thread. The suite's database
    # is in-memory SQLite behind a StaticPool, which is one connection shared by
    # every session: a worker thread flushing while the test thread closes a
    # request would have its uncommitted rows rolled back out from under it.
    # That is a property of the fixture, not of the runner — production runs a
    # file database with a pool per connection — so the tests drive the same
    # `run_now` the background task drives, without the thread.
    monkeypatch.setattr(operations, "run_in_background", operations.run_now)
    app.dependency_overrides[get_session] = override_session
    # tests run on the stub fixture dataset; hr-integration tests override this
    app.dependency_overrides[get_hr_index] = stub_index
    # recording a feed token verifies it against Fio, so every test that
    # configures one would otherwise reach the network. The default accepts;
    # tests about refusal or an outage override it with their own stub
    app.dependency_overrides[get_fio_client] = lambda: AcceptingFio()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


class AcceptingFio:
    """A bank that answers, holds no transactions, and accepts every token."""

    def fetch(self, token, date_from, date_to):
        return []

    def verify(self, token):
        return None


def set_fio_token(client, headers, slug, token="test-token"):
    """Configure a tournament's bank feed. Its own endpoint, because a token is
    verified as it is recorded and the tournament PATCH does not accept one
    (spec tournament-admin)."""
    response = client.put(
        f"/api/tournaments/{slug}/fio-token", json={"token": token}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response


FEATURE_FLAGS = ("feature_schedule", "feature_payments", "feature_teams", "feature_extras")


def feature_payload(**enabled) -> dict:
    """All four stored flags: one not named is off, because the endpoint takes
    them together rather than one at a time (spec tournament-features)."""
    return {flag: enabled.get(flag, False) for flag in FEATURE_FLAGS}


def set_features(client, headers, slug, **enabled):
    """Turn tournament features on. A tournament is created with every flag
    off, which asks fencers for no money at all, so every test exercising
    reservations, reminders, expiry, matching or the bank account has to enable
    payments — exactly as an organizer does, since nothing is ever derived at
    runtime (spec tournament-features)."""
    response = client.patch(
        f"/api/tournaments/{slug}/features", json=feature_payload(**enabled), headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def enable_payments(client, headers, slug):
    return set_features(client, headers, slug, feature_payments=True)


def publish(client, headers, slug):
    """Publish a tournament so it reaches fencers: setup-complete alone no
    longer does (design add-explicit-publishing). Every test that expects a
    tournament in /open, /held, /mine, or accepting registrations must call
    this after completing its mandatory setup.

    Fills in the mandatory items a caller is indifferent to and retries: the
    place, the organizer list and the bank account. Most tests set none of the
    three — a priced tournament cannot publish without an account
    (fix-payment-instructions-visibility), and since data work waits for
    publication (gate-data-work-behind-publication) every import, payments and
    matching test now comes through here. What is not filled in is what a test
    chooses: its disciplines and their prices. A tournament missing one of
    those cannot publish, and that is the test saying so."""
    filler = {
        "location": "Brno",
        "organizers": [{"name": "Org", "link": None}],
        "bank_account": "CZ6508000000192000145399",
    }
    response = client.post(f"/api/tournaments/{slug}/publish", headers=headers)
    if response.status_code == 422:
        missing = response.json()["detail"].get("missing", [])
        patch = {key: value for key, value in filler.items() if key in missing}
        if patch:
            client.patch(f"/api/tournaments/{slug}", json=patch, headers=headers)
            response = client.post(f"/api/tournaments/{slug}/publish", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def auth_headers(client, engine):
    """Signup helper. Accounts default to the Organizer role because most
    tests bootstrap a tournament with them; pass role=Role.FENCER for a
    plain fencer."""

    def make(email="organizer@example.com", name="Organizer", role=Role.ORGANIZER):
        response = client.post(
            "/api/auth/signup",
            json={"email": email, "password": "correct-horse", "display_name": name},
        )
        assert response.status_code == 201, response.text
        if role != Role.FENCER:
            with Session(engine) as session:
                fencer = session.scalar(select(Fencer).where(Fencer.email == email))
                fencer.role = role
                session.commit()
        return {"Authorization": f"Bearer {response.json()['token']}"}

    return make


def settle(client, headers, slug="cup", kind=None, timeout=10.0):
    """Wait out the tournament's running operation and return what concluded.

    The three console operations return the moment their record exists and do
    their work behind the request (spec console-operations, An operation is a
    record, not a request), so a test that wants the result asks the record for
    it — exactly as the console does. Requests drive the loop the background
    task runs on, so the poll is also what lets it progress.
    """
    import time

    deadline = time.monotonic() + timeout
    while True:
        body = client.get(f"/api/tournaments/{slug}/operations", headers=headers).json()
        if body["running"] is None:
            break
        assert time.monotonic() < deadline, f"operation never concluded: {body['running']}"
        time.sleep(0.01)
    concluded = {op["kind"]: op for op in body["concluded"]}
    if kind is None:
        return concluded
    assert kind in concluded, f"no concluded {kind} operation: {body}"
    return concluded[kind]


def import_statement(client, headers, content: bytes, slug="cup", filename="v.csv"):
    """Import a statement and return the counts it used to answer with.

    The import is a started operation now (design add-payments-intake D3), so
    the counts live in the record. Tests that only care about the effect ask
    for them the way the console does.
    """
    import io

    response = client.post(
        f"/api/tournaments/{slug}/payments/import-statement",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
        headers=headers,
    )
    if response.status_code != 202:
        return response
    return settle(client, headers, slug, kind="statement")["outcome"]


def outcome(client, headers, slug="cup", kind="parse"):
    """The outcome of the most recent operation of a kind — the body these
    endpoints used to return synchronously."""
    return settle(client, headers, slug, kind)["outcome"]
