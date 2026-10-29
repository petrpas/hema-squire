"""Payment strings and QR codes for bank payments.

A code in EUR is an EPC QR code (the SEPA "GiroCode"), which the foreign banks
EUR is offered for read; a code in any other currency is SPAYD, the Czech
format (design eur-payment-qr-epc D1). Both encode the tournament's IBAN.
"""

import io
import re
from decimal import Decimal

import qrcode
from qrcode.image.pil import PilImage

_MSG_FORBIDDEN = re.compile(r"[*\n\r]")
_LINE_BREAKS = re.compile(r"[\n\r]+")

# the EPC QR code's own limits (EPC069-12, version 002)
EPC_NAME_MAX = 70
EPC_REMITTANCE_MAX = 140
EPC_PAYLOAD_MAX_BYTES = 331


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
    # AM takes two decimals even though every stored price is a whole unit
    am = f"{Decimal(amount):.2f}"
    return f"SPD*1.0*ACC:{account_iban.replace(' ', '')}*AM:{am}*CC:{currency}*X-VS:{vs}*MSG:{msg}"


def epc_string(
    account_iban: str,
    holder: str,
    amount: int | Decimal,
    message: str,
) -> str:
    """An EPC QR code payload for a SEPA credit transfer in EUR (design D2):
    version 002, UTF-8, no BIC, no purpose, no structured reference, the
    payment message as unstructured remittance text. The message leads with
    the labelled VS, so a cut from its end keeps what matching reads."""
    name = _LINE_BREAKS.sub(" ", holder).strip()[:EPC_NAME_MAX]
    remittance = _LINE_BREAKS.sub(" ", message).strip()[:EPC_REMITTANCE_MAX]
    cents = Decimal(amount).quantize(Decimal("0.01"))
    # the format admits no zero amount; an empty field leaves it to the payer
    if cents <= 0:
        am = ""
    elif cents == cents.to_integral_value():
        am = f"EUR{int(cents)}"
    else:
        am = f"EUR{cents}"

    def payload(text: str) -> str:
        return "\n".join(
            ["BCD", "002", "1", "SCT", "", name, account_iban.replace(" ", ""), am, "", "", text]
        )

    # the 331-byte ceiling counts bytes, and a name or message in diacritics
    # can pass it within the character limits; the remittance gives way
    while len(payload(remittance).encode()) > EPC_PAYLOAD_MAX_BYTES:
        remittance = remittance[:-1]
    return payload(remittance)


def qr_png(data: str) -> bytes:
    image = qrcode.make(data, image_factory=PilImage)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
