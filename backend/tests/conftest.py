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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import operations
from app.db import Base, apply_sqlite_pragmas, get_session
from app.hr_index import get_hr_index, stub_index
from app.main import app
from app.models import Fencer, Role


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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


FEATURE_FLAGS = ("feature_schedule", "feature_payments", "feature_teams", "feature_extras")


def feature_payload(**enabled) -> dict:
    """A whole mode: a feature not named is off, because a mode is chosen as a
    whole rather than one flag at a time (design tournament-modes D2)."""
    return {flag: enabled.get(flag, False) for flag in FEATURE_FLAGS}


def set_features(client, headers, slug, **enabled):
    """Turn tournament features on. A tournament is created in easy mode, which
    asks fencers for no money at all, so every test exercising reservations,
    reminders, expiry, matching or the bank account has to enable payments —
    exactly as an organizer does, since nothing is ever derived at runtime
    (design tournament-modes D9)."""
    response = client.patch(
        f"/api/tournaments/{slug}/mode", json=feature_payload(**enabled), headers=headers
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

    Retries once with a filled-in bank account if that is the only thing
    missing: most callers are indifferent to it, and a priced tournament
    cannot publish without it (fix-payment-instructions-visibility)."""
    response = client.post(f"/api/tournaments/{slug}/publish", headers=headers)
    if response.status_code == 422 and "bank_account" in response.json()["detail"].get(
        "missing", []
    ):
        client.patch(
            f"/api/tournaments/{slug}",
            json={"bank_account": "CZ6508000000192000145399"},
            headers=headers,
        )
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
