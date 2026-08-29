## Why

A deleted row is not removed from the table — it is marked, and every phase
after the deletion keeps listing it struck through. The organizer who deleted a
row on Import meets it again on Fencers, on Matching, on Payments: five more
reminders of a decision already made. The strike-through says "handled", but a
handled row occupying a line of the table is still a line to read past, and on
the later phases it can no longer say anything useful — it is excluded from the
counts, from dedup, from HR matching, and from the export.

The deletion is a decision taken at one step of the console. That step is where
it can be reconsidered, and the only place it needs to remain visible.

## What Changes

- **A deleted row is listed on the phase whose deletion removed it, and on the
  phases before it; the phases after do not list it.** The row is still in the
  data and still in the projection — the change is what a table shows, not what
  the sheet holds.
- **A deletion is undone where it was made.** The restore button is offered
  exactly where the row is still listed, and the manual-edits log of that phase
  keeps its entry, so a deletion made on Fencers is reversed on Fencers.
- **A row absorbed by a merge is gone from every table but Import.** Today it
  renders struck through on all of them, which the existing Import-view
  requirement already contradicts; a merge is a statement about identity, true
  on every phase, not a step-local decision to be reconsidered later.
- **The projection states which phase removed a row**, so the table can tell a
  deletion made on Payments from one made on Import. Nothing else reads it.
- Rows whose removing phase cannot be placed in the phase order stay listed
  everywhere, as they are today: a row that cannot be located is never hidden.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: the row set a phase lists now depends on where a row was
  deleted — it is no longer "one and the same set of rows" from Fencers onward.
  Reversible row deletion gains where the reversal is offered.
- `edit-rules`: the replayed projection carries the phase that removed a row,
  alongside the removal itself.

## Impact

- `backend/app/rules.py` — replay records the removing phase on the row.
- `backend/app/sheet.py` — docstring of the projection; no new base field.
- `frontend/src/Console.tsx` — `rowsForPhase` filters by removing phase; the
  actions column offers restore only where the row is listed.
- `frontend/src/api.ts` — `SheetRow` gains the removing phase.
- Tests: `backend/tests/test_rules.py`, `frontend/src/consolePhases.test.tsx`.
- No migration, no API shape break: the field is additive and derived on every
  replay.
- Depends on `split-import-and-fencers` (Import/Fencers split, phase-scoped
  edit logs), which is implemented but not yet archived.
