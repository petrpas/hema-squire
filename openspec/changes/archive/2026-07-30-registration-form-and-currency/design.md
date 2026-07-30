## Context

The registration form lives in `RegistrationForm` inside
`frontend/src/TournamentDetail.tsx` (lines 195–440). It renders disciplines as
`.checkbox-chip` chips in a `.chips` flex row, and every extra item — regardless
of its category — as a bare `<input type="number">` inside `.param-field`. The
five legacy weapon codes are a hardcoded `LEGACY_WEAPONS` map. The data needed to
do better is already there: `ExtraItem` carries `category`, `price`, `max_qty`,
`schedule_when`, `schedule_where`, `remark`, and `ACTION_CATEGORIES`
(`backend/app/models.py:78`) already splits time-and-place kinds from goods kinds.
`Availability` already carries `taken`, `free`, `queue_length` per discipline.

Money is a literal today, in five places: `spayd.spayd_string` hardcodes
`CC:CZK` (`backend/app/spayd.py:20`); `matching.py:101-103` compares
`transaction.amount_cents` to `total_amount * 100` with no currency check even
though `BankTransaction.currency` exists (`models.py:366`); the six i18n keys with
`(Kč)` / `CZK` baked into the label text; `form.total` = `"Celkem: {{total}} Kč"`;
and the three email bodies in `backend/app/locales/{cs,en}.json` with
`{total} Kč` inline. Amounts are integers throughout — `Registration.total_amount`,
`ExtraItem.price`, `Discipline.fee` — and `pricing.py` rounds half-up to a whole
unit exactly once at the end.

Owner decisions taken before drafting (2026-07-29):

1. EUR is a real payment path, not only a displayed equivalent — second amount,
   second QR with `CC:EUR`, and conversion before tolerance on ingestion.
2. Extra items get one optional option field (label + optional preset choices),
   answered per selected item on the registration.
3. Registration instructions are a **new** field, distinct from the public
   `description` added in `small-layout-tweaks`.
4. A full discipline is a checkbox with an inline substitute sub-line; the 409
   confirm dialog leaves the fencer flow.

## Goals / Non-Goals

**Goals:**

- One reading order on the registration form: section heading, then rows of
  `[ ] name … price`, then indented detail lines. A fencer sees what is offered
  and what it costs without expanding anything.
- Capacity, substitute status, and item options are stated on the row they belong
  to.
- Currency is data. A tournament states its currency; every amount is rendered
  from (amount, currency) by one formatter per side (frontend, email).
- A EUR payer gets an amount and a QR they can actually use, and their transfer
  matches automatically.

**Non-Goals:**

- A general variant/SKU system. One option field per item, one answer per
  selection.
- Live exchange rates or any external FX service. The rate is a tournament
  setting the organizer types in.
- Multi-currency *pricing*. Item prices, discounts, and `total_amount` stay
  integers in the primary currency; EUR is derived.
- Per-currency bank accounts. The EUR QR uses the same configured IBAN.
- Changing the pricing algorithm, discount model, or reservation lifecycle.

## Decisions

### D1 — Currency as three tournament fields, not a currency table

`Tournament` gains `primary_currency` (`String(3)`, default `"CZK"`, not null),
`eur_payments_enabled` (bool, default false, not null), and `eur_rate`
(`Numeric`/`Decimal`, nullable) meaning *primary units per 1 EUR*. The currency
choice is a fixed enum of `CZK` and `EUR` — the two currencies HEMA events in
this region actually price in — declared as a `StrEnum` so widening it later is a
code change, not a schema change.

Invariants, enforced in `schemas.py` at save time:

- `primary_currency == "EUR"` ⇒ `eur_payments_enabled` is forced true and
  `eur_rate` is forced null. There is no second amount to show; the EUR block is
  simply the primary one.
- `eur_payments_enabled` with `primary_currency != "EUR"` ⇒ `eur_rate` is
  required and must be > 0.
- Disabling EUR payments clears `eur_rate`, mirroring how
  `qualification_open` clears `qualification_criteria`.

*Alternative rejected:* storing amounts in minor units with a currency per
amount. That is the right model for a system that prices in several currencies at
once; here it would rewrite `pricing.py`, every fee field, and every stored total
to buy nothing the organizer asked for.

### D2 — One money formatter per side, no currency in message strings

The currency-baked strings go away. Frontend gets a `formatMoney(amount,
currency)` helper and the i18n keys take the formatted string as a parameter
(`"total": "Celkem: {{amount}}"`), with the unit symbol chosen from a small
`CURRENCY_SYMBOLS` map (`CZK → Kč`, `EUR → €`) so Czech keeps its trailing `Kč`.
Field labels lose their suffix and gain a `{{currency}}` placeholder
(`"fee": "Cena ({{currency}})"`), fed from the tournament detail. The backend gets
`i18n.format_money(amount, currency)` used by the email templates, whose bodies
change from `{total} Kč` to `{total}`.

The EUR equivalent is rendered as `1 750 Kč (68,63 €)` by a
`formatMoneyWithEur(amount, detail)` wrapper that returns the bare primary amount
whenever `eur_payments_enabled` is false or the primary currency is already EUR.
This is the single decision point for "is there a EUR figure here", so no call
site repeats the condition.

### D3 — EUR conversion: one function, half-up to cents, derived never stored

`pricing.to_eur(amount, tournament) -> Decimal` divides by `eur_rate` and
quantizes half-up to two decimals; `pricing.from_eur_cents(cents, tournament) ->
Decimal` is its inverse used by matching. Registrations store only
`total_amount` in the primary currency — the EUR figure is recomputed from the
tournament's current rate every time it is shown.

That means a rate change moves the EUR figure on an existing unpaid reservation.
Accepted deliberately: the amount owed is the primary-currency total, the EUR
figure is a courtesy conversion, and the ±5 % amount tolerance already absorbs
the drift a mid-registration rate correction would cause. The alternative —
freezing a rate per reservation — adds a column and a migration to defend against
an organizer editing a number they rarely touch.

### D4 — SPAYD gains a currency parameter; a second QR, not a second account

`spayd_string(account_iban, amount, vs, message, currency="CZK")` puts the
currency in `CC:`, and `AM:` is formatted from a `Decimal` so `68.63` renders
correctly (today's `f"{amount}.00"` assumes an integer). `emails.payment_qr` and
the payment-instructions endpoint return two QRs when EUR payments are enabled
against a non-EUR primary currency: the primary one and a EUR one with the
converted amount, both against the tournament's single configured IBAN. Czech
IBANs accept SEPA EUR credits, so a second account field would be a setting most
organizers would leave empty.

The payment-instructions payload becomes
`{amount, currency, iban, vs, message, expires_at, qr_png_base64,
eur_amount?, eur_qr_png_base64?}` — the EUR pair absent when not applicable, so
existing clients are unaffected.

### D5 — Matching converts, then applies the existing tolerance

`matching.py` currently compares cents to cents with no currency check. It gains
one step before the comparison: if `transaction.currency` differs from the
tournament's primary currency, convert `amount_cents` into primary-currency cents
(EUR via `eur_rate`; any other currency is not converted). A transaction in a
currency that cannot be converted is flagged `currency_unconvertible` rather than
compared as if the numbers were commensurable — which is the latent bug today, a
68 EUR payment against a 1 750 CZK total currently reads as 96 % short and gets
flagged for the wrong reason.

The tolerance percentage then does what it was designed for: absorbing the
spread between the organizer's typed rate and the payer's bank's rate.

### D6 — Extra-item options: label + choices on the item, value on the selection

`ExtraItem` gains `option_label` (`String(50)`, nullable) and `option_choices`
(JSON list of strings, default empty). `RegistrationExtra` gains `option_value`
(`String(100)`, nullable). Semantics:

- No `option_label` ⇒ the item takes no option; a submitted `option_value` is
  rejected (422).
- `option_label` with a non-empty `option_choices` ⇒ the value must be one of the
  choices; the form renders a select.
- `option_label` with empty `option_choices` ⇒ free text, trimmed, length-capped;
  the form renders a text input.
- An option is **required** when the item is selected and declares a label.
  A half-filled t-shirt row is a support ticket, not a valid registration.

Options are inert for pricing — `pricing.py` is not touched — and a test asserts
that adding an option value leaves the computed total identical, mirroring the
existing "descriptive fields do not change totals" scenario.

*Alternative rejected:* a JSON `options` dict per selection. Flexible, but it
turns validation into schema-in-JSON and gives the Setup UI nothing concrete to
render.

### D7 — The checklist is a CSS grid row, reused by all three sections

One row component, three call sites. Each row is a grid of
`[control | name | price]` with the price right-aligned on a shared column, and
an optional indented block below spanning the full width for `when`/`where`,
`remark`, the capacity/substitute line, and the quantity/option controls. Rows
whose `max_qty` is 1 render a checkbox alone; rows allowing more render a checkbox
that reveals a quantity field defaulting to 1. Prohibitions apply: no radius, no
shadow, single hairline rules from `tokens.css`, no emoji, no filled icons.

Sections and their membership follow `ACTION_CATEGORIES`, so the split is data,
not another frontend list:

| Section | Contents |
|---|---|
| Tournament | disciplines |
| Optional programme | `seminar`, `afterparty`, `other_action` |
| Optional items | `rental`, `merch`, `other_item` |

Empty sections are omitted entirely. Legacy tournaments (no `extra_items`) keep
their fixed weapon-rental and afterparty controls, rendered as rows in the same
grid so the layout has one idiom — the `LEGACY_WEAPONS` map stays until legacy
tournaments are archived.

### D8 — Substitute choice moves onto the row

`Availability.free <= 0` on a discipline renders the sub-line "full {taken}/{capacity}
— you will be registered as a substitute" and, when ticked, contributes to a
submission with `wait_for_all: true`. The API contract does not change; the form
simply never submits a selection that would produce the 409, so the
`fullDisciplines` state and its dialog are deleted from the component. The 409
branch stays in `api.ts` error handling as a defensive fallback — a discipline can
fill between page load and submit — and surfaces as an inline error asking the
fencer to re-check the row rather than as a modal.

### D9 — `registration_instructions` is a separate field on Tournament

`Text`, nullable, edited in Setup next to `description`, presented only on the
registration form, line breaks preserved, no markdown — the same treatment
`description` received. It is not part of mandatory setup.

### D10 — Migration and export

One Alembic revision adds all six columns (three currency fields plus
`registration_instructions` on `tournaments`, `option_label`/`option_choices` on
`extra_items`, `option_value` on `registration_extras`). Existing rows get
`primary_currency = 'CZK'`, `eur_payments_enabled = false`, everything else null
or empty — which is exactly today's behavior, so no tournament changes how it
prices or bills.

`export_json.SCHEMA_VERSION` goes to 3, carrying the new tournament fields, the
item option definition, and the per-selection option value. Restore accepts v1,
v2, and v3: absent currency fields default to CZK with EUR off, absent option
fields to null/empty.

## Risks / Trade-offs

- **Wrong exchange rate typed by an organizer** (e.g. `0.04` instead of `25.5`)
  → the EUR figure is nonsense and EUR payments land far outside tolerance.
  Mitigation: validate `eur_rate > 0`, and add a plausibility warning (not a
  block) in Setup when the rate falls outside 0.5–1000, plus a help hint stating
  the direction explicitly ("primary units per 1 EUR").
- **Rate edited after reservations exist** → the EUR figure shown to an unpaid
  fencer changes (D3). Mitigation: the primary-currency total is authoritative
  everywhere, and the tolerance absorbs modest drift. A Setup hint says the rate
  affects EUR figures on existing unpaid reservations.
- **Required options break in-flight registrations** → nothing breaks for
  existing rows (no item declares an option until an organizer adds one), but an
  organizer adding an option label to an item that already has selections leaves
  those selections with a null value. Mitigation: the requirement applies at
  submit time only; existing selections render as "—" and are never retroactively
  invalid.
- **Rewriting the form loses a behavior** (after-sparring, accommodation, the
  price-preview debounce, the substitute path) → mitigation: the form's behaviors
  are pinned by scenarios in the `registration` delta spec before the rewrite, and
  the non-billable fields are moved, not dropped.
- **Currency de-hardcoding is a wide, shallow diff** touching six i18n keys, three
  email bodies, and every amount render site → mitigation: a grep gate in the task
  list (no `Kč`, `CZK`, or `€` literal outside the symbol map and the currency
  enum) so the sweep is verifiable rather than believed.

## Migration Plan

1. Ship the Alembic revision with the currency and option columns; defaults
   reproduce current behavior exactly.
2. Ship backend validation, SPAYD currency, conversion helpers, and matching
   conversion — all inert while every tournament is CZK with EUR off.
3. Ship the Setup controls (currency, rate, instructions, item options).
4. Ship the rewritten registration form and the de-hardcoded money rendering
   together, since the form is the largest consumer of the formatter.

Rollback: the revision's down-migration drops the six columns; the form rewrite is
a frontend-only revert. No data written by this change is load-bearing for
existing registrations — their totals are unchanged integers.

## Open Questions

None blocking. Deferred by choice: per-currency bank accounts, frozen per-reservation
rates, currencies beyond CZK/EUR, and more than one option per item — all additive
if an organizer asks.
