## Context

See proposal.md — Why. Three facts of the current implementation shape the
approach:

- `/sheet` is phase-blind. It returns one projection (`sheet.base_rows` +
  `rules.replay`) and the console picks columns per phase from `PHASE_COLUMNS`.
  Splitting Import from Fencers is therefore a filter on the client over a set
  the server already computes — no per-phase endpoint is needed.
- Deleted rows already travel to the client and render struck through
  (`visibleRows = rows`, `row-deleted`). The Import view's requirement to keep
  absorbed rows visible needs no new plumbing, only a per-phase choice about
  which rows to list.
- Imported rows are keyed by a content fingerprint (`importer.row_fingerprint`)
  and appear as `imp:<fingerprint>`; in-app rows appear as `reg:<id>`. Both keys
  are stable across re-upload and rerun, which makes them a sound key to hang a
  permanent number on.

## Goals / Non-Goals

**Goals**

- A number that is stable under every operation the console offers, including
  ones that remove rows.
- One ordering rule for a list built from two populations with unequal data
  quality.
- Keep `/sheet` a read: no allocation as a side effect of viewing.

**Non-Goals**

- Making disciplines editable on the fencer list. The organizer's "add her to
  sabre as well" case is real but is a separate change; this one only puts the
  decisions it produces in the right log.
- Numbering fencers across tournaments, or exposing the number outside the
  console (exports keep their own columns).
- Changing the parse, the match, the dedup bands, or the net-edits projection.

## Decisions

### The number is allocated per tournament and keyed by the sheet row id

A new per-tournament allocation table maps a sheet row id (`reg:<id>` or
`imp:<fingerprint>`) to an integer, unique within the tournament, allocated from
a running maximum. Nothing else is derived from it and nothing reuses a freed
value.

Keying on the sheet row id rather than on the underlying record is what makes
re-upload work: an unchanged CSV row keeps its fingerprint, so it keeps its
number without any special case. It also gives one allocator for both
populations, which a column on `Registration` plus a column on `ImportedRow`
would not — those are two sequences that would have to be reconciled to produce
a single "No." column.

Alternatives rejected:

- **`Registration.id` as the number.** Global autoincrement: numbers would be
  large, gappy, and would leak how many registrations other tournaments have.
  Says nothing about imported rows at all.
- **Derive from chronological position at read time.** Cheapest, and exactly
  what exists today. It cannot satisfy fixedness: a backdated import inserts
  rows and renumbers everything after them.
- **Allocate lazily during projection.** One call site instead of several, but
  `GET /sheet` would write, which makes the read path transactional and makes
  concurrent viewers race for numbers.

### Allocation happens where a row is born

Registration creation allocates; import intake allocates once per new
fingerprint, in file order. Both go through one helper so there is a single
place that knows the rule. Rows that predate the change are backfilled by the
migration in registration-moment order, imported rows after in-app ones.

A projected row that somehow carries no number renders a dash rather than
falling back to a position — a visible gap beats a number that lies.

### Sorting compares wall clock in the tournament's zone

An in-app registration's moment is an instant with a zone; an imported row's is
whatever wall clock the source file stated, and `show-register-times` already
fixed that it is displayed unshifted. Ordering must not compare those two as if
they were the same kind of value. The sort therefore converts in-app moments to
the tournament's zone and compares them as wall clock against the imported ones,
which is the same frame the column displays.

The sort key is: rows with a moment first, by that wall clock, ties broken by
the fixed number; then rows without one, in the order of the file they came
from. A registration moment the parser produced but that does not read as a date
is treated as absent — it sorts last rather than sorting somewhere arbitrary.

### The old phase values are migrated by what the rule targets

Stored rules carry `phase` values `load` and `parsing`, neither of which exists
after this change. The migration maps them by the row a rule targets: a rule on
an `imp:` row becomes `import` (it corrected how a file was read), a rule on a
`reg:` row becomes `fencers` (it was a decision about a fencer that happened to
be made while an import tab was open). Every other phase value is untouched.

A blunt rename of both to `import` was considered. It is simpler but would file
decisions about in-app registrations in the errata log, which is precisely the
distinction this change exists to draw. The target prefix is available in the
same row, so the precise mapping costs one `WHERE`.

### `/console/load` and `/console/parsing` become not-found

The existing requirement is that a phase segment outside the console's known
phases renders the not-found screen. Redirecting the two retired names was
considered and rejected: the tournament is pre-launch, no bookmark to those URLs
exists outside development, and a permanent redirect is a permanent obligation.

### Notes and problems stay columns, and change how they render

`notes` and `problems` remain entries in `PHASE_COLUMNS` and gain a marker
rendering in `CellDisplay`, rather than becoming a new kind of table cell. That
keeps the existing column-label translations, the phase-column machinery, and
the header logic working unchanged. `notes` leaves `EDITABLE_COLUMNS`.

The disclosure is a static bordered panel anchored to the marker, dismissed by
Esc or a click outside — no shadow, no entrance animation, and reachable from
the keyboard, since a marker whose content cannot be opened is only anxiety.

### The edits rail reads the number off the row

`ManualEditsRail.rowText` currently derives the number with
`rows.findIndex(...) + 1`. It takes the row's fixed number instead. The rail
keeps receiving the full row set, not the phase's filtered view, so an entry can
still name a row the current tab does not list.

## Risks / Trade-offs

- **Numbers reading out of sequence look like a defect.** → The column is
  labelled as a fencer's number, set in tabular numerals, and the case only
  arises after an import of backdated rows. The alternative — sorting by number
  — would put a fencer who registered in March below one who registered in May,
  which is worse.
- **Two numbering systems on adjacent tabs.** An organizer may read an Import
  row number as a fencer number. → They are never shown together, and the Import
  view is explicitly a view of one file.
- **The backfill fixes an arbitrary order for existing rows.** → Pre-launch;
  the order chosen (registration moment, imports last) is the same one the list
  will display.
- **Imported registration times are LLM output and may be malformed.** → Treated
  as absent for sorting; the column already shows an em dash for them.

## Migration Plan

One Alembic revision:

1. Create the allocation table with a unique constraint on (tournament, number)
   and on (tournament, row id).
2. Backfill: for each tournament, allocate to in-app registrations in
   `registered_at` order, then to the latest batch's imported rows in file
   order.
3. Rewrite `phase` on stored rules: `load` → `import`; `parsing` → `import`
   where the target begins `imp:`, `fencers` where it begins `reg:`.

Rollback is the inverse rewrite plus dropping the table; no data is destroyed by
the forward migration. The project is pre-launch, so no phased rollout is needed.
