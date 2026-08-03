"""Translates pydantic's `RequestValidationError` and the router's existing
`HTTPException(detail="snake_case")` codes into one response envelope:

    {"detail": {"errors": [{"field": ..., "code": ..., "params": {...}}]}}

`field` is pydantic's own dotted path with the leading `body` segment
dropped, so a client can address a row inside a list (design
`add-field-validation` D3). `code` is one of a closed set for anything caught
by a declared constraint (see `_TYPE_CODE_MAP`), or — for a `ValueError`
raised by one of our own `BeforeValidator`/`model_validator` functions — the
raised message itself, which is already one of those codes or, for a router
check with no field-level equivalent, its own snake_case name.

Router codes not named in `_ROUTER_CODE_FIELDS` are left exactly as they are
today (a bare string in `detail`) — the bare-string form stays readable by
the client for anything not yet converted, so the migration is incremental.
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class FieldValueError(ValueError):
    """Raised from a `model_validator` for a cross-field bound that cannot be
    expressed as a plain `Field(...)` constraint (a discipline capacity
    ceiling that depends on `kind`, an extra item's `max_qty` ceiling that
    depends on `category`) — carries the same `code`/`params` a declared
    constraint would, rather than leaving `params` empty like a bare
    `ValueError(code)`.

    `field` names the offending field explicitly: a whole-model
    `@model_validator(mode="after")` reports its error at the model's own
    (empty) location, not at any one field, so `field` is not optional here
    the way it is for a single-field validator."""

    def __init__(self, field: str, code: str, params: dict | None = None) -> None:
        self.field = field
        self.code = code
        self.params = params or {}
        super().__init__(code)

# pydantic error `type` -> one of the closed validation codes (design D3).
# "value_error" is deliberately absent: our own validators raise
# ValueError(code) directly, so the code is read from the error's message.
_TYPE_CODE_MAP = {
    "missing": "required",
    "string_too_short": "too_short",
    "string_too_long": "too_long",
    "too_short": "too_short",  # list/collection min_length
    "too_long": "too_long",  # list/collection max_length
    "greater_than_equal": "out_of_range",
    "less_than_equal": "out_of_range",
    "greater_than": "out_of_range",
    "less_than": "out_of_range",
    "decimal_max_digits": "out_of_range",
    "decimal_whole_digits": "out_of_range",
    "string_pattern_mismatch": "bad_pattern",
    "enum": "bad_enum",
    "literal_error": "bad_enum",
    "date_from_datetime_parsing": "bad_date",
    "date_parsing": "bad_date",
    "value_error.email": "bad_email",
    "int_parsing": "not_a_number",
    "float_parsing": "not_a_number",
    "decimal_parsing": "not_a_number",
    "int_type": "not_a_number",
    "float_type": "not_a_number",
}

# named router codes that address a specific field (task 3.3); anything else
# stays a bare-string `detail`, unwrapped, exactly as before this change
_ROUTER_CODE_FIELDS = {
    "slug_taken": "slug",
    "qualification_criteria_required": "qualification_criteria",
    "discipline_slug_taken": "slug",
    "discipline_slug_frozen": "slug",
    "discipline_kind_frozen": "kind",
    "discipline_name_required": "name",
    "amendments_close_after_registration_closes": "amendments_close",
    "legacy_fixed_fees_block_eur": "eur_payments_enabled",
}

_CTX_MIN_KEYS = ("min_length", "ge", "gt")
_CTX_MAX_KEYS = ("max_length", "le", "lt")


def _params_from_ctx(ctx: dict) -> dict:
    params: dict = {}
    for key in _CTX_MIN_KEYS:
        if key in ctx:
            params["min"] = ctx[key]
            break
    for key in _CTX_MAX_KEYS:
        if key in ctx:
            params["max"] = ctx[key]
            break
    if "pattern" in ctx:
        params["pattern"] = ctx["pattern"]
    if "expected" in ctx:
        params["expected"] = ctx["expected"]
    return params


def _field_path(loc: tuple) -> str:
    if loc and loc[0] == "body":
        loc = loc[1:]
    return ".".join(str(part) for part in loc)


def _pydantic_error_to_entry(error: dict) -> dict:
    field = _field_path(error["loc"])
    error_type = error["type"]
    if error_type == "value_error":
        ctx = error.get("ctx") or {}
        raw = ctx.get("error")
        if isinstance(raw, FieldValueError):
            # a whole-model validator reports at the model's own (empty)
            # location; the exception itself names the actual field
            entry_field = f"{field}.{raw.field}" if field else raw.field
            return {"field": entry_field, "code": raw.code, "params": raw.params}
        code = str(raw) if raw is not None else "invalid"
        return {"field": field, "code": code, "params": {}}
    code = _TYPE_CODE_MAP.get(error_type, error_type)
    params = _params_from_ctx(error.get("ctx") or {})
    return {"field": field, "code": code, "params": params}


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [_pydantic_error_to_entry(error) for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": {"errors": errors}})


def _split_conflict_detail(detail: str) -> tuple[str, str | None]:
    if ":" in detail:
        code, _, rest = detail.partition(":")
        return code.strip(), rest.strip()
    return detail, None


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        code, conflict = _split_conflict_detail(detail)
        field = _ROUTER_CODE_FIELDS.get(code)
        if field is not None:
            params = {"value": conflict} if conflict is not None else {}
            content = {"detail": {"errors": [{"field": field, "code": code, "params": params}]}}
            return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


class FieldValidationError(Exception):
    """For a check that cannot be expressed as a pydantic constraint — the
    money ceiling, resolved per request from the tournament's currency
    (design 2.4a) — a router raises this directly with its own
    `{field, code, params}` entries, delivered in the same envelope."""

    def __init__(self, errors: list[dict], status_code: int = 422) -> None:
        self.errors = errors
        self.status_code = status_code


async def field_validation_error_handler(
    request: Request, exc: FieldValidationError
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": {"errors": exc.errors}})
