"""Authentication endpoints are throttled (deployment spec).

The suite runs with the limiter off — many tests legitimately sign up several
accounts a minute from one address — so these tests turn it on around themselves
and reset its counters, leaving no state behind for whatever runs next.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session
from app.hr_index import get_hr_index, stub_index
from app.main import app
from app.ratelimit import limiter

# distinct source addresses: the point of the throttle is that they are
# accounted separately
ATTACKER = "203.0.113.10"
BYSTANDER = "198.51.100.7"


@pytest.fixture
def throttled(engine):
    """Clients bound to explicit source addresses, with the limiter live."""

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_hr_index] = stub_index
    limiter.reset()
    limiter.enabled = True

    def client_from(address: str) -> TestClient:
        return TestClient(app, client=(address, 40000))

    try:
        yield client_from
    finally:
        limiter.enabled = False
        limiter.reset()
        app.dependency_overrides.clear()


def _login(client, email="nobody@example.com", password="wrong-password"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_attempts_are_capped_per_address(throttled):
    client = throttled(ATTACKER)
    with client:
        statuses = [_login(client).status_code for _ in range(6)]

    # the first five are answered (401: the account does not exist), the sixth
    # is refused before any password is verified
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429


def test_one_throttled_address_does_not_lock_out_another(throttled):
    attacker = throttled(ATTACKER)
    with attacker:
        for _ in range(6):
            _login(attacker)
        assert _login(attacker).status_code == 429

    bystander = throttled(BYSTANDER)
    with bystander:
        assert _login(bystander).status_code == 401


def test_signup_is_capped_more_tightly(throttled):
    client = throttled(ATTACKER)
    with client:
        statuses = []
        for i in range(4):
            response = client.post(
                "/api/auth/signup",
                json={
                    "email": f"signup{i}@example.com",
                    "password": "correct-horse",
                    "display_name": f"S{i}",
                },
            )
            statuses.append(response.status_code)

    assert statuses[:3] == [201] * 3
    assert statuses[3] == 429
