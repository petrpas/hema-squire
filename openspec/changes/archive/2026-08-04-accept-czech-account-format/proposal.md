## Why

Setup accepts a bank account in IBAN form only. `constraints.py:37` enforces
`^[A-Z]{2}[0-9]{2}[A-Za-z0-9]{10,30}$`, mirrored into `frontend/src/constraints.ts`
and held identical by `test_constraints_mirror.py`. A Czech organizer who types the
account they actually use — `19-2000145399/0800` — is rejected by a field that was
just made mandatory for publication by `fix-payment-instructions-visibility`.

Czech organizers do not know their IBAN. It appears nowhere on a bank card, rarely
on a statement, and never in the domestic transfer form they use every day. The
two forms are deterministically interconvertible: a CZ IBAN's BBAN is exactly the
four-digit bank code, the six-digit prefix and the ten-digit account number that
make up the domestic format, so nothing is lost in either direction.

The same field is also validated only for **shape**. `CZ00XXXXXXXXXX` passes today
— there is no mod-97 check — so a mistyped IBAN is stored, printed into four
emails, and encoded into a QR code that fails at the payer's bank. That is the
failure mode this area keeps producing: money that cannot be paid, discovered by
the fencer rather than the organizer.

## What Changes

- **Both formats accepted on input.** The Setup field takes a Czech domestic
  account (`[prefix-]number/bankcode`) or an IBAN. The shared pattern widens to
  admit both shapes, keeping instant feedback in Setup and staying a literal the
  mirror test can compare.
- **A Czech account is converted to its IBAN on save.** The column keeps holding a
  canonical IBAN, so `spayd.py` — which documents `ACC:` as IBAN-only — and every
  existing stored value are untouched. No new column, no migration.
- **Checksums are validated on save**: IBAN mod-97 check digits, and the ČNB
  mod-11 weighted checksum on a Czech account's prefix and number, each of which
  every real account satisfies. A failing account is refused with a field error
  naming what is wrong, rather than being stored and mailed out.
- **The fencer is shown the domestic form when the account is Czech.** It is
  derived from the stored IBAN, never stored twice. The four email bodies pass
  their account through a single `{account}` placeholder in both locales, so this
  changes what `emails.py` formats and no template at all. The payment slip gains
  the domestic line beside the IBAN.
- **New `backend/app/accounts.py`** owning parse, convert, validate and format for
  both directions — one module, so no consumer of `bank_account` learns two
  formats.

Not in scope: non-Czech domestic formats (a Slovak or German account is entered as
its IBAN, as today); any change to matching, SPAYD encoding, or which currencies a
tournament prices in; the deposit model.

## Capabilities

### Modified Capabilities
- `tournament-admin`: the bank account field accepts either format, is stored
  canonically, and is validated rather than merely shape-checked.
- `registration`: payment instructions and the payment emails present a Czech
  account in the form a Czech payer can use.
- `field-validation`: the bank-account bound admits both shapes, and checksum
  validation is defined as a backend-only rule that the shared-constraint mirror
  deliberately does not carry.

## Impact

**Backend** (`backend/app/`): new `accounts.py`; `constraints.py`
(`BANK_ACCOUNT_PATTERN` widened); `schemas.py` (a validator on `TournamentUpdate.
bank_account` normalizing to IBAN and rejecting a bad checksum); `emails.py`
(format the account for display); `routers/registrations.py`
(`PaymentInstructionsOut` gains the domestic form); `tests/` for conversion,
checksums, and the mirror.

**Frontend** (`frontend/src/`): `constraints.ts` (the mirrored pattern);
`setup/BankAccountSection.tsx` (hint that either form is accepted, and surface the
server's checksum error); `TournamentDetail.tsx` (the domestic line on the payment
slip); `api.ts`; `i18n/{en,cs}.json` — `payment.iban` currently reads "Account
(IBAN)" and must stop claiming the form.

**Design constraints**: `CLAUDE.md` / `openspec/squire-design-spec.md` are binding
— the added slip line is static text in existing classes, no new colour or icon.

**Verification**: `pytest` covers conversion in both directions against known
account/IBAN pairs, checksum rejection, and `test_constraints_mirror.py`. The
frontend has no test runner, so its part is typecheck, build, and entering both
formats in Setup.
