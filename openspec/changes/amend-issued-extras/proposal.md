## Why

The fencer list shows what each row borrows, and the cell does not open. An
organizer who finds a rental named wrong — or one the roster missed — has
nowhere to correct it, and the correction is not cosmetic: on a tournament
priced by items each rental carries a price, so a wrong name is a wrong total.
Squire has just started pricing those rentals at issuing
(`imported-registrations`, What an issued registration is worth); until the cell
opens, the only remedy for a mistake in one is a hand-settled row.

The disciplines cell reached the same point a day earlier and was opened by
`edit-issued-disciplines`, which built the machinery this needs: an amendment
that replaces a registration's selection, re-prices it through the fencer's own
amendment call, records the event, writes to the fencer only where the
correction costs them, and can be withdrawn from the manual-edits log.

What that change built is named after disciplines alone. Rentals are the second
priced field the console must be able to correct, the afterparty is the third
and merchandise the fourth — every one of them moves the total. The kind is
generalized here rather than copied, so that the fourth of them is a column and
a validator rather than a fourth parallel code path.

## What Changes

- The **rentals cell opens** on the fencer list for every row, edited as free
  text: the item names, separated by commas, as the disciplines cell is edited.
- For a row with no registration the edit stays a `field_edit` — a correction to
  the row, carried into the registration when it is issued.
- For a row with one, the edit **amends the registration**: its rental
  selections are replaced by the items named, its other extras (afterparty,
  merchandise) are left exactly as they stand, its legacy rental list is written
  to match, and its total is recomputed by the same call the fencer's own
  amendment uses.
- **RENAMED**: the rule kind `discipline_amendment` becomes
  `registration_amendment`, carrying the field it amends. Existing rules are
  migrated. Its validation, its replay and its withdrawal become per-field, so
  a row may hold an amendment of its disciplines and one of its rentals at once
  and withdrawing either leaves what the other says.
- A name the tournament lends nothing by is **accepted and billed nothing**, as
  an imported row's unpriced rental already is — and now says so in the row's
  problems as well as in the cell, so it is visible where the organizer is
  looking rather than only where they are typing (owner decision, 2026-09-06).
- The **problems marker joins the fencer list**, which is where a correction is
  made and therefore where a problem with one has to be legible.
- Mail is unchanged in kind: the surcharge notice where the correction leaves
  the fencer owing more, silence otherwise.

## Capabilities

### Modified Capabilities
- `discipline-amendment`: generalized from the disciplines of a registration to
  any priced field of one — what an amendment replaces, what it re-prices, and
  what a second amendment of a different field does to the first.
- `edit-rules`: the rule kind's name, and its replay and withdrawal becoming
  per-field.
- `etl-console`: the rentals column's editability, and the problems marker on
  the fencer list.
- `imported-registrations`: an unpriced rental is stated in the row's problems,
  not only in the cell.

## Impact

**Backend**: `app/rules.py` (the renamed kind, per-field validation, replay and
withdrawal), `app/amendment.py` (an amendment that replaces extras of one
category and leaves the rest), `app/routers/rules_api.py`, `app/sheet.py` (the
problems text on a row whose rentals are unpriced), one Alembic migration for
the rule kind already stored.

**Frontend**: `Console.tsx` (`editableHere`, `ruleKindFor`, the rentals cell's
value and parsing, the problems marker in the fencer list's columns),
`RentalsCell.tsx`, `i18n/{cs,en}.json`.

**Not affected**: the fencer's own amendment — its window, its confirmation
mail, its refusal for a registration that is not live. Pricing gains no rules:
extras are already priced by `pricing.selection_total`, and the afterparty and
merchandise columns are not opened here because neither has a cell to open yet.
