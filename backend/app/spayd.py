"""SPAYD (Short Payment Descriptor) strings and QR codes for bank payments.

The ACC field requires IBAN format; organizers must configure the tournament
bank account as IBAN. The currency travels in CC, so the same account can be
offered both in the tournament's primary currency and in EUR (design D4).
"""

import io
import re
from decimal import Decimal

import qrcode

_MSG_FORBIDDEN = re.compile(r"[*\n\r]")


def spayd_string(
    account_iban: str,
    amount: int | Decimal,
    vs: int,
    message: str,
    currency: str,
) -> str:
    """`currency` is required on purpose: a payment string that guesses its
    currency is how a EUR payer ends up sending the CZK amount."""
    msg = _MSG_FORBIDDEN.sub(" ", message).strip()[:60]
    # AM takes two decimals; formatting from Decimal keeps a converted EUR
    # amount like 68.63 intact instead of truncating it to whole units
    am = f"{Decimal(amount):.2f}"
    return (
        f"SPD*1.0*ACC:{account_iban.replace(' ', '')}"
        f"*AM:{am}*CC:{currency}*X-VS:{vs}*MSG:{msg}"
    )


def qr_png(data: str) -> bytes:
    image = qrcode.make(data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
