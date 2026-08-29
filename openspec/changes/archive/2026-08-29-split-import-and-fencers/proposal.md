## Why

The console's Load and Parsing tabs show the same rows over four shared columns
and differ only in which three columns follow. Neither answers a question the
other cannot, and one of them shows a column — `problems` — that is structurally
empty for every in-app registration: `sheet.base_rows` sets it to `None` for
`reg:` rows unconditionally. The tabs are named after two halves of one
operation (a file upload parses on intake, in the same request), so Parsing owns
no operation, no parameter panel, and nothing to rerun.

Fencers reach the table by two paths, and those paths want two different views:
an **import** is a batch of rows from a file that may have been misread and needs
checking against its source; the **fencer list** is every fencer known to the
tournament, however they arrived. The current tabs cut across that grain rather
than along it.

Separately, the table's `#` column is a render-position counter (`index + 1`
over the visible rows). Deleting a row renumbers every row below it. The
manual-edits log, which now names each entry's row "by the row's number in the
current table", inherits that: after one deletion, existing log entries name the
wrong fencer's number. A fixed number is what makes that requirement true.

## What Changes

- **Load becomes Import** and shows only imported rows — the latest batch, as
  uploaded, parsed, and hand-corrected. Registrations never appear there.
- **Parsing becomes Fencers** and shows every fencer from both paths, ordered by
  registration moment. It is not a stage between two others; it is the fencer
  list itself, and every later phase is that same list under other columns.
  Duplicates are visible until Deduplication merges them.
- **`notes` and `problems` leave the column list.** Each becomes a narrow marker
  column — `[i]` for a note, `[!]` for a parse problem — shown only on rows that
  carry one, opening the full text in a read-only popup. `[!]` appears on Import
  only; `[i]` appears on both.
- **A fencer's number is fixed.** It is allocated once per tournament when the
  fencer enters the table, never reissued, and never renumbered by a deletion, a
  merge, or a later import. The table sorts by registration moment, so numbers
  may read out of sequence — the number identifies a fencer, it does not count
  rows. Import keeps its own separate numbering: the row's line in the uploaded
  file, scoped to that batch.
- **Rows whose registration moment is unknown sort last**, in file order, rather
  than being given a substitute moment.
- **The console opens on Fencers** instead of Load, so an organizer who never
  imports anything does not land on a permanently empty tab.
- **Two edit logs, two meanings.** Import's log is errata against a batch — the
  machine misread this cell. Fencers' log is the organizer's decisions — add her
  to sabre as well. Re-uploading a corrected file preserves the first and never
  touches the second.
- **The spec's claim that each tab shows "the full fencer list in the state after
  that operation" is retired.** There is one live row set; a phase is a choice of
  columns and one operation's controls beside it.
- **BREAKING** (internal): the `load` and `parsing` phase values on stored rules
  are replaced by `import` and `fencers`; existing rules are migrated. The
  console URLs `/console/load` and `/console/parsing` cease to exist.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: the phase list and their contents, the default phase, per-row
  phase status, fixed row numbering, the marker columns, and how the
  manual-edits log names a row.
- `table-import`: re-uploading a corrected file as a stated behaviour — what
  survives it and what does not.

## Impact

- **Frontend**: `Console.tsx` (phase list, `PHASE_COLUMNS`, `DEFAULT_PHASE`, row
  filtering per phase, the `#` cell), `ManualEditsRail.tsx` (`rowText` stops
  deriving a number from list position), a new marker-cell component and its
  popup, `routes.ts`, `i18n/{cs,en}.json`.
- **Backend**: `sheet.py` (chronological merge of both populations, marker
  fields, the fixed number on each row), `models.py` + a migration for number
  allocation and the rule-phase rename, `importer.py` (allocation at intake),
  `schemas.py`.
- **Not touched**: the rule engine, replay, the append-only journal, the net
  edits projection landed in `net-manual-edits-log`, and the LLM parse itself.
