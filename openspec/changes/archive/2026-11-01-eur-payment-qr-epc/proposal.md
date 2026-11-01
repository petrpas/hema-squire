## Why

The first production confirmation carried a EUR QR code that a banking app refused. Every code Squire draws is a SPAYD string, and the EUR one differs only in `CC:EUR`. SPAYD is a Czech format. The EUR code exists for foreign fencers, and their banks (German, Austrian, Polish, Slovak…) read the **EPC QR code** — the European Payments Council's SEPA transfer code, the "GiroCode" — and mostly not SPAYD. As things stand the EUR code helps almost nobody it was made for.

## What Changes

- Every payment code denominated in EUR becomes an **EPC QR code** (version `002`, UTF-8, SEPA credit transfer). Codes in any other currency stay SPAYD. This covers the second code of a local + EUR tournament and the only code of a EUR-only one, in every mail and in the in-app payment instructions.
- The VS travels in the EPC code's remittance text, labelled (`VS2601004 <tournament>`), which payment matching already finds in a SEPA message.
- The tournament records the **account holder**: a plain-text name of at most 70 characters, entered on `PAYMENTS` directly below the bank account, with a help hint saying why it is needed. EPC requires a beneficiary name.
- The holder is **mandatory for publication** on a tournament with payments on that takes EUR. Where a holder is missing anyway (a tournament already published), the instructions still state the EUR amount, IBAN and VS in text and carry no EUR code rather than one that fails.
- The holder is **recalled** like the bank account, from the organizer's own earlier tournaments. Picking a recalled account also fills its holder when the holder field is empty.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payments`: a code's format follows its currency (EPC for EUR, SPAYD otherwise); foreign payers get an EPC code against the IBAN and holder.
- `registration`: the confirmation and the in-app payment data carry codes in their currency's format.
- `fencer-home`: the detail page's payment QR is in its currency's format.
- `tournament-admin`: the account holder field beside the bank account; completeness requires it where EUR is taken.
- `setup-field-suggestions`: the holder recalls prior values; a recalled account brings its holder.

## Impact

- `backend/app/spayd.py` gains an EPC builder beside `spayd_string` (or a sibling `epc.py`); `emails.payment_spayd` picks the format by currency, and the payment-data endpoints in `routers/registrations.py` follow it. The response fields named `spayd`/`eur_spayd` carry whichever string was drawn.
- `models.Tournament.bank_account_holder` (nullable `String(70)`) with an alembic migration; `TournamentUpdate`/`TournamentOut`; `setup.py` completeness; `SetupSuggestionsOut` gains the holders and the account→holder pairing.
- `frontend/src/setup/BankAccountSection.tsx` gains the field, its hint and the suggestion behaviour; `PUBLISH` names the missing item; `cs`/`en` locale keys.
- No new dependency: `qrcode` already renders any string.
