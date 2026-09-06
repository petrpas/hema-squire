## Why

The disciplines cell on the fencer list opens only for a row that has no
registration behind it (`Console.tsx`, `ROW_ONLY_COLUMNS`). Issuing became a
step of intake, so after any import every row has one — the condition is
effectively dead and the cell never opens. An organizer who imported a roster
with a wrong discipline has no way to fix it in Squire at all, and reports the
feature as broken rather than as withheld.

The rule it guards is real: an issued registration's disciplines are its
entries, and they decide what it is billed and where it is seated. A cell edit
that moved only the table would leave the row saying one thing while the
registration charged another. But Squire already knows how to move both — the
fencer's own amendment (`routers/registrations.py`, `amend_registration`) does
exactly this, re-pricing and re-seating in place. The organizer needs the same
operation from the other side, not a weaker one.

## What Changes

- The disciplines cell opens on the fencer list for **every** row, whether or
  not a registration stands behind it. For a row without one, the edit stays
  what it is today: a correction to the row, applied when it is issued.
- For a row with one, the edit **amends the registration**: its entries are
  replaced, the total is recomputed by the same call the fencer's amendment
  uses, and a discipline that is full is joined as a substitute placement in
  place rather than refused.
- Squire mails the fencer **only where the edit leaves them owing more**
  (`send_surcharge_due`). A correction that lowers the price or leaves it
  unchanged is silent: an organizer straightening an imported roster is not
  sending a letter per corrected row.
- The edit is **not bound by the amendment window**. `amendments_close` and
  lifecycle dormancy govern what a fencer may do to their own registration, not
  what an organizer may correct about the roster.
- The edit persists as a **new rule kind**, so it appears in the phase's
  manual-edits log and can be withdrawn there like every other console
  decision. Withdrawing it re-prices back.
- **BREAKING for `field_edit`**: a disciplines edit on an issued row is no
  longer a `field_edit`. `field_edit` writes to the projected row and would
  move the table without the money; that shape is now refused for a row with a
  registration rather than silently producing the mismatch.

## Capabilities

### New Capabilities
- `discipline-amendment`: an organizer's change to the disciplines of a
  registration that already exists — what it re-prices, what it re-seats, who
  is told, and how it is withdrawn.

### Modified Capabilities
- `etl-console`: the disciplines column's editability rule, which today names
  rows without a registration.
- `edit-rules`: a rule kind that acts on a registration rather than on a
  projected row, and what withdrawing it undoes.

## Impact

**Backend**: `app/rules.py` (the new kind, its validation, its application and
its withdrawal), `app/pricing.py` (read, not changed), a shared amendment core
factored out of `routers/registrations.amend_registration` so the fencer's path
and the organizer's cannot drift, `app/routers/` for the console's edit path,
`app/emails.py` (reuses `send_surcharge_due`).

**Frontend**: `Console.tsx` (`editableHere`, `ruleKindFor`), the disciplines
cell's validation, `i18n/{cs,en}.json`.

**Not affected**: the fencer's own amendment keeps its window, its confirmation
mail and its refusal for a registration that is not RESERVED or PAID. Seating
capacity, discounts and early-bird pricing are read by the existing pricing
call and gain no new rules here.
