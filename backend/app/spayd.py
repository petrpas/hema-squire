"""SPAYD (Short Payment Descriptor) strings and QR codes for Czech bank payments.

The ACC field requires IBAN format; organizers must configure the tournament
bank account as IBAN. Currency is CZK until multi-currency enters scope.
"""

import io
import re

import qrcode

_MSG_FORBIDDEN = re.compile(r"[*\n\r]")


def spayd_string(account_iban: str, amount: int, vs: int, message: str) -> str:
    msg = _MSG_FORBIDDEN.sub(" ", message).strip()[:60]
    return (
        f"SPD*1.0*ACC:{account_iban.replace(' ', '')}"
        f"*AM:{amount}.00*CC:CZK*X-VS:{vs}*MSG:{msg}"
    )


def qr_png(data: str) -> bytes:
    image = qrcode.make(data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
