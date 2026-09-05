## Context

Imported rows are keyed by `ImportedRow.key`, a fingerprint of the row's raw
content (`importer.row_fingerprint`). That key is already the tournament's unit
of identity for everything downstream: parse decisions, HR match proposals,
dedup classifications and edit rules all address `imp:<key>`, and
`SheetRowNumber` allocates the fixed fencer number to it once, in arrival order,
never to move again.

Only two places still think in files:

- `sheet._imported_rows` reads `importer.latest_batch` and nothing else, so the
  fencer list and the Import view are populated from one upload.
- `Console.tsx:160` gives Import a numbering of its own — `_source.row`, the
  line in that file — instead of the fixed number every other view shows.

Issuing became part of intake, and that broke the second one. A row from an
earlier file survives as a registration under its `imp:<key>` id; `base_rows`
builds registrations first and adds imported rows with `setdefault`
(`sheet.py:253`), so the registration wins and carries no `_source`. Import's
filter is `id.startsWith("imp:")` (`Console.tsx:194`), which lets that row in
regardless of which file it came from. Result: dashes where numbers belong, and
a sort on `_source?.row ?? 0`.

The uploads this is for are Google Form exports — the same sheet, a few rows
longer each time. Under the batch model every upload renumbers the Import view
from one and drops the previous file from view.

## Goals / Non-Goals

**Goals:**

- Intake takes in only rows the tournament has not seen, recognised by exact
  content fingerprint.
- The Import view is a record of everything the tournament imported, in arrival
  order, numbered by the fixed fencer number.
- Numbers, parse decisions and hand corrections keep surviving a re-upload
  exactly as they do today.
- Clearing remains the one way to make a tournament forget what it imported.

**Non-Goals:**

- Recognising an *edited* row as the row it used to be. A changed cell is new
  content and a new row; deduplication settles the pair. Fingerprinting an
  identity subset of columns is a separate change.
- Showing which file a row came from. The provenance stays recorded, unread.
- Removing a single upload's rows as a unit. See Risks.

## Decisions

### D1. The union happens at intake, not at read

A row whose key the tournament already holds is not persisted a second time; the
batch it arrived in simply does not carry it.

The alternative — take every file in whole and union when the sheet is read — was
rejected because identity is already established at intake: `rownumbers.allocate`
runs there (`importer.py:344`), and `GET /sheet` is a read that allocates
nothing. Unioning at read would mean two `ImportedRow` rows for one key, both
answering to the same decisions and the same number, with the reader picking one.
Skipping at intake keeps one row per key and leaves every downstream reader
alone.

`ImportBatch.row_count` keeps stating what the *file* contained, not what was
new. It is provenance about an upload, and an upload that brought nothing new
still happened.

### D2. Recognition needs no new keying

Keys are computed per file exactly as today, including the occurrence suffix
that gives literally identical lines distinct keys (`fingerprint`,
`fingerprint-2`, …). The union is then one test: skip the keys the tournament
already holds.

That is sufficient because the numbering is deterministic per file. A file
carrying a row twice yields `F` and `F-2`; if the tournament already holds `F`
alone, `F` is skipped and `F-2` is taken in as the second copy it is. No
seeding of occurrence counters across uploads is needed.

### D3. `ImportedRow` becomes unique per tournament

`UniqueConstraint("batch_id", "key")` becomes `("tournament_id", "key")` — the
database then states the invariant D1 establishes. Existing data predates it and
holds the same key in several batches, so the migration collapses each
`(tournament_id, key)` group to its earliest row (lowest `batch_id`) before
adding the index. Earliest, because that is the arrival the fixed number was
allocated against; the collapsed rows are byte-identical to it by construction,
so nothing is lost but the record that a later file also carried them.

Nothing references `ImportedRow.id`: decisions key on `key`, rules and
registrations on the string `imp:<key>`, and `importclear` deletes by tournament.

### D4. Import shows the fixed number

`rowNumber`'s `phase === "import"` branch goes; every phase returns
`row.number`. `rowsForPhase` sorts Import by that number instead of by
`_source.row`. The filter on `id.startsWith("imp:")` becomes correct rather than
accidental: under the union, every `imp:` row does belong to the Import view.

This deletes the special case rather than patching it, and the dashes go with
it — a registration row carries `number` like any other.

Consequence to accept: Import's numbers are the tournament's, so they are not
contiguous where in-app registrations interleave. A view numbered 3, 4, 7, 8 is
telling the truth about which fencers those are; the previous 1..N was a count
of lines in a file that no longer describes the population shown.

### D5. `_source` stays as provenance, unread

It keeps saying which file and which line a row arrived on — the first file to
carry it, since later ones are skipped. Nothing displays it, and it stops being
a sort key or a number. The registration-shadowing gap (`sheet.py:208`, no
`_source` on a registration row) therefore stays open; it becomes worth closing
only when a column asks for it.

### D6. A row the newest file omits stays

`Re-uploading a corrected table` currently promises that a row the new file
drops leaves the fencer list with it. Under a union that promise cannot be kept
and cannot even be stated: two different files do not contain each other's rows,
so omission is indistinguishable from absence.

Removing an imported row becomes what removing any row is — the reversible row
deletion the table already offers — or a clear.

### D7. The import outcome states what was recognised

`import_outcome` gains `skipped`: rows the file carried that the tournament
already held. Without it a hundred-row upload reporting four rows reads as a
failure. `parsed`/`reused` keep their meanings; a skipped row is neither, having
never been a row of this batch.

The `problems` list switches from `row.row_number` to the fixed number, since
that is the number the organizer can now find the row by.

### D8. The parse works on the tournament's undecided rows, not the batch's

Found in implementation, and forced. Resuming an interrupted or failed parse is
done by uploading the file again (spec table-import, Partial parse survives an
interruption): intake reuses the stored decisions and the run does the
remainder. Under the union that upload brings *no rows at all* — they were taken
in the first time — so a parse scoped to the batch would find nothing to do and
the remainder would be unreachable.

Rows belong to the tournament, and so does the work of parsing them. The upload
endpoint therefore asks `importer.imported_rows` for every imported row and
parses those without a decision, whichever upload carried them. The batch stays
what the operation is recorded against.

`import_outcome` follows: it takes the counts rather than a row list, and its
`problems` are the tournament's — every imported row whose parse reported one —
so the count reads as the review queue it is instead of emptying out on an
upload that brought nothing. `reused` keeps its name and its meaning (rows this
upload brought that already had a decision) and is now almost always zero; the
count that carries the meaning it used to is `skipped`.

## Risks / Trade-offs

**An edited row appears twice until dedup runs** → Accepted, and the owner's
decision: this change handles exact matches, dedup handles the rest. The two
rows share a name and a club, which is the case dedup's bands are built for. D7's
count is what tells the organizer a re-upload brought new rows to settle.

**A hand correction does not follow edited content** → Unchanged from today
(`table-import`, Corrections do not follow changed content), but more visible:
the corrected old row now stays in the table beside the new one instead of
vanishing with its batch. Dedup's merge is where the two become one.

**Uploading the wrong file can no longer be undone by uploading the right one**
→ Today the wrong file's rows disappear when the next upload replaces the batch.
Under the union they stay and must be deleted — reversibly, per row — or the
whole import cleared, which is all-or-nothing and takes the good rows with it.
Mitigation for now: the row deletion is reversible and the clear is warned
about. A "remove the rows this upload brought" operation is the honest fix and
is a separate change; the batch of origin is recorded, so it stays possible.

**The migration collapses rows** → It deletes `ImportedRow` records whose key is
held by an earlier batch. They are byte-identical to the survivor by
construction (the key is the content fingerprint), and nothing references their
ids. Verified by counting rows per `(tournament_id, key)` before and after.

**A tournament whose Import view suddenly grows** → A tournament that uploaded
three files sees all three unioned after deploy, where it saw the third. That is
the intent, and the rows were already on the fencer list; only the Import view
changes.

## Migration Plan

1. Alembic revision: collapse duplicate `(tournament_id, key)` rows to the
   earliest, then swap the unique constraint. Downgrade restores the old
   constraint and leaves the collapsed rows collapsed — they are recoverable
   only by re-uploading, which is what the union does anyway.
2. Backend and frontend ship together; no feature flag. The Import view's
   numbering is a display change, and the sheet payload keeps its shape.
3. Rollback: reverting the code without reverting the migration leaves
   `latest_batch` reading a batch that now holds only the rows it introduced —
   the Import view would show too little. Revert both, or roll forward.

## Open Questions

None. Both decisions the change turns on — that changed rows are deduplication's
problem, and that no file column is added yet — were taken by the owner.
