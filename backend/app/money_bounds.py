"""The per-currency money ceiling (design `add-field-validation` D4/2.4a): a
local-currency money field cannot carry a static `Field(le=...)` bound
because its ceiling depends on which currency the *tournament* is
denominated in. This is therefore a router-time check, resolved from the
tournament's `local_currency` rather than baked into the schema."""

from __future__ import annotations

from app import constraints
from app.models import Tournament


def local_money_error(tournament: Tournament, field: str, value: int | None) -> dict | None:
    """A field-error entry if `value` (already known non-negative by the
    schema) exceeds the ceiling for the tournament's local currency, so the
    message can state the maximum that actually applies (design 2.4a)."""
    if value is None:
        return None
    ceiling = constraints.MONEY_MAX[str(tournament.local_currency)]
    if value > ceiling:
        return {"field": field, "code": "out_of_range", "params": {"min": 0, "max": ceiling}}
    return None


def collect_local_money_errors(tournament: Tournament, fields: dict[str, int | None]) -> list[dict]:
    errors = []
    for field, value in fields.items():
        error = local_money_error(tournament, field, value)
        if error is not None:
            errors.append(error)
    return errors
