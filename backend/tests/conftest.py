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

import hypothesis
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

# Hypothesis budgets, named as CLAUDE.md's test guidance already refers to them.
# `dev` is what an edit loop wants: enough inputs to catch a shape error, few
# enough that the contract suite stays under a minute. `ci` is the fuller run.
# `deadline=None` because these examples cross an ASGI stack into SQLite and a
# per-example time limit measures the machine, not the code.
hypothesis.settings.register_profile(
    "dev", max_examples=20, deadline=None, suppress_health_check=[hypothesis.HealthCheck.too_slow]
)
hypothesis.settings.register_profile(
    "ci", max_examples=50, deadline=None, suppress_health_check=[hypothesis.HealthCheck.too_slow]
)
hypothesis.settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


def today_local() -> datetime.date:
    """Today where the tournament is: the clock every date an organizer entered
    is read on.

    Registration opens and closes, the seating deadline, the team composition
    deadline and the early-bird cutoff are all whole days in the tournament's
    own timezone (spec `day-boundaries`). `date.today()` answers in whatever
    timezone the process happens to run in and is read nowhere in `app/` — a
    test that builds one of these dates that way names whichever day the runner
    is on and is a day out for the hours the runner runs ahead of UTC.

    Test tournaments leave `timezone` unset, so they resolve to
    `DEFAULT_TIMEZONE`, which is what this reads.
    """
    return datetime.datetime.now(zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)).date()


def today_utc() -> datetime.date:
    """Today in UTC: the clock the boundaries with nobody's calendar behind them
    are read on.

    Those are the split the public tournament listing draws between upcoming
    and held — one global boundary over tournaments from many zones, decided so
    in `fencer-home` — and the operational windows (the Fio fetch range, the set
    of tournaments the lifecycle passes walk, the feed token check).

    Not for a deadline: a date the organizer entered belongs to `today_local`
    above.
    """
    return datetime.datetime.now(datetime.UTC).date()


def today_in(timezone: str) -> datetime.date:
    """Today in a named zone, for a test that wants two tournaments whose own
    days provably differ from UTC's.

    A boundary read in the tournament's zone and one read in UTC agree for most
    of the day, so a single tournament cannot prove which clock the app used.
    A pair in `FAR_EAST` and `FAR_WEST` can: at every hour of the UTC day at
    least one of them is on a different date from UTC, and between them they
    cover all 24, so a pair of assertions written against each tournament's own
    day fails at any hour if the app reads UTC instead.
    """
    return datetime.datetime.now(zoneinfo.ZoneInfo(timezone)).date()


# UTC+14 and UTC-11: the extremes of the inhabited offsets, chosen so their
# disagreements with UTC overlap and together span every hour (`today_in`)
FAR_EAST = "Pacific/Kiritimati"
FAR_WEST = "Pacific/Niue"


def deadline_passed(days_ago: int = 1) -> datetime.date:
    """A deadline already past — on the one clock every deadline is read on.

    Settlement, settled-ness, the reminder anchor and the registration close all
    resolve the moment through the tournament's own timezone (`setup.local_date`),
    so one date is past for all of them. This used to take the earliest of three
    clocks, because the app read three; `unify-day-boundary-clocks` left one.
    """
    return today_local() - datetime.timedelta(days=days_ago)


def deadline_ahead(days: int = 5) -> datetime.date:
    """A seating deadline `days` out, on the same clock `deadline_passed` uses.

    The reminder horizon is measured from the tournament's own day
    (`scheduler._reminder_due`), so the distance a test intends is the distance
    the app will measure.
    """
    return today_local() + datetime.timedelta(days=days)


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
                fencer = session.scalars(select(Fencer).where(Fencer.email == email)).one()
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


# a source row nothing else uses, handed out one per synthetic credit so that
# two credits in one test are two payments rather than one offered twice
_fake_source_id = 900_000


def credit_registration(
    session,
    registration,
    amount_cents: int,
    *,
    currency=None,
    value_date=None,
    source_id: int | None = None,
    origin=None,
):
    """Credit a registration in a test the way the application does: by
    appending to the journal.

    A test that wants a paid registration builds one out of money, because
    that is the only thing that makes one — there is no paid state to assign
    since `derive-balances-from-credits`. Setting a counter used to do it in a
    line, and a test that did could go on passing after the counter stopped
    being what anything read.

    `source_id` defaults to a value unique per call, so two credits against one
    registration are two payments rather than one payment offered twice — which
    the journal refuses.
    """
    from app import ledger
    from app.models import CreditOrigin, CreditSource, Currency

    global _fake_source_id
    _fake_source_id += 1
    tournament = registration.tournament
    entry = ledger.credit(
        session,
        tournament,
        registration,
        amount_cents=amount_cents,
        currency=currency or Currency(tournament.local_currency),
        value_date=value_date or registration.registered_at.date(),
        source_kind=CreditSource.BANK_TRANSACTION,
        source_id=source_id if source_id is not None else _fake_source_id,
        origin=origin or CreditOrigin.AUTO_VS,
    )
    session.commit()
    return entry


def waive_registration(session, registration, reason: str = "test waiver", by: str = "test <t@e>"):
    """Waive a registration in a test — the other way one comes to read paid."""
    from app import ledger

    entry = ledger.grant_waiver(
        session,
        registration.tournament,
        registration,
        reason=reason,
        granted_by=by,
    )
    session.commit()
    return entry


def pay_registration(session, registration, *, currency=None):
    """Credit exactly what a registration owes, so it reads as paid.

    The replacement for `registration.state = RegistrationState.PAID`, which
    was never true of anything but the enum."""
    which = "eur" if currency is not None and str(currency) == "EUR" else "local"
    due = registration.outstanding_in(which)
    return credit_registration(session, registration, due, currency=currency)


def paid_at_of(registration):
    """The day a registration became paid, derived from the credit that
    completed its balance — the replacement for the field tests used to read.

    Takes the tournament off the registration's own relationship, which a test
    holding a live session always has."""
    from app import ledger

    return ledger.paid_at(registration, registration.tournament)
