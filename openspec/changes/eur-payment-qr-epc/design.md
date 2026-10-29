## Context

`spayd.spayd_string(account_iban, amount, vs, message, currency)` builds every code. `emails.payment_spayd` calls it once for the local currency and once more with `currency="EUR"` when the registration has a EUR total. `payment_qrs` and the payment-data endpoints in `routers/registrations.py` render both through `spayd.qr_png`. `payment_message` is `VS{vs} {display_name}`. Matching (`matching.py`) already scans every text field of a transaction for `LABELLED_VS` (`\bVS[:\s]*(\d{1,10})\b`), and the "SEPA payment with VS in the message" scenario is green today. The tournament stores the IBAN only. Account suggestions are derived per request from the caller's tournaments (`_distinct_recent`).

## Goals / Non-Goals

**Goals:**
- A EUR code a foreign bank app reads.
- The holder recorded once and recalled like the account.

**Non-Goals:**
- Other foreign currencies. The enumeration holds `CZK` and `EUR` only; a future local currency picks its format when it is added.
- BIC. EPC version `002` makes it optional inside the EEA, and asking organizers for it would only produce typos.
- Changing the CZK code or how matching works.

## Decisions

**D1. Choose the format by currency, in one place.** A `payment_code(currency, iban, holder, amount, vs, message) -> str | None` returns SPAYD for non-EUR and EPC for EUR, and `None` for EUR without a holder. `payment_spayd` (renamed `payment_codes`) calls it for both currencies, so a EUR-only tournament's primary code is EPC with no special case. Alternative: always ship both a SPAYD and an EPC EUR code. Rejected: a fencer handed two codes for one payment has to guess, and the confirmation already carries up to four.

**D2. EPC payload.** Lines joined by `\n`: `BCD`, `002`, `1` (UTF-8), `SCT`, empty BIC, holder (≤70), IBAN, `EUR` + amount (`Decimal` normalized, dot, ≤2 decimals, no trailing `.00` needed), empty purpose, empty structured reference, remittance text (≤140), no information line. The whole payload must stay ≤331 bytes; a 70-character name plus 140 of text fits. Line breaks inside the name or message are replaced with spaces, as SPAYD's `*` already is. The unstructured remittance is used rather than an RF creditor reference, because the VS is what matching reads and an RF reference would need its own parser.

**D3. Holder is a tournament column, recalled like the account.** `Tournament.bank_account_holder: Mapped[str | None] = String(70)`. Suggestions gain `bank_account_holders` (distinct recent) and a `holder_by_account` map from each recalled IBAN to the holder stored with it on its most recent tournament. The frontend fills the holder from that map only when the field is empty. Alternative: a per-organizer table of accounts. Rejected: suggestions are derived from tournaments by design ("nothing is stored"), and a second store would drift from them.

**D4. Completeness, not a soft warning.** The holder joins the bank account's rule: required when payments are on, the tournament charges something and it takes EUR (EUR-only, or local + EUR). The existing "a published tournament's save becomes refused once it becomes incomplete" mechanics apply unchanged. Since D1 returns `None` without a holder, a tournament published before this change degrades to text-only EUR instructions instead of a failing code.

**D5. Response field names stay.** `spayd`/`eur_spayd` in the payment-data response keep their names and now carry whichever string was drawn. Renaming them would churn the frontend for a name only developers read. A comment at the schema says so.

## Risks / Trade-offs

- [A bank app parses EPC strictly and rejects an edge case] → a unit test fixes the exact payload for a reference case, and the drill is repeated with a real foreign app (a German or Austrian banking app, or a GiroCode test reader) before archiving.
- [Czech fencers paying EUR from a Czech app may still be unable to scan] → acceptable: they pay CZK, and the EUR text details remain stated.
- [An organizer types the club name where the bank knows a person] → the hint says "as the bank knows it". Banks match SEPA beneficiary names loosely, so a mismatch rarely blocks a transfer.

## Migration Plan

Alembic migration adding the nullable column. No backfill: production has one test tournament. Deploy with the next ordinary deploy; the owner fills the holder on any EUR tournament, which `PUBLISH` will name.
