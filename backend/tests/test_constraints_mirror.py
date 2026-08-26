"""Guards `frontend/src/constraints.ts` against drifting away from the
bounds the backend actually publishes (design `add-field-validation` D1,
task 1.4).

Reads the OpenAPI schema FastAPI builds from `app/schemas.py` and compares
each request-body property's `maxLength`/`minLength`/`minimum`/`maximum`/
`exclusiveMinimum`/`exclusiveMaximum`/`enum` against the mirror's entry for
that field.

One constraint is deliberately excluded from this comparison: `pattern` on a
field whose type also carries a `BeforeValidator` (`bank_account`, the
discipline `slug`). Pydantic 2.13's JSON-schema renderer drops a bare
`pattern=` constraint from the rendered schema for such a field even though
it is enforced correctly at runtime — confirmed empirically while writing
this test (`model_json_schema()` omits it; `ValidationError` is still
raised). Since the schema this test would have to read is itself missing the
information, those two patterns are instead checked directly against
behavior in `test_discipline_slug_pattern.py` and below.
"""

import ast
import re
from pathlib import Path

import pytest

from app.main import app

MIRROR_PATH = (
    Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "constraints.ts"
)

# openapi component name, when it differs from the mirror's model name (the
# input/output split some models get from a field_serializer)
_COMPONENT_ALIASES = {
    "DiscountCondition": "DiscountCondition-Input",
    "DiscountIn": "DiscountIn-Input",
}

# (model, field) pairs that are legitimately unbounded: identifiers, foreign
# keys, and a free string checked dynamically at runtime rather than by a
# static bound (the language code, checked against the locale catalog)
_NO_BOUND_NEEDED = {
    ("SignupIn", "email"),
    ("SignupIn", "hr_id"),
    ("SignupIn", "language"),
    ("AccountUpdate", "email"),
    ("AccountUpdate", "language"),
    ("TournamentCreate", "language"),
    ("TournamentUpdate", "language"),
    ("TeamEntryIn", "id"),
    ("TeamEntryIn", "slug"),
    ("DisciplineIn", "ordinal"),
    ("RosterMemberIn", "hr_id"),
    ("ExtraSelectionIn", "extra_item_id"),
}

_REQUEST_MODELS = [
    "SignupIn",
    "AccountUpdate",
    "PleaIn",
    "DisciplineIn",
    "ExtraItemIn",
    "ExtraSelectionIn",
    "DiscountCondition",
    "DiscountEffect",
    "DiscountIn",
    "OrganizerIn",
    "TournamentCreate",
    "TournamentUpdate",
    "RuleIn",
    "TeamEntryIn",
    "RosterMemberIn",
]

_RAW_ALIASES = {
    "ge": "minimum",
    "le": "maximum",
    "gt": "exclusiveMinimum",
    "lt": "exclusiveMaximum",
}
_BOUND_KEYS = {
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "pattern",
    "enum",
}
# fields whose `pattern` this test cannot compare against the mirror:
# `bank_account` because pydantic's JSON-schema renderer drops a bare
# `pattern=` from a BeforeValidator-wrapped field even though it enforces it
# at runtime (see module docstring); `eur_rate` because Decimal's own JSON
# schema carries an internal numeric-string pattern that is not a bound this
# design declares — every other bound on these fields is still checked
_PATTERN_BLIND_SPOTS = {
    ("TournamentUpdate", "bank_account"),
    ("TournamentUpdate", "eur_rate"),
}

# fields with no runtime bound the schema walk can see at all: the
# discipline slug's alphabet and length are enforced by its own
# BeforeValidator (`_normalize_discipline_slug`), not by a `Field(...)`
# constraint — verified behaviorally in test_discipline_slug_pattern.py, not
# by this schema comparison
_SCHEMA_BLIND_SPOTS = {("DisciplineIn", "slug")}


def _collect_bounds(prop: dict, openapi_schemas: dict | None = None) -> dict:
    if "$ref" in prop and openapi_schemas is not None:
        ref_name = prop["$ref"].rsplit("/", 1)[-1]
        return _collect_bounds(openapi_schemas.get(ref_name, {}), openapi_schemas)
    out: dict = {}
    for key, value in prop.items():
        key = _RAW_ALIASES.get(key, key)
        if key in _BOUND_KEYS:
            out.setdefault(key, value)
    for branch in prop.get("anyOf", []):
        if branch.get("type") == "null":
            continue
        for key, value in _collect_bounds(branch, openapi_schemas).items():
            out.setdefault(key, value)
    return out


def _prop_type(prop: dict) -> str | None:
    if "type" in prop:
        return prop["type"]
    for branch in prop.get("anyOf", []):
        branch_type = branch.get("type")
        if branch_type not in (None, "null"):
            return branch_type
    return None


def _is_temporal(prop: dict) -> bool:
    """A date, an instant, or a time of day. Its format is its bound: there is
    no length or range for the design to declare on top of it."""
    if prop.get("format") in ("date", "date-time", "time"):
        return True
    return any(_is_temporal(branch) for branch in prop.get("anyOf", []))


def _load_mirror() -> dict:
    text = MIRROR_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"export const FIELD_CONSTRAINTS: Record<string, FieldConstraint> = (\{.*?\n\});",
        text,
        re.DOTALL,
    )
    assert match, "FIELD_CONSTRAINTS block not found in constraints.ts"
    # every key and value in the block is a quoted string, a number, or a
    # nested object of the same — valid Python dict literal syntax too
    return ast.literal_eval(match.group(1))


@pytest.fixture(scope="module")
def openapi_schemas():
    return app.openapi()["components"]["schemas"]


@pytest.fixture(scope="module")
def mirror():
    return _load_mirror()


def _iter_model_fields(openapi_schemas, model):
    component = _COMPONENT_ALIASES.get(model, model)
    return openapi_schemas[component]["properties"].items()


def test_every_mirrored_bound_matches_backend(openapi_schemas, mirror):
    mismatches = []
    for model in _REQUEST_MODELS:
        for field, prop in _iter_model_fields(openapi_schemas, model):
            key = f"{model}.{field}"
            if key not in mirror or (model, field) in _SCHEMA_BLIND_SPOTS:
                continue
            backend_bounds = _collect_bounds(prop, openapi_schemas)
            mirror_bounds = dict(mirror[key])
            if (model, field) in _PATTERN_BLIND_SPOTS:
                backend_bounds.pop("pattern", None)
                mirror_bounds.pop("pattern", None)
            if backend_bounds != mirror_bounds:
                mismatches.append((key, backend_bounds, mirror_bounds))
    assert not mismatches, "\n".join(
        f"{key}: backend={backend!r} mirror={mirror!r}" for key, backend, mirror in mismatches
    )


def test_every_editable_scalar_field_has_a_bound(openapi_schemas, mirror):
    unbounded = []
    for model in _REQUEST_MODELS:
        for field, prop in _iter_model_fields(openapi_schemas, model):
            if (model, field) in _NO_BOUND_NEEDED:
                continue
            if _is_temporal(prop):
                continue
            prop_type = _prop_type(prop)
            if prop_type not in ("string", "integer", "number"):
                continue
            key = f"{model}.{field}"
            if key not in mirror and not _collect_bounds(prop, openapi_schemas):
                unbounded.append(key)
    assert not unbounded, f"editable field(s) with no declared bound: {unbounded}"


def test_hr_category_map_keys_and_values_are_bounded(openapi_schemas, mirror):
    prop = dict(_iter_model_fields(openapi_schemas, "TournamentUpdate"))["hr_category_map"]
    for branch in prop["anyOf"]:
        if branch.get("type") == "object":
            assert (
                branch["propertyNames"]["maxLength"]
                == mirror["TournamentUpdate.hr_category_map_key"]["maxLength"]
            )
            assert (
                branch["additionalProperties"]["maxLength"]
                == mirror["TournamentUpdate.hr_category_map_value"]["maxLength"]
            )
            return
    pytest.fail("hr_category_map has no object branch")


def test_bank_account_pattern_enforced_despite_schema_blind_spot(client, auth_headers):
    """`bank_account`'s pattern is invisible to the schema walk above (see
    module docstring) — checked behaviorally instead."""
    headers = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=headers,
    )
    rejected = client.patch(
        "/api/tournaments/cup", json={"bank_account": "not-an-iban"}, headers=headers
    )
    assert rejected.status_code == 422
    accepted = client.patch(
        "/api/tournaments/cup",
        json={"bank_account": "CZ6508000000192000145399"},
        headers=headers,
    )
    assert accepted.status_code == 200
