## Why

A fencer registering for a tournament that lends gear sees a section headed
"Volitelné položky" holding three rows — `Sabre 50 Kč`, `Sword 50 Kč`,
`Buckler 50 Kč` — and nothing on the screen says these are weapons to borrow
rather than weapons to buy, entry fees for something, or a second way to enter
the same disciplines listed above. The heading names the rows' billing status
(optional) instead of naming what they are, and the rows themselves are just
object names, so the section carries no information the fencer can act on. The
organizer already classified every one of these rows — `rental`, `merch`,
`other_item` — and the form throws that classification away by pooling all three
into one bucket.

## What Changes

- The register form's single "Volitelné položky" section is replaced by one
  section per **item category** actually offered: `rental`, `merch`,
  `other_item`, each under its own fencer-facing heading, in that fixed order.
  A tournament that only lends gear therefore gets exactly one section, headed
  "Zapůjčení vybavení" — no more sections than today, and the rows explain
  themselves.
- The item categories gain fencer-facing headings, worded for someone reading
  the form rather than for the organizer filling the setup table:
  "Zapůjčení vybavení" / "Equipment rental", "Merch" / "Merch", "Ostatní zboží"
  / "Other goods". The organizer-facing category names in Setup are unchanged.
- A category with no rows is omitted, as an empty section already is. Rows keep
  their existing order within a category.
- The **optional programme** (`seminar`, `afterparty`, `other_action`) stays one
  section under its present heading. "Volitelný program" already tells a fencer
  what the rows are — a section headed "Afterparty" over a single row reading
  "Afterparty" would say the same thing twice.
- Nothing about pricing, selection, quantity, options, discounts, or the
  submitted payload changes. **Not breaking**: this is a heading-and-grouping
  change on one screen.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `registration`: the rule fixing the register form's sections currently names
  four — disciplines, team disciplines, optional programme, and one "optional
  items" section covering `rental`, `merch`, and `other_item`. The goods half
  becomes one section per category, each named by its category, and the rule
  gains the ordering and omission behaviour that follows.

## Impact

- `frontend/src/TournamentFace.tsx` — the `optionalItems` filter becomes a
  grouping over the item categories; the register form renders a heading per
  non-empty group. `unanswered` keeps covering every extra row.
- `frontend/src/i18n/{cs,en}.json` — `form.sections.items` gives way to a
  fencer-facing heading per item category.
- Backend: none. `ExtraCategory` and `ACTION_CATEGORIES` already carry the
  classification; no model, schema, API, or migration change.
