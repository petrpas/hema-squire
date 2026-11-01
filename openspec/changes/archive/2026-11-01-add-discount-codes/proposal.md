## Why

Today every discount a tournament offers is automatic and public: it is listed on
the detail page and on the registration form, and it applies to whoever meets its
condition. An organizer who wants to give one club, a helper or a trainer a better
price has to settle it by hand after the fact. A code the organizer hands out —
which the fencer types in, pays less, and nobody else sees — closes that gap
without touching the public price list.

## What Changes

- An organizer defines **discount codes** in Setup's `PAYMENTS` tab, directly below
  the discount list: name, code (prefilled as a slug of the name, editable), an
  optional limit on uses, and an effect — a fixed amount off the whole total, or a
  percentage of the whole total or of selected categories.
- The registration form offers a code field while the tournament has a usable code.
  A code that does not exist, belongs elsewhere or has run out gets one and the same
  answer, so an exhausted code reads as if it never existed. The form's total shows
  the discount before the fencer submits.
- A registration carries at most one code. It stacks with the automatic discounts
  and takes its place in the existing order: fixed before percentage.
- A fencer who forgot the code may add it in their amendment while the amendment
  window is open. A code cannot be removed or swapped.
- Uses are counted from live registrations, so a cancellation or an expiry gives the
  use back. A late payment reviving an expired registration keeps its discount even
  where that overruns the limit by one.
- **BREAKING (spec)** A registration brought to zero by a code reads as settled with
  no credit and no waiver: no payment window, no reminder, no expiry, and it shows as
  paid. Without this a 100 % code would cost a fencer their seat. `payment-ledger`'s
  rule that only a waiver or a credit can settle gains this third, narrow case.
- Once a code has been used its effect, scope and code text are locked; the name and
  the limit stay editable, and lowering the limit to the current uses retires it. A
  code no registration has ever carried can be deleted.
- The Payments phase gains a third table beside the fencer table and the payments:
  who holds which code and what it took off. The tab exists only while the tournament
  has codes.
- Revenue states each code as its own discount line. Codes and the registrations
  holding them survive the JSON export (schema v20).
- The deposit asked of a fencer is capped at what they actually owe, since a code can
  push a total below the flat deposit.

## Capabilities

### New Capabilities
- `discount-codes`: defining codes, redeeming them, how they price, how uses are
  counted, what a registration brought to zero means, and who can see what.

### Modified Capabilities
- `payment-ledger`: settled gains the case of a total a code brought to zero.
- `payments`: the deposit asked is capped at the total; a payments-off Payments phase
  may also hold the codes table.
- `payments-console`: the phase holds a codes table as well as the two it has.
- `registration`: registering and amending accept a code; the preview prices one.
- `fencer-home`: the code field on the form and the amendment, and the line it leaves
  on the registration.
- `setup-navigation`: the codes section's place on `PAYMENTS` / `PRICING`.
- `export-revenue`: a code is a discount line of its own.
- `data-export`: codes and their holders round-trip through the document.

## Impact

- **Backend**: new `DiscountCode` model and table, two columns on `Registration`,
  Alembic revision; new `app/discount_codes.py`; `pricing.py` (both pricing worlds),
  `models.py` (`settled`), `amendment.py`, `routers/registrations.py`, a new organizer
  router, `exportrevenue.py`, `export_json.py` (v20), `emails.py` (deposit cap, the
  nothing-to-pay mail), `setup.py` (missing EUR amounts), `tournament_delete.py`.
- **Frontend**: new `setup/DiscountCodesSection.tsx`, a code field shared by the
  register and amendment forms, a third table in `payments/`, `api.ts`, both i18n
  files, `constraints.ts`.
- **API**: new organizer CRUD and redemptions endpoints; a rate-limited priced
  preview carrying a code; `RegisterIn` and the amendment body accept a code.
- **Migrations**: additive; no existing registration or total changes.
