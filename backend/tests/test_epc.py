"""The EPC QR code a EUR payment is drawn as (change eur-payment-qr-epc D2)."""

from decimal import Decimal

from app import emails
from app.spayd import EPC_PAYLOAD_MAX_BYTES, epc_string

IBAN = "CZ6508000000192000145399"


def test_reference_payload_is_fixed():
    # a bank app parses this strictly: every line, and no trailing line break
    assert epc_string(IBAN, "TJ Šerm Praha", 60, "VS2601004 Na Duel!") == (
        "BCD\n002\n1\nSCT\n\nTJ Šerm Praha\nCZ6508000000192000145399\nEUR60\n\n\nVS2601004 Na Duel!"
    )


def test_amount_keeps_cents_with_a_dot():
    assert "\nEUR12.50\n" in epc_string(IBAN, "Holder", Decimal("12.5"), "VS1")


def test_line_breaks_inside_name_and_message_become_spaces():
    lines = epc_string(IBAN, "TJ Šerm\nPraha", 60, "VS2601004\r\nNa Duel!").split("\n")
    assert len(lines) == 11
    assert lines[5] == "TJ Šerm Praha"
    assert lines[10] == "VS2601004 Na Duel!"


def test_remittance_is_cut_to_140_and_keeps_the_labelled_vs():
    remittance = epc_string(IBAN, "Holder", 60, "VS2601004 " + "x" * 300).split("\n")[10]
    assert len(remittance) == 140
    assert remittance.startswith("VS2601004 ")


def test_payload_stays_within_331_bytes_at_maximum_lengths():
    # two-byte characters fill both fields to their character limits
    payload = epc_string(IBAN, "Š" * 100, Decimal("999999.99"), "VS2601004 " + "ž" * 300)
    assert len(payload.encode()) <= EPC_PAYLOAD_MAX_BYTES
    lines = payload.split("\n")
    assert len(lines[5]) == 70
    assert lines[10].startswith("VS2601004 ")


def test_eur_without_a_holder_draws_no_code():
    assert emails.payment_code("EUR", IBAN, None, 60, 2601004, "VS2601004 Cup") is None
    assert emails.payment_code("EUR", IBAN, "  ", 60, 2601004, "VS2601004 Cup") is None


def test_the_format_follows_the_currency():
    czk = emails.payment_code("CZK", IBAN, "Holder", 1500, 2601004, "VS2601004 Cup")
    eur = emails.payment_code("EUR", IBAN, "Holder", 60, 2601004, "VS2601004 Cup")
    assert czk is not None and czk.startswith("SPD*1.0*") and "CC:CZK" in czk
    assert eur is not None and eur.startswith("BCD\n002\n")
