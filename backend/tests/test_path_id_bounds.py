"""Row ids arriving in the URL path, bounded the way body-side ones are.

`RowId` has bounded the body side since phase 4 of the static-analysis change,
where the contract fuzzer found that a `registration_id` of 2**63 overflowed
SQLite's INTEGER in the driver before any query could answer "no such row" —
an unhandled `OverflowError`, so a 500. The path side kept the same hole, and
kept it invisible: seeding the contract suite (tests/contract_seed.py)
substitutes real ids for generated ones, so the fuzzer stopped reaching a path
parameter with a value of its own choosing.

The first test is the one that matters over time. It reads the published schema
rather than a list, so a route added later with a bare `int` id fails here
without anyone remembering this file exists.
"""

from app.fieldtypes import ROW_ID_MAX
from app.main import app


def _integer_path_params():
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            for parameter in operation.get("parameters", []):
                schema = parameter.get("schema", {})
                if parameter.get("in") == "path" and schema.get("type") == "integer":
                    yield method.upper(), path, parameter["name"], schema


def test_every_integer_path_id_is_bounded():
    unbounded = [
        f"{method} {path} ({name})"
        for method, path, name, schema in _integer_path_params()
        if schema.get("minimum") != 1 or schema.get("maximum") != ROW_ID_MAX
    ]
    assert not unbounded, "unbounded integer path parameters: " + ", ".join(unbounded)


def test_an_oversized_path_id_is_refused_rather_than_crashing(client, auth_headers):
    """The behaviour the bound exists for: past the column, the answer is a
    422 naming the field, not an OverflowError raised inside the driver."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-10-17"},
        headers=organizer,
    )
    refused = client.delete(f"/api/tournaments/cup/team/{2**63}", headers=organizer)
    assert refused.status_code == 422, refused.text
    # the envelope reports the bound that was crossed, not both
    assert refused.json()["detail"]["errors"] == [
        {
            "field": "path.fencer_id",
            "code": "out_of_range",
            "params": {"max": ROW_ID_MAX},
        }
    ]
