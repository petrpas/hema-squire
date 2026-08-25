"""Unit tests for `app.accounts`: parsing, checksums and conversion between
the Czech domestic form and IBAN (design `accept-czech-account-format`)."""

import pytest

from app import accounts

# the canonical Czech example IBAN (Wikipedia's ISO IBAN registry example),
# checksum-valid, whose BBAN is bankcode 0800 + prefix 000019 + number
# 2000145399
CZ_IBAN = "CZ6508000000192000145399"
CZ_DOMESTIC = "19-2000145399/0800"
# Germany's canonical example IBAN, for a non-Czech round trip
DE_IBAN = "DE89370400440532013000"


def test_domestic_with_prefix_converts_to_known_iban():
    assert accounts.parse(CZ_DOMESTIC) == CZ_IBAN


def test_iban_accepted_unchanged():
    assert accounts.parse(CZ_IBAN) == CZ_IBAN


def test_domestic_and_iban_of_one_account_normalize_identically():
    assert accounts.parse(CZ_DOMESTIC) == accounts.parse(CZ_IBAN)


def test_zero_prefix_domestic_account():
    parsed = accounts.parse("2000145399/0800")
    assert parsed.startswith("CZ")
    assert accounts.to_domestic(parsed) == "2000145399/0800"


def test_short_account_number_is_zero_padded():
    iban = accounts.to_iban("19", "107", "0100")
    assert iban == "CZ1101000000190000000107"
    assert accounts.valid_iban(iban)


def test_round_trip_domestic_to_iban_to_domestic():
    for domestic in (CZ_DOMESTIC, "2000145399/0800", "19-107/0100"):
        iban = accounts.parse(domestic)
        assert accounts.to_domestic(iban) == domestic


def test_spaces_around_the_separators_are_stripped():
    """Every space goes before the checksums run, so the domestic form typed
    with spaces parses identically to the compact one."""
    for spaced in ("19 - 2000145399 / 0800", "19-2000145399 / 0800", "19- 2000145399/0800"):
        assert accounts.parse(spaced) == CZ_IBAN


def test_to_domestic_none_for_non_czech_iban():
    assert accounts.to_domestic(DE_IBAN) is None


def test_display_shows_both_forms_for_czech_account():
    assert accounts.display(CZ_IBAN) == f"{CZ_DOMESTIC} ({CZ_IBAN})"


def test_display_shows_iban_alone_for_foreign_account():
    assert accounts.display(DE_IBAN) == DE_IBAN


def test_foreign_iban_accepted_as_is():
    assert accounts.parse(DE_IBAN) == DE_IBAN


def test_lowercase_and_spacing_normalized():
    assert accounts.parse(" cz65 0800 0000 1920 0014 5399 ") == CZ_IBAN
    assert accounts.parse(" 19-2000145399/0800 ") == CZ_IBAN


def test_bad_iban_checksum_rejected():
    with pytest.raises(accounts.AccountError, match="iban_checksum"):
        accounts.parse("CZ0008000000192000145399")


def test_bad_account_number_checksum_rejected():
    with pytest.raises(accounts.AccountError, match="account_checksum"):
        accounts.parse("19-2000145398/0800")


def test_bad_prefix_checksum_rejected():
    with pytest.raises(accounts.AccountError, match="account_checksum"):
        accounts.parse("20-2000145399/0800")


def test_unrecognized_shape_rejected():
    with pytest.raises(accounts.AccountError, match="format"):
        accounts.parse("not-an-account")


def test_valid_cz_part_zero_prefix_passes():
    assert accounts.valid_cz_part("0")


def test_iban_check_digits_matches_known_example():
    bban = "08000000192000145399"
    assert accounts.iban_check_digits(bban, "CZ") == "65"
