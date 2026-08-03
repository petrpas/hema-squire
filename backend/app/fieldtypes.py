"""Shared pydantic field types for `app/schemas.py` (design `add-field-validation`
D2, D4, D6): a tolerant numeric parser accepting either decimal separator, a
string type applying the global whitespace/control-character rules, and a
scheme-restricted URL type. Each raises `ValueError` with one of the closed
validation codes (see `app/errors.py`) as its message, so the
`RequestValidationError` handler can read the code straight off the error.
"""

from __future__ import annotations

import decimal
import re
import unicodedata
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator, BeforeValidator, Field

from app import constraints

_GROUPING_CHARS = "   "
_NUMBER_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")

# C0/C1 controls excluding tab/LF/CR, which are legitimate whitespace in text
# (single-line fields collapse them to a space below; multiline fields keep
# LF as a line break)
_C0_C1_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# zero-width space, ZWNJ, ZWJ, word joiner, BOM/ZWNBSP
_ZERO_WIDTH_JOINERS = re.compile(r"[​-‍⁠﻿]")


def _strip_grouping(raw: str) -> str:
    for ch in _GROUPING_CHARS:
        raw = raw.replace(ch, "")
    return raw.strip()


def _normalize_numeric_text(raw: str) -> str:
    """Common ground for `TolerantDecimal` and `TolerantInt`: strip thousands
    grouping, accept exactly one `,` or `.` as the decimal separator and
    normalize it to `.`. Raises `not_a_number` on anything else (design D2)."""
    text = _strip_grouping(raw)
    if not text:
        raise ValueError("not_a_number")
    comma_count = text.count(",")
    dot_count = text.count(".")
    if comma_count + dot_count > 1:
        raise ValueError("not_a_number")
    if comma_count == 1:
        text = text.replace(",", ".")
    if not _NUMBER_RE.match(text):
        raise ValueError("not_a_number")
    if text.startswith(".") or text.startswith("-.") or text.endswith("."):
        raise ValueError("not_a_number")
    return text


def _coerce_decimal(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = _normalize_numeric_text(value)
    try:
        return decimal.Decimal(text)
    except decimal.InvalidOperation as exc:
        raise ValueError("not_a_number") from exc


def _coerce_int(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = _normalize_numeric_text(value)
    as_decimal = decimal.Decimal(text)
    if as_decimal != as_decimal.to_integral_value():
        raise ValueError("must_be_whole")
    return int(as_decimal)


# `,` or `.` accepted interchangeably, space/NBSP/narrow-NBSP thousands
# grouping tolerated, two separators or stray characters rejected as
# `not_a_number`; a non-whole value into an integer field is `must_be_whole`
# rather than silently rounded (design D2).
TolerantDecimal = Annotated[decimal.Decimal, BeforeValidator(_coerce_decimal)]
TolerantInt = Annotated[int, BeforeValidator(_coerce_int)]


def _clean_string(value: object, *, collapse_whitespace: bool) -> object:
    if not isinstance(value, str):
        return value
    if _C0_C1_CONTROLS.search(value) or _ZERO_WIDTH_JOINERS.search(value):
        raise ValueError("forbidden_characters")
    trimmed = value.strip()
    if collapse_whitespace:
        trimmed = re.sub(r"\s+", " ", trimmed)
    return trimmed


def _clean_single_line(value: object) -> object:
    return _clean_string(value, collapse_whitespace=True)


def _clean_multiline(value: object) -> object:
    return _clean_string(value, collapse_whitespace=False)


def SingleLineStr(max_length: int, *, min_length: int | None = None, pattern: str | None = None) -> type:
    """A trimmed, whitespace-collapsed, control-character-free string bounded
    to `max_length` (design D4). Used for every single-line editable field.
    Every constraint is a single `Field(...)` call — stacking a second one at
    the assignment site silently drops the first's constraints from the
    generated JSON schema, even though both still validate at runtime."""
    return Annotated[
        str,
        BeforeValidator(_clean_single_line),
        Field(max_length=max_length, min_length=min_length, pattern=pattern),
    ]


def MultilineStr(max_length: int) -> type:
    """A trimmed, control-character-free string that keeps internal line
    breaks — for markdown bodies and other multi-line fields (design D4)."""
    return Annotated[str, BeforeValidator(_clean_multiline), Field(max_length=max_length)]


_ALLOWED_URL_SCHEMES = {"http", "https"}


def _validate_http_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise ValueError("bad_url") from exc
    if not parts.scheme:
        raise ValueError("bad_url")
    if parts.scheme not in _ALLOWED_URL_SCHEMES:
        raise ValueError("bad_link_scheme")
    if not parts.netloc:
        raise ValueError("bad_url")
    return value


def HttpUrlStr(max_length: int) -> type:
    """A link field: SHALL parse as a URL and SHALL carry only an `http`/
    `https` scheme (design: URL fields are parsed and scheme-restricted).
    `javascript:`/`data:` and other schemes are rejected as `bad_link_scheme`;
    a value that does not parse as a URL at all is `bad_url`."""
    return Annotated[
        str,
        BeforeValidator(_clean_single_line),
        AfterValidator(_validate_http_url),
        Field(max_length=max_length),
    ]


def _normalize_discipline_slug(value: object) -> object:
    """Fold a slug into the alphabet the discipline slug pattern accepts:
    diacritics folded to ASCII, every run outside letters/digits/`-` collapsed
    to a single `-`, leading/trailing `-` stripped, and truncated to the
    column width. Ported from `app.taxonomy.normalize_slug` and moved ahead of
    the field's `pattern=` (design D6, task 8a.1) — normalization must run
    before the pattern check, or an override such as "Sword & Buckler
    (variant)" would be rejected before it could be folded into
    "Sword-Buckler-variant". Normalizing to nothing (or to nothing after
    truncation) becomes None, so the router's existing fallback to a
    generated slug still applies instead of a pattern rejection."""
    if not isinstance(value, str):
        return value
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^A-Za-z0-9-]+", "-", folded).strip("-")
    if len(collapsed) > constraints.DISCIPLINE_SLUG_MAX_LENGTH:
        collapsed = collapsed[: constraints.DISCIPLINE_SLUG_MAX_LENGTH].rstrip("-")
    return collapsed or None


def DisciplineSlugStr() -> type:
    """The discipline slug field, normalized ahead of its own pattern check
    (design D6). The pattern and length are enforced by `_normalize_discipline_slug`
    itself (restricted alphabet, truncation) rather than by a `Field(...)`
    constraint here: attaching `Field(pattern=..., max_length=...)` to a
    `str | None` union applies the constraint to the `None` branch too and
    crashes, since normalizing to nothing returns `None` (the router's
    existing fallback to a generated slug then applies)."""
    return Annotated[str | None, BeforeValidator(_normalize_discipline_slug)]


__all__ = [
    "DisciplineSlugStr",
    "HttpUrlStr",
    "MultilineStr",
    "SingleLineStr",
    "TolerantDecimal",
    "TolerantInt",
]
