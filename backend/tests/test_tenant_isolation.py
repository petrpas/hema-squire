"""Tenant isolation is held by a test, not by discipline (deployment spec).

Console access is designed correctly in app.auth, but enforced by each router
remembering to call require_console_access. This sweeps every console-scoped
endpoint as the organizer of a *different* tournament and asserts refusal, so a
new endpoint that forgets the check fails here rather than in production.

Endpoints are discovered from the route table, not listed: a new console
endpoint joins this test by existing. Discovery walks included routers rather
than app.routes directly, because this FastAPI version includes routers lazily.

Refusal means 403 exactly, and that strictness is the point. Neutralizing
require_console_access across the app turns all 47 of these routes from 403 into
404 — the handler proceeds and merely fails to find a sub-resource — except
DELETE /api/tournaments/{slug}, which succeeds with 204 and destroys another
organizer's tournament. So a test that accepted 404 as refusal would sit green
through the removal of every check but one. 404 is what a missing check looks
like here; 403 is what an enforced one looks like.
"""

import inspect

import pytest

from app.main import app

# Bodies for endpoints whose request schema has required fields. Without one,
# FastAPI answers 422 from body validation before the endpoint runs, so the
# tenant check is never reached and the sweep would pass vacuously. A new
# endpoint with a required body therefore fails this test until it is listed
# here — deliberately: that failure is the reminder.
BODIES: dict[tuple[str, str], object] = {
    ("POST", "/api/tournaments/{slug}/disciplines"): {
        "slug": "LS",
        "name": "Longsword",
        "weapon": "LS",
        "capacity": 10,
        "fee": 500,
    },
    ("PATCH", "/api/tournaments/{slug}/disciplines/{discipline_slug}"): {
        "weapon": "LS",
        "capacity": 10,
    },
    ("POST", "/api/tournaments/{slug}/extra-items"): {
        "name": "Rental",
        "category": "rental",
        "price": 100,
    },
    ("PATCH", "/api/tournaments/{slug}/extra-items/{item_id}"): {
        "name": "Rental",
        "category": "rental",
        "price": 100,
    },
    ("POST", "/api/tournaments/{slug}/import/dedup/decide"): {"key": "k", "accept": True},
    ("POST", "/api/tournaments/{slug}/manual-rows"): {
        "name": "Hand Entered",
        "disciplines": ["LS"],
    },
    ("POST", "/api/tournaments/{slug}/payments/link"): {"transaction_id": 1, "vs": [1]},
    ("POST", "/api/tournaments/{slug}/rules"): {
        "phase": "arrival",
        "kind": "note",
        "target": "all",
        "payload": {},
    },
    ("PATCH", "/api/tournaments/{slug}/rules/{rule_id}"): {"payload": {}},
    ("POST", "/api/tournaments/{slug}/transfer-ownership"): {"email": "someone@example.com"},
    ("POST", "/api/tournaments/{slug}/team"): {"email": "someone@example.com"},
    ("PATCH", "/api/tournaments/{slug}/mode"): {
        "feature_schedule": False,
        "feature_payments": False,
        "feature_teams": False,
        "feature_extras": False,
    },
}

# Endpoints taking an upload rather than a JSON body. The content is deliberately
# junk: every one of these checks console access before it looks at the file, and
# this test is what keeps that ordering true.
FILES: dict[tuple[str, str], dict] = {
    ("POST", "/api/tournaments/{slug}/logo"): {"file": ("logo.png", b"not-an-image", "image/png")},
    ("POST", "/api/tournaments/{slug}/import"): {"file": ("roster.csv", b"name\tclub", "text/csv")},
    ("POST", "/api/tournaments/{slug}/payments/import-statement"): {
        "file": ("statement.csv", b"date;amount", "text/csv")
    },
}

# Path parameters other than {slug}. The values need not exist: a foreign
# organizer must be refused before the lookup, and where the lookup happens
# first the result is the weaker 404 that this test reports separately.
PATH_PARAMS = {
    "discipline_slug": "LS",
    "registration_id": "1",
    "transaction_id": "1",
    "item_id": "1",
    "rule_id": "1",
    "fencer_id": "1",
}


def _walk(router, prefix=""):
    for route in getattr(router, "routes", []):
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            yield from _walk(included, prefix + (getattr(context, "prefix", "") or ""))
        elif getattr(route, "endpoint", None) is not None:
            yield prefix + route.path, route


def console_routes():
    """Every {slug}-scoped route whose handler consults console access."""
    found = []
    for path, route in _walk(app):
        if "{slug}" not in path:
            continue
        try:
            source = inspect.getsource(route.endpoint)
        except OSError:  # pragma: no cover - only for C-implemented endpoints
            continue
        if "require_console_access" not in source and "require_tournament_owner" not in source:
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            found.append((method, path))
    return sorted(set(found))


CONSOLE_ROUTES = console_routes()


@pytest.fixture
def two_tournaments(client, auth_headers):
    """Tournament A owned by one organizer, B by another, plus B's credentials."""
    owner_a = auth_headers(email="a@example.com", name="A")
    owner_b = auth_headers(email="b@example.com", name="B")
    for slug, headers in (("tournament-a", owner_a), ("tournament-b", owner_b)):
        created = client.post(
            "/api/tournaments",
            json={"slug": slug, "display_name": slug, "date": "2026-10-03"},
            headers=headers,
        )
        assert created.status_code == 201, created.text
    return client, owner_b


def _request(client, method, path, headers):
    url = path.replace("{slug}", "tournament-a")
    for name, value in PATH_PARAMS.items():
        url = url.replace("{" + name + "}", value)
    kwargs: dict = {"headers": headers}
    if (method, path) in FILES:
        kwargs["files"] = FILES[(method, path)]
    elif method in ("POST", "PATCH", "PUT"):
        kwargs["json"] = BODIES.get((method, path), {})
    return client.request(method, url, **kwargs)


def test_there_are_console_routes_to_sweep():
    """Guards the discovery itself: a route-table change that silently stops
    matching would otherwise turn this whole file into zero assertions."""
    assert len(CONSOLE_ROUTES) > 30


@pytest.mark.parametrize(
    ("method", "path"), CONSOLE_ROUTES, ids=[f"{m} {p}" for m, p in CONSOLE_ROUTES]
)
def test_foreign_organizer_is_refused(two_tournaments, method, path):
    client, owner_b = two_tournaments
    response = _request(client, method, path, owner_b)

    if response.status_code == 422:
        pytest.fail(
            f"{method} {path} answered 422 from body validation, so the tenant check never "
            f"ran. Add a valid request body for it to BODIES in this file."
        )
    assert response.status_code == 403, (
        f"{method} {path} answered {response.status_code} to an organizer of another "
        f"tournament, not 403. A 404 here means the handler ran and looked something "
        f"up instead of refusing: check that it calls require_console_access before "
        f"anything else. Response: {response.text[:200]}"
    )
