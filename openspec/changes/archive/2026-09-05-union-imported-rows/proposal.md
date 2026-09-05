## Why

A tournament's registration table is not uploaded once. It is a Google Form
export that grows: the same file, a few rows longer, uploaded again and again.
Today each upload replaces the last as *the* imported batch, and the Import view
shows only that batch — numbered by line in the file, a number that starts again
at one every time.

That model has stopped holding. Issuing a registration is now part of intake, so
a row that came from an earlier file survives as a registration under its own
`imp:<key>` id and leaks into the Import view of the *next* file, where it has no
line number and no place. Every row in that view now reads a dash where its
number should be, and the view sorts on a number nobody has.

The file-shaped model is what is wrong. An imported row belongs to the
tournament, not to the upload that carried it.

## What Changes

- Intake becomes a union. A row whose content the tournament has already
  imported is recognised at intake and not taken in a second time; only rows new
  to the tournament become source rows. Recognition is exact — the same content
  fingerprint that already survives a re-upload today. A row the organizer
  *edited* between uploads is new content and arrives as a new row; the pair is
  deduplication's to settle, as any two rows describing one fencer are.
- The Import view shows everything the tournament has imported, from every
  upload, in the order the rows arrived — not the latest file alone.
- Import stops numbering by line in the file and uses the fixed fencer number,
  as every other view does. The number is already allocated in arrival order and
  already survives a re-upload; Import was the one place that ignored it.
- **BREAKING** A row the newest file omits no longer leaves the fencer list.
  Once imported, a row belongs to the tournament; removing it is the reversible
  row deletion the table already offers, or a clear.
- Clearing is unchanged: it already removes every batch, row, decision,
  correction and number the tournament ever imported, and it stays the one way
  to make the tournament forget what it has seen.
- The file and line a row arrived from stay recorded as provenance. No column
  displays them yet.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `table-import`: intake recognises rows the tournament has already imported and
  takes in only what is new; re-uploading no longer replaces the previous batch,
  and an omitted row no longer leaves the list.
- `etl-console`: the Import view shows every imported row rather than the latest
  batch, and numbers its rows by the fixed fencer number rather than by line in
  the file.

## Impact

- `backend/app/importer.py` — `intake` seeds its duplicate check from the keys
  the tournament already holds and skips known rows; the batch records only what
  it actually brought.
- `backend/app/sheet.py` — `_imported_rows` reads every batch's rows rather than
  `latest_batch`'s.
- `backend/app/rownumbers.py` — `arrival_order` (restore of a document that
  records no numbers) covers every batch.
- `backend/app/models.py` + migration — `ImportedRow`'s uniqueness becomes
  per tournament rather than per batch.
- `frontend/src/Console.tsx` — `rowNumber` loses its Import special case and
  `rowsForPhase` sorts Import by the fixed number. Both shrink.
- `POST /api/tournaments/{slug}/import` outcome gains a count of rows recognised
  and skipped, so the organizer sees why a hundred-row file brought four rows.
- Unaffected: parse decisions and edit rules, which are keyed by row key and not
  by batch; `importclear`, which already works on everything imported.
