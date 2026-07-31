## Why

The registration screen grew by accretion: disciplines render as chips, extra
services as bare number inputs, and the legacy weapon-rental fields sit in a
section of their own — so a fencer cannot read what a tournament actually offers
or what it costs. What the tournament sells (disciplines, seminars, afterparties,
gear, merch) is already modelled richly enough to be presented as one priced
checklist, and it should be, because that checklist *is* the tiskopis the design
system is built around.

Separately, every price in the system is implicitly CZK — hardcoded in the SPAYD
QR (`CC:CZK`), in i18n labels, and in email bodies. Tournaments with foreign
participants need to state a EUR figure and take a EUR transfer, which is
impossible while the currency is a literal.

## What Changes

- **Registration form becomes a priced checklist.** One tree of sections, each
  row a checkbox (or a checkbox plus quantity when the item allows more than one),
  the price right-aligned on the row, and the item's `when`/`where`/`remark` as
  indented sub-lines. Sections: the tournament itself (disciplines), the optional
  programme (seminar / afterparty / other action), and optional items (rental /
  merch / other item). Non-billable fields (after-sparring, accommodation,
  remarks) move to a closing block.
- **Full disciplines are explained in place.** A discipline at capacity shows
  `full 25/20 — you will be registered as a substitute` under its row, and
  ticking it registers as a substitute. **BREAKING (UI):** the current 409
  "drop full / join queue" dialog is removed from the fencer flow; the API keeps
  the `wait_for_all` contract and the form always sends it as chosen on the row.
- **Extra items gain one option field.** An extra item may declare an option
  label (for example "size") with optional preset choices; the registration
  stores the fencer's answer per selected item, and it appears in the summary,
  the confirmation email, and the export. Options never affect pricing.
- **Registration instructions.** A new optional multiline field on the tournament,
  edited in Setup, shown only at the top of the registration form — the place for
  payment or registration notes that do not belong on the public information
  screen.
- **Tournament currency.** The tournament gains a primary currency (CZK or EUR).
  When the primary currency is not EUR, the organizer may enable EUR payments,
  which requires an exchange rate (`1 EUR = N primary units`). All money is
  presented in the primary currency; the EUR equivalent is shown alongside only
  when EUR payments are enabled.
- **EUR payment path.** With EUR payments enabled, payment instructions and the
  confirmation email carry a second amount and a second SPAYD QR with `CC:EUR`
  against the same IBAN. An ingested EUR transaction is converted at the
  tournament's stored rate before the existing amount tolerance is applied, so
  matching stays a single rule.
- **No hardcoded currency.** `CC:CZK`, the `Kč`/`CZK` suffixes in i18n keys, and
  the `{total} Kč` email lines are replaced by a formatted amount carrying its
  currency code.

## Capabilities

### New Capabilities

None. Every change extends an existing capability.

### Modified Capabilities

- `registration`: the registration form is specified as a categorized priced
  checklist; substitute registration becomes an in-row choice rather than a
  post-submit dialog; item options are captured, validated, and carried into the
  summary, email, and export; totals and payment instructions are presented in
  the tournament's currency with an optional EUR equivalent.
- `tournament-admin`: tournament definition gains `primary_currency`,
  `eur_payments_enabled`, `eur_rate`, and `registration_instructions`; extra-service
  rows gain an option label and optional choices; setup completeness requires an
  exchange rate whenever EUR payments are enabled.
- `payments`: amount tolerance is evaluated after converting a foreign-currency
  transaction at the tournament's stored rate; payment instructions and reminders
  may carry a second EUR amount and QR.
- `localization`: money is rendered from (amount, currency) rather than from
  currency-baked message strings, in both the frontend and the email templates.

### Unchanged

The pricing computation itself — item subtotals, ordered discounts, half-up
rounding — is untouched. Amounts stay integers in the primary currency; the EUR
figure is derived for presentation and matching, never stored on a registration.

## Impact

- **Backend models**: `Tournament` (currency, EUR flag, rate, registration
  instructions), `ExtraItem` (option label, option choices), new
  per-selection option value on `RegistrationExtra`. One Alembic revision.
- **Backend logic**: `spayd.py` (currency parameter, second QR), `matching.py`
  (convert before tolerance), `emails.py` + `locales/*.json` (formatted money,
  EUR block, option lines), `schemas.py` (new fields plus option validation),
  `setup.py` (completeness rule), `export_json.py` (schema version bump for the
  new fields).
- **Frontend**: `TournamentDetail.tsx` (form rewritten as the checklist,
  instructions block, EUR line, payment panel), `SetupPanel.tsx` (currency
  controls, instructions field, extra-item option columns), `ParamPanel.tsx`
  (currency-labelled fee fields), `index.css` (checklist row pattern),
  `i18n/{cs,en}.json` (currency-free labels, new keys).
- **APIs**: `POST /api/tournaments/{slug}/registrations` and the price-preview
  endpoint accept an option value per extra selection; tournament detail,
  fencer-facing list, and payment-instruction payloads carry currency fields.
  Existing clients omitting the new fields keep working.
