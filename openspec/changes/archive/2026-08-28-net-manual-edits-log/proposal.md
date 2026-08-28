## Why

The manual-edits log lists one entry per rule application, so operations that
undo one another pile up instead of cancelling: deleting a row, restoring it,
and deleting it again leaves three entries for a single net change. The entries
are also written in the table's internal vocabulary — `_deleted: false → true`
against a row id like `imp:c1aa278b8e464cc3` — where the organizer needs to read
which row, by name, changed how.

## What Changes

- The edits log states the **net difference from the source data**, one entry per
  changed cell, rather than the history of applied changes. Rules that return a
  cell to its source value produce no entry at all.
- An entry is attributed to the newest rule that contributed to it, and sits in
  that rule's phase.
- Removing an entry removes **every rule behind it**, so the cell returns to its
  source value in one action rather than one action per rule.
- Entries name the row the way the table does — its number and the fencer's name
  — instead of its internal id.
- Entries are phrased in the organizer's words: a deletion reads as a deletion, a
  merge as a merge into a named row, and field names use their column labels.
  Both languages get the copy.
- **BREAKING** (internal): `GET /sheet` returns net entries in `edits` in place
  of per-application audit entries; each carries a list of rule ids rather than
  one. Nothing outside the console consumes it.

The rule engine, the replay, and the append-only journal are untouched. Every
rule still exists, still replays, and the journal still answers who did what and
when — this changes only what the log presents.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `edit-rules`: the audit of applied changes becomes a net statement per cell —
  cancelling rules leave no entry, and an entry is removed as a whole.
- `etl-console`: the manual-edits log names rows and phrases changes in the
  organizer's vocabulary.

## Impact

- `backend/app/rules.py` — a net-difference projection over the replay audit.
- `backend/app/schemas.py` — `AppliedChangeOut` gains rule ids, loses its
  one-rule identity.
- `backend/app/routers/rules_api.py` — `/sheet` returns the net entries.
- `frontend/src/Console.tsx` — the edits rail renders readable entries and
  removes an entry's whole rule set; the rail is a candidate for its own file.
- `frontend/src/i18n/{cs,en}.json` — labels for the fields and pseudo-fields the
  log can name, and the sentence forms for deletion and merge.
