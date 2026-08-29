## Why

Once a row has been matched on HEMA Ratings, the profile is the authority on who
the fencer is — but the console keeps identifying rows by what the fencer typed
into a registration form or what an import file happened to spell. Deduplication,
Payments and Export therefore read three tables of self-reported names,
nationalities and clubs, in whatever vocabulary each source used, while the
canonical values sit unused in columns those phases do not show. An organizer
comparing two rows on Deduplication, or reading an export line, cannot tell
whether a difference is a real difference or a spelling.

Name is already promoted to the HR canonical form on a verdict (`hr-integration`,
Canonical naming); nationality and club are not, and no phase after Matching
states which of the three values it is showing.

## What Changes

- From Deduplication onwards — Deduplication, Payments, Export — the table's
  three identity columns SHALL state the matched profile's name, nationality and
  club, not the registered ones. Matching keeps its claim-beside-evidence layout
  unchanged: that comparison is what the phase is for.
- A row with no bound profile keeps its registered name, nationality and club in
  those columns, rendered in italic. The italic is the whole of the marking: the
  reader can see at a glance which lines of the table are HR-backed and which are
  the fencer's own words, and a row without a profile stays identifiable rather
  than collapsing to a dash.
- **BREAKING** (organizer-facing, no data): the identity columns become read-only
  on Deduplication, Payments and Export. An HR-backed value is the profile's, not
  the organizer's, to rewrite; a registered value is corrected where it is
  claimed — on the fencer list, on Import, or by rebinding the id on Matching.
  Identity cells stay editable on Import, Fencers and Matching as today.
- No new rules, no new row fields, no backend change: the HR register already
  travels on every row of the sheet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: the identity columns of the phases after Matching are sourced
  from the HR register, fall back to the registered values in italic, and are
  read-only there.

## Impact

- `frontend/src/Console.tsx` — identity column resolution per phase, the editable
  set becoming phase-dependent.
- `frontend/src/index.css` — the italic register for a non-HR-backed identity
  cell.
- `frontend/src/consoleCells.test.tsx`, `frontend/src/consolePhases.test.tsx` —
  coverage for the resolution and for editability by phase.
- No backend, API, schema or rule change.
