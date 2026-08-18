"""Bank account parsing, validation and display for both accepted forms: an
IBAN, or the Czech domestic form `[prefix-]number/bankcode` (design
`accept-czech-account-format`). No dependency on models or schemas — this
module converts and validates strings only; `app/schemas.py` is the only
caller that stores the result.

The stored form is always a canonical IBAN (design Decision 1); the domestic
form is derived on demand from a `CZ` IBAN and never stored a second time.
"""

import re

# ISO 7064 mod-97-10, applied from the rightmost digit after moving the
# first four characters to the end (design Decision 3)
_IBAN_SHAPE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Za-z0-9]{10,30}$")
# prefix (optional, 1-6 digits) - number (2-10 digits) / bankcode (4 digits)
_DOMESTIC_SHAPE = re.compile(r"^(?:([0-9]{1,6})-)?([0-9]{2,10})/([0-9]{4})$")

# ČNB weighted modulo-11, applied from the rightmost digit (design Decision 3)
_CZ_WEIGHTS = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]


class AccountError(ValueError):
    """Raised by `parse` naming the failed check — `iban_checksum`,
    `account_checksum` or `format` — so the message is already the code a
    field_validator's ValueError(...) should carry."""


def _to_numeric(value: str) -> str:
    """`A`-`Z` -> `10`-`35`, digits unchanged (ISO 7064 letter mapping)."""
    return "".join(str(ord(char) - 55) if char.isalpha() else char for char in value)


def iban_check_digits(bban: str, country: str) -> str:
    rearranged = bban + country + "00"
    return f"{98 - (int(_to_numeric(rearranged)) % 97):02d}"


def valid_iban(value: str) -> bool:
    if not _IBAN_SHAPE.match(value):
        return False
    rearranged = value[4:] + value[:4]
    return int(_to_numeric(rearranged)) % 97 == 1


def valid_cz_part(digits: str) -> bool:
    # strict=False on purpose: an account part is shorter than the weight table
    # whenever it has fewer than ten digits, and the surplus weights go unused
    total = sum(
        int(digit) * weight
        for digit, weight in zip(reversed(digits), _CZ_WEIGHTS, strict=False)
    )
    return total % 11 == 0


def to_iban(prefix: str, number: str, bankcode: str) -> str:
    bban = bankcode.zfill(4) + prefix.zfill(6) + number.zfill(10)
    return f"CZ{iban_check_digits(bban, 'CZ')}{bban}"


def to_domestic(iban: str) -> str | None:
    """The inverse of `to_iban` for a `CZ` IBAN; `None` for any other
    country, since no other domestic form is known here."""
    if not iban.startswith("CZ") or len(iban) != 24:
        return None
    bban = iban[4:]
    bankcode, prefix, number = bban[:4], bban[4:10].lstrip("0"), bban[10:20].lstrip("0")
    number = number or "0"
    return f"{prefix}-{number}/{bankcode}" if prefix else f"{number}/{bankcode}"


def parse(raw: str) -> str:
    """Accepts either form, strips spaces, uppercases, validates, and
    returns the canonical IBAN. Raises `AccountError` naming which check
    failed."""
    value = raw.strip().replace(" ", "").upper()
    domestic = _DOMESTIC_SHAPE.match(value)
    if domestic:
        prefix, number, bankcode = domestic.group(1) or "0", domestic.group(2), domestic.group(3)
        if not valid_cz_part(prefix) or not valid_cz_part(number):
            raise AccountError("account_checksum")
        return to_iban(prefix, number, bankcode)
    if _IBAN_SHAPE.match(value):
        if not valid_iban(value):
            raise AccountError("iban_checksum")
        return value
    raise AccountError("format")


def display(iban: str) -> str:
    domestic = to_domestic(iban)
    return f"{domestic} ({iban})" if domestic else iban
