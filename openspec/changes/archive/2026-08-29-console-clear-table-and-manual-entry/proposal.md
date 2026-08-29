## Why

Two things an organizer needs at the console today have no action anywhere.

The first is undoing an import. Uploading the wrong file — last year's sheet, a
half-finished export, the registration table of a different tournament — is a
single click, and nothing takes it back. Re-uploading the right file does not
help: the fencer list keeps only what the newest batch contains, but the wrong
file's parse decisions, its corrections, and the numbers it consumed all stay
behind, and the mistake stays visible in the Import log for good. There is no
way to say *that never happened*.

The second is entering a fencer by hand. A fencer who pays at the door, one
whose form arrived by mail, one the organizer signed up over the phone — none
of them can reach the table at all. The two ways in are in-app registration,
which only the fencer can perform, and file import, which needs a file. An
organizer with one fencer to add has to build a one-row spreadsheet and import
it.

## What Changes

- **Import gains a Clear table action**, beside the upload in its rail. It
  removes everything the tournament ever imported — every batch, every source
  row, the parse, match, merge and dedup decisions taken about those rows, the
  organizer's corrections to them, and the fixed numbers those rows held. What
  remains is what never came from a file. The Import view goes empty and stays
  empty until the next upload.
- **Clearing is a hard delete and says so before it happens.** A confirmation
  states what will be removed, in rows and in files, and states that it cannot
  be undone. This is not the reversible row deletion the table already offers;
  it is the removal of a source. Registrations are never touched by it.
- **The retirement of numbers is broken here, and only here.** A cleared row's
  number returns to the pool, because a cleared row is one the tournament is
  asserting never existed. Numbers still held by registrations are never
  reissued.
- **Fencers gains a Manual entry action**, in its rail. It opens a dialog whose
  fields are the tournament's own structure — its offered individual
  disciplines, the items it lends, whether it holds an afterparty — rather than
  a generic fencer form. Submitting adds one row to the fencer list.
- **A manually entered row is a third source population**, beside in-app
  registrations and imported rows. It is an organizer-authored source record:
  it takes a fixed number, sorts by its registration moment, carries a note,
  and travels through matching, deduplication and export exactly as an imported
  row does. It creates no account, no VS, and no payment instruction, and sends
  no mail — the same limits an imported row already lives under.
- **A manual entry never appears on the Import view.** The Import view is the
  record of a file, and nobody typed a file.
- **Validation is strict and refuses rather than repairs.** A name is required,
  a discipline must be one the tournament offers as individual, a rental must
  be an item it lends, an hr_id must be a whole number, a registration moment
  must be readable. Nothing is guessed, defaulted into place, or silently
  dropped; the dialog names the field it will not accept and keeps the rest of
  the organizer's typing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `table-import`: clearing the tournament's imported content outright — what it
  removes, what it leaves, and that it is irreversible.
- `etl-console`: the manual entry action and its dialog, the third source
  population and how it behaves in each phase, the numbers released by a clear,
  and where each of the two new actions lives in the rail.

## Impact

- **Backend**: a `ManualRow` model and its migration; `sheet.py` (a third
  population in `base_rows`); a `manualrows.py` module beside `rownumbers.py`;
  `rownumbers.py` (arrival order, and releasing numbers on a clear); a clear
  endpoint on `import_api.py` and a manual-entry endpoint beside it;
  `export_json.py` (export and restore of manual rows); `schemas.py`.
- **Frontend**: `ImportPanel.tsx` (the clear action and its confirmation),
  a new `ManualEntryPanel.tsx` and `ManualEntryDialog.tsx` under a
  `frontend/src/manual/` directory, `Console.tsx` (mounting the Fencers rail
  panel), `api.ts`, `i18n/{cs,en}.json`.
- **Not touched**: the rule engine and replay, the append-only journal beyond
  the entries of rules being cleared, the parser, in-app registration, pricing,
  and payments.
- **Depends on** `split-import-and-fencers`, whose Import and Fencers phases
  are the two places these actions live.
