import os

os.environ["HEMA_SQUIRE_SCHEDULER_ENABLED"] = "false"
os.environ["HEMA_SQUIRE_HR_AUTO_REFRESH"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.hr_index import get_hr_index, stub_index
from app.main import app
from app.models import Fencer, Role


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine):
    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    # tests run on the stub fixture dataset; hr-integration tests override this
    app.dependency_overrides[get_hr_index] = stub_index
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


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
