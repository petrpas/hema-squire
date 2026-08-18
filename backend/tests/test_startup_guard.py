"""The application refuses to run with development secrets (deployment spec).

The failure this prevents is silent by construction: a deployment that forgets
HEMA_SQUIRE_SECRET_KEY works perfectly, and the only symptom is that anyone
holding the published repository key can forge a token for any account.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import DEV_SECRET_KEY, settings
from app.main import app


def test_dev_secret_key_refuses_to_boot(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", DEV_SECRET_KEY)
    monkeypatch.setattr(settings, "debug", False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        with TestClient(app):
            pass


def test_dev_secret_key_boots_in_debug(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", DEV_SECRET_KEY)
    monkeypatch.setattr(settings, "debug", True)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200


def test_production_secret_boots_without_debug(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "a" * 64)
    monkeypatch.setattr(settings, "debug", False)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
