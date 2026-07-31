## 1. Backend data model and migration

- [x] 1.1 Add a `Currency` StrEnum (`CZK`, `EUR`) to `models.py` and the three currency columns to `Tournament`: `primary_currency` (String(3), default `CZK`, not null), `eur_payments_enabled` (bool, default false, not null), `eur_rate` (Numeric, nullable)
- [x] 1.2 Add `registration_instructions` (Text, nullable) to `Tournament`
- [x] 1.3 Add `option_label` (String(50), nullable) and `option_choices` (JSON list, default empty) to `ExtraItem`
- [x] 1.4 Add `option_value` (String(100), nullable) to `RegistrationExtra`
- [x] 1.5 Write the Alembic revision adding all six columns with defaults that reproduce current behavior (CZK, EUR off, nulls/empties), plus a down-revision dropping them
- [x] 1.6 Add a test that a tournament created before the migration loads as CZK with EUR payments off and its stored totals are unchanged

## 2. Currency validation and conversion

- [x] 2.1 Extend `TournamentUpdate`/`TournamentOut`/`TournamentDetailOut` in `schemas.py` with the currency fields and `registration_instructions`
- [x] 2.2 Enforce the currency invariants on save: EUR primary forces `eur_payments_enabled` true and `eur_rate` null; EUR payments on a non-EUR tournament require `eur_rate > 0` (field-level 422); disabling EUR payments clears the rate
- [x] 2.3 Add `pricing.to_eur(amount, tournament)` and `pricing.from_eur_cents(cents, tournament)`, both quantizing half-up to two decimals, returning None when no rate applies
- [x] 2.4 Extend `setup.setup_missing` with the missing-exchange-rate condition and cover it with a test
- [x] 2.5 Tests for every currency invariant scenario in the `tournament-admin` delta (rate required, non-positive rejected, EUR primary stores no rate, disabling clears)

## 3. Extra-item options

- [x] 3.1 Extend the extra-item schemas with `option_label` and `option_choices`, rejecting choices without a label and trimming/deduplicating choices
- [x] 3.2 Extend the registration and price-preview input schemas so each extra selection accepts an optional `option_value`
- [x] 3.3 Validate option values at registration time: required when the item declares a label, must be one of the choices when choices exist, non-empty trimmed text within the length cap otherwise, rejected when the item declares no label
- [x] 3.4 Carry `option_value` through registration creation and the registration detail response
- [x] 3.5 Add a pricing test proving an answered option leaves the computed total identical
- [x] 3.6 Add a test that a selection stored before an option label existed stays valid and renders with no option value

## 4. SPAYD, payment instructions, and emails

- [x] 4.1 Add a `currency` parameter to `spayd.spayd_string` (feeding `CC:`) and format `AM:` from a `Decimal` so non-integer amounts render correctly; drop the CZK-only note from the module docstring
- [x] 4.2 Extend `emails.payment_qr` to return the primary QR plus a EUR QR when EUR payments are enabled on a non-EUR tournament, both against the configured IBAN
- [x] 4.3 Add `i18n.format_money(amount, currency)` and replace `{total} Kč` with `{total}` in the three email bodies in `locales/{cs,en}.json`; add the optional EUR amount block and the per-item option lines to the confirmation body
- [x] 4.4 Extend the payment-instructions response with `currency`, optional `eur_amount`, and optional `eur_qr_png_base64` — absent, not empty, when they do not apply
- [x] 4.5 Extend the price-preview response with `currency` and the optional EUR equivalent
- [x] 4.6 Tests: SPAYD string carries `CC:EUR` with a decimal amount; instructions carry the EUR pair only when applicable; the confirmation email lists option values

## 5. Payment matching

- [x] 5.1 In `matching.py`, convert a transaction whose currency differs from the tournament's primary currency into primary-currency cents before the tolerance comparison
- [x] 5.2 Flag a VS-matched transaction in a currency with no configured rate as `currency_unconvertible` instead of comparing the raw amounts, and audit it with that reason
- [x] 5.3 Tests: 68.63 EUR against a 1750 CZK total at rate 25.5 matches; an unconvertible currency is flagged with its own reason; the existing same-currency tolerance behavior is unchanged

## 6. Export

- [x] 6.1 Bump `export_json.SCHEMA_VERSION` to 3 and carry the currency fields plus `registration_instructions` in `_TOURNAMENT_FIELDS`
- [x] 6.2 Carry `option_label`/`option_choices` on exported extra items and `option_value` on exported selections
- [x] 6.3 Accept v1, v2, and v3 on restore, defaulting absent currency fields to CZK with EUR off and absent option fields to null/empty
- [x] 6.4 Round-trip test covering a v2 file restored into the new schema and a v3 file round-tripping unchanged

## 7. Setup panel

- [x] 7.1 Add the currency controls to Setup: primary-currency select, EUR-payments checkbox (hidden when primary is EUR), and the rate field shown only when EUR payments are on, with a help hint naming the direction ("primary units per 1 EUR")
- [x] 7.2 Show a non-blocking warning when the entered rate falls outside 0.5–1000
- [x] 7.3 Add a Setup hint stating that changing the rate moves the EUR figures shown on existing unpaid reservations
- [x] 7.4 Add the `registration_instructions` textarea beside `description`, using the existing textarea field pattern
- [x] 7.5 Add the option-label and option-choices columns to the extra-services table, with choices entered as a comma-separated list and a help hint
- [x] 7.6 Feed the tournament's currency into the price/fee field labels in `SetupPanel.tsx` and `ParamPanel.tsx`

## 8. Money rendering (frontend)

- [x] 8.1 Add `formatMoney(amount, currency)` and a `CURRENCY_SYMBOLS` map, plus `formatMoneyWithEur(amount, detail)` returning the bare primary amount whenever EUR payments are off or the primary currency is EUR
- [x] 8.2 Rewrite the six currency-baked i18n keys in `cs.json`/`en.json` to take an interpolated amount or `{{currency}}`, and update every call site
- [x] 8.3 Replace every hardcoded `Kč` in `TournamentDetail.tsx` (discipline info, form rows, total, payment panel) with the formatter
- [x] 8.4 Grep gate: no `Kč`, `CZK`, or `€` literal outside `CURRENCY_SYMBOLS` and the currency enum, in either frontend or backend

## 9. Registration form rewrite

- [x] 9.1 Add the checklist row CSS to `index.css`: a `[control | name | price]` grid with a right-aligned price column and a full-width indented detail block, hairlines from `tokens.css` only
- [x] 9.2 Build the row component (checkbox, name, price, optional quantity revealed on selection, optional detail lines) and use it for all three sections
- [x] 9.3 Render the sections from `ACTION_CATEGORIES` membership, omitting empty sections, and render legacy weapon-rental/afterparty controls as rows in the same grid
- [x] 9.4 Add the header block: display name, subtitle when set, registration instructions when set with line breaks preserved
- [x] 9.5 Render the option control per row — select when the item has choices, text input when it does not — and include the value in the price-preview and submit payloads
- [x] 9.6 Render the full-discipline sub-line ("full {taken}/{capacity} — you will be registered as a substitute") and submit `wait_for_all: true` when such a row is selected
- [x] 9.7 Delete the `fullDisciplines` state and its confirm dialog; keep the 409 branch as an inline error naming the affected disciplines
- [x] 9.8 Move after-sparring, accommodation, and remarks into a closing non-billable block below the total
- [x] 9.9 Show the running total with its EUR equivalent through `formatMoneyWithEur`
- [x] 9.10 Show option values in `RegistrationSummary` and `RegistrationPanel` beside their items

## 10. Verification

- [x] 10.1 Run the backend test suite and the frontend typecheck/build; fix fallout
- [x] 10.2 Walk the form against the prohibitions list: no radius > 2px, no shadow, no gradient, no emoji or filled icons, no hex outside `tokens.css`, no default blue focus ring
- [x] 10.3 Manually verify one CZK-only tournament and one CZK+EUR tournament end to end: form, total, payment instructions, both QR codes, confirmation email
- [x] 10.4 Verify a legacy tournament (no extra items) still renders, prices, and registers as before
