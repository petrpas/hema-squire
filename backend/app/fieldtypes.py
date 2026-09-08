"""Shared pydantic field types for `app/schemas.py` (design `add-field-validation`
D2, D4, D6): a tolerant numeric parser accepting either decimal separator, a
string type applying the global whitespace/control-character rules, and a
scheme-restricted URL type. Each raises `ValueError` with one of the closed
validation codes (see `app/errors.py`) as its message, so the
`RequestValidationError` handler can read the code straight off the error.
"""

from __future__ import annotations

import datetime
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


def _stamp_utc(value: datetime.datetime | None) -> datetime.datetime | None:
    """Stamp UTC on an instant SQLite handed back naive.

    Every instant Squire records is UTC, but SQLite drops tzinfo on round-trip
    even for a `DateTime(timezone=True)` column. Serialized without a zone, a
    client reads the instant as its own local time and states the wrong hour —
    the failure `rules._utc` already fixes for the manual-edits log, and the
    contract fuzzer caught again on the account plea (phase 4 of the
    static-analysis change).

    Only for instants Squire itself recorded. A stamp imported from someone
    else's table has no zone to restore and is deliberately shown unshifted
    (`frontend/src/consoleCells.test.tsx`, "an imported row's zone-less stamp"),
    so those fields must not use this type.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=datetime.UTC)


# An instant Squire recorded, serialized with the zone it was recorded in.
UtcInstant = Annotated[datetime.datetime, AfterValidator(_stamp_utc)]


# Each alias below is a single `Field(...)` call. Stacking a second one at the
# assignment site silently drops the first's constraints from the generated
# JSON schema, even though both still validate at runtime — so a field's bound
# belongs here, in its alias, and nowhere else.
#
# These are plain `Annotated` aliases rather than factory functions taking a
# length, because a call expression is not valid in a type annotation: pyright
# rejects `club: SingleLineStr(N)` outright, and no suppression makes that
# shape check (design `add-field-validation` D4, restated for static analysis).

# A trimmed, whitespace-collapsed, control-character-free string (design D4).
# Used for every single-line editable field.
SingleLine = BeforeValidator(_clean_single_line)
# The same, keeping internal line breaks — for markdown bodies and other
# multi-line fields (design D4).
Multiline = BeforeValidator(_clean_multiline)

DisplayNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.DISPLAY_NAME_MAX_LENGTH,
        min_length=constraints.DISPLAY_NAME_MIN_LENGTH,
    ),
]
ClubStr = Annotated[str, SingleLine, Field(max_length=constraints.CLUB_MAX_LENGTH)]

DisciplineNameStr = Annotated[
    str, SingleLine, Field(max_length=constraints.DISCIPLINE_NAME_MAX_LENGTH)
]
DisciplineWeaponStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.DISCIPLINE_WEAPON_MAX_LENGTH,
        min_length=constraints.DISCIPLINE_WEAPON_MIN_LENGTH,
    ),
]
DisciplineRulesetStr = Annotated[
    str, SingleLine, Field(max_length=constraints.DISCIPLINE_RULESET_MAX_LENGTH)
]
DisciplineScheduleWhenStr = Annotated[
    str, SingleLine, Field(max_length=constraints.DISCIPLINE_SCHEDULE_WHEN_MAX_LENGTH)
]
DisciplineScheduleWhereStr = Annotated[
    str, SingleLine, Field(max_length=constraints.DISCIPLINE_SCHEDULE_WHERE_MAX_LENGTH)
]

ExtraItemNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.EXTRA_ITEM_NAME_MAX_LENGTH,
        min_length=constraints.EXTRA_ITEM_NAME_MIN_LENGTH,
    ),
]
ExtraItemOptionLabelStr = Annotated[
    str, SingleLine, Field(max_length=constraints.EXTRA_ITEM_OPTION_LABEL_MAX_LENGTH)
]
ExtraItemScheduleWhenStr = Annotated[
    str, SingleLine, Field(max_length=constraints.EXTRA_ITEM_SCHEDULE_WHEN_MAX_LENGTH)
]
ExtraItemScheduleWhereStr = Annotated[
    str, SingleLine, Field(max_length=constraints.EXTRA_ITEM_SCHEDULE_WHERE_MAX_LENGTH)
]
OptionValueStr = Annotated[str, SingleLine, Field(max_length=constraints.OPTION_VALUE_MAX_LENGTH)]

DiscountNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.DISCOUNT_NAME_MAX_LENGTH,
        min_length=constraints.DISCOUNT_NAME_MIN_LENGTH,
    ),
]
OrganizerNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.ORGANIZER_NAME_MAX_LENGTH,
        min_length=constraints.ORGANIZER_NAME_MIN_LENGTH,
    ),
]

TournamentDisplayNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.TOURNAMENT_DISPLAY_NAME_MAX_LENGTH,
        min_length=constraints.TOURNAMENT_DISPLAY_NAME_MIN_LENGTH,
    ),
]
TournamentSubtitleStr = Annotated[
    str, SingleLine, Field(max_length=constraints.TOURNAMENT_SUBTITLE_MAX_LENGTH)
]
TournamentLocationStr = Annotated[
    str, SingleLine, Field(max_length=constraints.TOURNAMENT_LOCATION_MAX_LENGTH)
]
BankAccountStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.TOURNAMENT_BANK_ACCOUNT_MAX_LENGTH,
        pattern=constraints.BANK_ACCOUNT_PATTERN,
    ),
]
FioTokenStr = Annotated[
    str, SingleLine, Field(max_length=constraints.TOURNAMENT_FIO_TOKEN_MAX_LENGTH)
]
HrCategoryKeyStr = Annotated[
    str, SingleLine, Field(max_length=constraints.HR_CATEGORY_MAP_KEY_MAX_LENGTH)
]
HrCategoryValueStr = Annotated[
    str, SingleLine, Field(max_length=constraints.HR_CATEGORY_MAP_VALUE_MAX_LENGTH)
]

TeamNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.TEAM_NAME_MAX_LENGTH,
        min_length=constraints.TEAM_NAME_MIN_LENGTH,
    ),
]
RosterMemberNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.ROSTER_MEMBER_NAME_MAX_LENGTH,
        min_length=constraints.ROSTER_MEMBER_NAME_MIN_LENGTH,
    ),
]
RosterMemberClubStr = Annotated[
    str, SingleLine, Field(max_length=constraints.ROSTER_MEMBER_CLUB_MAX_LENGTH)
]
RosterMemberNationalityStr = Annotated[
    str, SingleLine, Field(max_length=constraints.ROSTER_MEMBER_NATIONALITY_MAX_LENGTH)
]

ManualEntryNameStr = Annotated[
    str,
    SingleLine,
    Field(
        max_length=constraints.MANUAL_ENTRY_NAME_MAX_LENGTH,
        min_length=constraints.MANUAL_ENTRY_NAME_MIN_LENGTH,
    ),
]
ManualEntryClubStr = Annotated[
    str, SingleLine, Field(max_length=constraints.MANUAL_ENTRY_CLUB_MAX_LENGTH)
]
ManualEntryNationalityStr = Annotated[
    str, SingleLine, Field(max_length=constraints.MANUAL_ENTRY_NATIONALITY_MAX_LENGTH)
]

PleaMessageStr = Annotated[str, Multiline, Field(max_length=constraints.PLEA_MESSAGE_MAX_LENGTH)]
ExtraItemRemarkStr = Annotated[
    str, Multiline, Field(max_length=constraints.EXTRA_ITEM_REMARK_MAX_LENGTH)
]
ManualEntryNotesStr = Annotated[
    str, Multiline, Field(max_length=constraints.MANUAL_ENTRY_NOTES_MAX_LENGTH)
]
TournamentDescriptionStr = Annotated[
    str, Multiline, Field(max_length=constraints.TOURNAMENT_DESCRIPTION_MAX_LENGTH)
]
TournamentQualificationCriteriaStr = Annotated[
    str,
    Multiline,
    Field(max_length=constraints.TOURNAMENT_QUALIFICATION_CRITERIA_MAX_LENGTH),
]
TournamentRegistrationInstructionsStr = Annotated[
    str,
    Multiline,
    Field(max_length=constraints.TOURNAMENT_REGISTRATION_INSTRUCTIONS_MAX_LENGTH),
]


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


# A link field: SHALL parse as a URL and SHALL carry only an `http`/`https`
# scheme (design: URL fields are parsed and scheme-restricted). `javascript:`/
# `data:` and other schemes are rejected as `bad_link_scheme`; a value that
# does not parse as a URL at all is `bad_url`.
HttpUrl = AfterValidator(_validate_http_url)

OrganizerLinkStr = Annotated[
    str, SingleLine, HttpUrl, Field(max_length=constraints.ORGANIZER_LINK_MAX_LENGTH)
]
ExternalRegistrationUrlStr = Annotated[
    str,
    SingleLine,
    HttpUrl,
    Field(max_length=constraints.EXTERNAL_REGISTRATION_URL_MAX_LENGTH),
]
OutputSheetUrlStr = Annotated[
    str,
    SingleLine,
    HttpUrl,
    Field(max_length=constraints.TOURNAMENT_OUTPUT_SHEET_URL_MAX_LENGTH),
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


# The discipline slug field, normalized ahead of its own pattern check (design
# D6). The pattern and length are enforced by `_normalize_discipline_slug`
# itself (restricted alphabet, truncation) rather than by a `Field(...)`
# constraint here: attaching `Field(pattern=..., max_length=...)` to a
# `str | None` union applies the constraint to the `None` branch too and
# crashes, since normalizing to nothing returns `None` (the router's existing
# fallback to a generated slug then applies).
DisciplineSlug = Annotated[str | None, BeforeValidator(_normalize_discipline_slug)]


__all__ = [
    "BankAccountStr",
    "ClubStr",
    "DisciplineNameStr",
    "DisciplineRulesetStr",
    "DisciplineScheduleWhenStr",
    "DisciplineScheduleWhereStr",
    "DisciplineSlug",
    "DisciplineWeaponStr",
    "DiscountNameStr",
    "DisplayNameStr",
    "ExternalRegistrationUrlStr",
    "ExtraItemNameStr",
    "ExtraItemOptionLabelStr",
    "ExtraItemRemarkStr",
    "ExtraItemScheduleWhenStr",
    "ExtraItemScheduleWhereStr",
    "FioTokenStr",
    "HrCategoryKeyStr",
    "HrCategoryValueStr",
    "ManualEntryClubStr",
    "ManualEntryNameStr",
    "ManualEntryNationalityStr",
    "ManualEntryNotesStr",
    "Multiline",
    "OptionValueStr",
    "OrganizerLinkStr",
    "OrganizerNameStr",
    "OutputSheetUrlStr",
    "PleaMessageStr",
    "RosterMemberClubStr",
    "RosterMemberNameStr",
    "RosterMemberNationalityStr",
    "SingleLine",
    "TeamNameStr",
    "TolerantDecimal",
    "UtcInstant",
    "TolerantInt",
    "TournamentDescriptionStr",
    "TournamentDisplayNameStr",
    "TournamentLocationStr",
    "TournamentQualificationCriteriaStr",
    "TournamentRegistrationInstructionsStr",
    "TournamentSubtitleStr",
]
