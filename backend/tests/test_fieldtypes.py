"""Tests for the shared pydantic field types (design `add-field-validation`
D2, D4): tolerant numeric parsing, the global string rules, and the
scheme-restricted URL type — task 2.5."""

import pytest
from pydantic import BaseModel, ValidationError

from app.fieldtypes import HttpUrlStr, MultilineStr, SingleLineStr, TolerantDecimal, TolerantInt


class _Decimal(BaseModel):
    value: TolerantDecimal


class _Int(BaseModel):
    value: TolerantInt


class _SingleLine(BaseModel):
    value: SingleLineStr(20)


class _Multiline(BaseModel):
    value: MultilineStr(20)


class _Url(BaseModel):
    value: HttpUrlStr(200)


def _error_code(exc: ValidationError) -> str:
    error = exc.value.errors()[0]
    if error["type"] == "value_error":
        return str(error["ctx"]["error"])
    return error["type"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("25,5", "25.5"),
        ("25.5", "25.5"),
        ("1 250", "1250"),
        ("1 250", "1250"),
        ("1 250", "1250"),
        ("0", "0"),
        ("-5", "-5"),
    ],
)
def test_tolerant_decimal_accepts(raw, expected):
    import decimal

    assert _Decimal(value=raw).value == decimal.Decimal(expected)


@pytest.mark.parametrize("raw", ["2,5,5", "12a", ".5", "5.", "", "1,2.3", "abc"])
def test_tolerant_decimal_rejects_malformed(raw):
    with pytest.raises(ValidationError) as exc:
        _Decimal(value=raw)
    assert _error_code(exc) == "not_a_number"


def test_tolerant_int_accepts_whole_values_either_separator():
    assert _Int(value="4").value == 4
    assert _Int(value="4,0").value == 4
    assert _Int(value="4.0").value == 4
    assert _Int(value="1 250").value == 1250


def test_tolerant_int_rejects_fraction_as_must_be_whole():
    with pytest.raises(ValidationError) as exc:
        _Int(value="3,5")
    assert _error_code(exc) == "must_be_whole"


def test_tolerant_int_rejects_malformed_as_not_a_number():
    with pytest.raises(ValidationError) as exc:
        _Int(value="2,5,5")
    assert _error_code(exc) == "not_a_number"


def test_single_line_trims_and_collapses_whitespace():
    assert _SingleLine(value="  Prague  ").value == "Prague"
    assert _SingleLine(value="a   b\t\nc").value == "a b c"


def test_single_line_rejects_zero_width_joiner():
    with pytest.raises(ValidationError) as exc:
        _SingleLine(value="a‍joined")
    assert _error_code(exc) == "forbidden_characters"


def test_single_line_rejects_control_character():
    with pytest.raises(ValidationError) as exc:
        _SingleLine(value="a\x07b")
    assert _error_code(exc) == "forbidden_characters"


def test_multiline_keeps_line_breaks_but_trims_ends():
    assert _Multiline(value="  line one\nline two  ").value == "line one\nline two"


def test_url_accepts_http_and_https():
    assert _Url(value="http://example.com/rules").value == "http://example.com/rules"
    assert _Url(value="https://example.com").value == "https://example.com"


def test_url_rejects_javascript_scheme():
    with pytest.raises(ValidationError) as exc:
        _Url(value="javascript:alert(1)")
    assert _error_code(exc) == "bad_link_scheme"


def test_url_rejects_data_scheme():
    with pytest.raises(ValidationError) as exc:
        _Url(value="data:text/html;base64,QQ==")
    assert _error_code(exc) == "bad_link_scheme"


def test_url_rejects_missing_scheme_as_malformed():
    with pytest.raises(ValidationError) as exc:
        _Url(value="example.com/rules")
    assert _error_code(exc) == "bad_url"
