## 1. Backend: the accounts module

- [x] 1.1 Create `backend/app/accounts.py` with no dependency on models or schemas: it converts and validates strings only
- [x] 1.2 `iban_check_digits(bban, country)` — ISO 7064 mod-97-10: append `{country}00`, map `A`–`Z` to 10–35, compute `98 - (n % 97)`, return zero-padded two digits
- [x] 1.3 `valid_iban(value)` — shape, then move the first four characters to the end, map letters, require `n % 97 == 1`
- [x] 1.4 `valid_cz_part(digits)` — ČNB weighted modulo-11 with weights `1,2,4,8,5,10,9,7,3,6` applied from the rightmost digit; the weighted sum must be divisible by 11. Applied separately to prefix and account number; an omitted prefix is treated as `0` and passes
- [x] 1.5 `to_iban(prefix, number, bankcode)` — BBAN is `bankcode(4) + prefix.zfill(6) + number.zfill(10)`, then `CZ` + check digits + BBAN, giving 24 characters
- [x] 1.6 `to_domestic(iban)` — the inverse for a `CZ` IBAN, stripping leading zeros from prefix and number and omitting the prefix entirely when it is zero; returns `None` for any other country
- [x] 1.7 `parse(raw)` — accepts either form, strips spaces, uppercases, validates, and returns the canonical IBAN; raises a typed error naming which check failed (`iban_checksum`, `account_checksum`, `format`) so the caller can build a field message
- [x] 1.8 `display(iban)` — `"{domestic} ({iban})"` for a Czech account, the IBAN alone otherwise
- [x] 1.9 Unit tests over known pairs in both directions, including a zero prefix, a short account number needing padding, an account whose prefix is present, and a round trip `domestic → IBAN → domestic` returning the original

## 2. Backend: validation and storage

- [x] 2.1 Widen `BANK_ACCOUNT_PATTERN` in `backend/app/constraints.py` to `^([A-Z]{2}[0-9]{2}[A-Za-z0-9]{10,30}|[0-9]{1,6}-?[0-9]{2,10}/[0-9]{4})$` (design Decision 5); leave `TOURNAMENT_BANK_ACCOUNT_MAX_LENGTH` at 50
- [x] 2.2 Add a field validator on `TournamentUpdate.bank_account` in `schemas.py` calling `accounts.parse`, returning the canonical IBAN so the normalized value is what reaches the model. Keep the existing `SingleLineStr` bound and pattern — the validator runs after them
- [x] 2.3 Map the typed error to a 422 field error in the shape the frontend already places under a field, matching how the "rejection the client could not predict" path works for a taken slug
- [x] 2.4 Confirm nothing else writes `bank_account` — the validator is the only normalization point, so no consumer sees a domestic string
- [x] 2.5 Tests: a domestic account is stored as its IBAN; a valid IBAN is stored unchanged; a bad IBAN checksum is refused naming `iban_checksum`; a bad account checksum is refused naming `account_checksum`; both forms of one account normalize identically; an account stored before this change is readable and is not re-validated on load

## 3. Backend: presentation

- [x] 3.1 In `emails.py`, replace the four `account=tournament.bank_account or "?"` display call sites (lines 114, 192, 320, 356) with `accounts.display(...)`, preserving the `or "?"` fallback for an unset account
- [x] 3.2 Confirm no locale template changes are needed — all four bodies interpolate a single `{account}` in both `cs.json` and `en.json` (design Decision 2)
- [x] 3.3 Leave `emails.payment_spayd` and `payment_qrs` untouched: they pass `tournament.bank_account`, which is still the IBAN SPAYD requires
- [x] 3.4 Add `account_domestic: str | None` to `PaymentInstructionsOut` in `schemas.py`, populated from `accounts.to_domestic` in `routers/registrations.py::my_registration_payment`; leave the existing `iban` field as it is
- [x] 3.5 Tests: a Czech tournament's confirmation email states both forms; a foreign-IBAN tournament's states the IBAN alone; the QR encodes the IBAN in both cases; the payment endpoint returns `account_domestic` for a Czech account and `null` otherwise

## 4. Frontend

- [x] 4.1 Update the `"TournamentUpdate.bank_account"` pattern in `frontend/src/constraints.ts` to the identical literal from 2.1 — do not hand-tune one side; `backend/tests/test_constraints_mirror.py` compares them as text
- [x] 4.2 In `setup/BankAccountSection.tsx`, add a hint naming both accepted forms with an example of each, and surface the server's field error on save alongside the existing client-side pattern check
- [x] 4.3 Add `account_domestic: string | null` to `PaymentInstructions` in `api.ts`
- [x] 4.4 In `TournamentDetail.tsx`, render the domestic form as its own row above the IBAN when present, using the existing `.data-value` treatment — no new class, colour or icon (`CLAUDE.md`)
- [x] 4.5 Rename the `payment.iban` string from "Account (IBAN)" to a neutral account label and add a separate IBAN label, in `i18n/{en,cs}.json`; add the Setup hint and the two checksum error messages in both locales

## 5. Verification

- [x] 5.1 `pytest` in `backend/`, including `test_constraints_mirror.py`
- [x] 5.2 `npm run lint` (`tsc -b --noEmit`) and `npm run build` in `frontend/`
- [x] 5.3 In Setup, enter `19-2000145399/0800`, save, and confirm the stored value round-trips to that same domestic form on reload
- [x] 5.4 Enter an IBAN with one digit altered and confirm the save is refused with a message naming the checksum, under the field. **Note**: verified live — the refusal names the checksum correctly, but only in the tab-level save-bar summary, not as the field's own inline `<FieldError>`. Root cause: every Setup section's `useEffect(..., [detail])` unconditionally clears local validation state whenever any save attempt (success or failure) triggers `Console.tsx`'s `refresh()`, which always produces a new `detail` object. This is pre-existing and system-wide (`OrganizersSection`, `IdentitySection`, etc. share the identical pattern) — not a regression from this change. Owner decision (2026-08-04): leave as-is; the save-bar message already names the failed check actionably.
- [x] 5.5 Register as a fencer on a Czech-account tournament and confirm the payment slip shows both forms, the confirmation email states both, and the QR still scans to the correct account

## 6. Sequencing note

- [x] 6.1 Archive `fix-payment-instructions-visibility` **before** syncing this change's specs. Both modify `registration / In-app payment instructions retrieval`, and this change's delta is written against that change's version — syncing in the other order would drop its failure-case requirements. **Status**: `fix-payment-instructions-visibility` is implementation-complete (27/27) but not yet archived — flagged to the user; archiving/syncing is a separate action from `apply` and was not performed here.
