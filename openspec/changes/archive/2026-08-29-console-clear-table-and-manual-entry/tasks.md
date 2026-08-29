## 1. Clearing the imported content — backend

- [x] 1.1 Add `importclear.clear_imports(session, tournament)` performing the ordered deletion of design D3 (journal entries, rules naming an imported row as target or in payload, decisions reachable from cleared rows, `SheetRowNumber` rows for `imp:` ids, `ImportedRow`, `ImportBatch`) in one transaction, returning the counts of rows and files removed; verify with a unit test asserting each of those tables is empty for the tournament afterwards
- [x] 1.2 Add `DELETE /api/tournaments/{slug}/import` to `import_api.py` behind `require_console_access`, returning `{"rows": n, "files": n}`; verify with an API test that a non-organizer is refused and an organizer gets the counts
- [x] 1.3 Test that registrations survive a clear untouched — content, notes, fixed numbers, and their own rules and journal entries all intact (spec table-import, Registrations survive a clear)
- [x] 1.4 Test that all batches go, not only the latest: upload three files, clear, and assert the Import view falls back to no batch at all (spec, Superseded batches go too)
- [x] 1.5 Test decision removal per kind — `parse`, `hr_match`, `merge`, `dedup` — asserting `import_decisions` holds nothing for the tournament after a clear (design D3, risk of a missed key shape)
- [x] 1.6 Test that a merge folding an imported row into a registration is removed with it, leaving the registration unmerged and listed (spec, Merge decision naming a cleared row)
- [x] 1.7 Test that re-importing after a clear parses every row afresh, reusing no decision and no correction (spec, Re-import after a clear starts clean)
- [x] 1.8 Test that numbers are released: a table numbered 1–30 whose 11–30 came from a file numbers its next row 11 after a clear (spec etl-console, Clearing releases the cleared numbers)

## 2. Clearing the imported content — console

- [x] 2.1 Add `api.clearImports(slug)` to `api.ts` calling the new endpoint; verify by type-check and its use in the panel below
- [x] 2.2 Add the clear action and its static confirmation modal to `ImportPanel.tsx`, offered only when a batch exists, stating the row and file counts and that the removal cannot be undone, reusing the `modal-backdrop` / `modal` / `modal-actions` classes; verify with a component test covering: action absent with no batch, dismissal changing nothing, confirmation calling the endpoint and refreshing
- [x] 2.3 Add the `cs` and `en` strings for the action, the confirmation title, body, counts and confirm label, in the design spec's register — lower case, no exclamation marks, no emoji; verify both files carry the same keys

## 3. The manual population — backend

- [x] 3.1 Add the `ManualRow` model per design D1 (scalars as columns, `disciplines` and `weapon_rentals` as JSON, `afterparty`, `created_by`, `created_at`) and its Alembic revision; verify the migration applies and reverts against a copy of the dev database
- [x] 3.2 Add `manualrows.py` with creation and listing helpers beside `rownumbers.py`, allocating the row's fixed number as `man:<id>` at creation; verify with a unit test that a new manual row takes the next number and keeps it after a later import
- [x] 3.3 Add `_manual_rows` to `sheet.py` and merge it into `base_rows` beside `_imported_rows`, with `state: "manual"`, `problems: None`, no `_source`, and `match_verdict` from whether an hr_id was given; verify with a test that a manual row appears on the fencer list with its disciplines and rentals resolved
- [x] 3.4 Extend `rownumbers.arrival_order` to include manual rows in their creation order; verify with a test that a document recording no numbers restores them in the order rows entered
- [x] 3.5 Export and restore manual rows in `export_json.py`, tolerating a document that carries none; verify with a round-trip test that a tournament with manual rows exports and restores with numbers and content intact
- [x] 3.6 Test that a manual row interleaves by its registration moment and that a backdated one sorts into place rather than at the end (spec etl-console, Backdated manual entry interleaves)
- [x] 3.7 Test that a manual row never appears on the Import view whatever its state (spec, Manual entry absent from Import)
- [x] 3.8 Test that a manual row is matchable and deduplicable — it reaches the dedup queue when it shares an hr_id with an imported row (spec, Manual row deduplicates like any other)

## 4. Manual entry endpoint and validation

- [x] 4.1 Add `ManualEntryIn` to `schemas.py` stating shape — required non-blank name, integer hr_id, e-mail form, ISO registration moment, optional nationality/club/note — with empty optionals recorded as absent; verify with unit tests per field
- [x] 4.2 Add `_resolve_manual_entry` validating tournament fit — offered individual disciplines only, lent items only — raising 422 with the `unknown_disciplines` / `team_discipline_not_individual` / `unknown_weapons` detail shapes the registration path already uses; verify with a test per refusal
- [x] 4.3 Add `POST /api/tournaments/{slug}/manual-rows` behind `require_console_access`, defaulting the registration moment to now in the tournament's zone, creating the row and allocating its number in one transaction; verify with an API test that a valid entry returns the created row and it appears in the next `GET /sheet`
- [x] 4.4 Test that at least one discipline is required and a blank name is refused, with no row added in either case (spec, Strict validation of a manual entry)
- [x] 4.5 Test that an entry duplicating an existing fencer is accepted rather than refused (spec, Duplicate is allowed through)

## 5. Manual entry — console

- [x] 5.1 Add `api.createManualRow(slug, entry)` and its types to `api.ts`; verify by type-check
- [x] 5.2 Add `manual/ManualEntryDialog.tsx`: the modal form offering the tournament's individual disciplines, its lent items, and the afterparty only where one exists, defaulting the moment to now in the tournament's zone, using `useFieldValidation` and rendering server refusals through `FieldError` against the named field; verify with a component test covering a valid submission, a refused field keeping the rest of the form, and the absence of team disciplines
- [x] 5.3 Add `manual/ManualEntryPanel.tsx` as the Fencers rail card that opens the dialog, and mount it in `Console.tsx` for `phase === "fencers"` only; verify with a test that the action is offered on Fencers and on no other phase (spec, Where the two source actions live)
- [x] 5.4 Test that a tournament holding no afterparty asks nothing about one, and one lending nothing offers no items (spec, Manual entry fields follow the tournament's structure)
- [x] 5.5 Add the `cs` and `en` strings for the panel, the dialog's field labels, its refusals and its buttons; verify both files carry the same keys

## 6. Verification across the whole change

- [x] 6.1 Run the backend suite and the frontend suite green, and `ruff` / `tsc` clean
- [x] 6.2 Walk the two flows in the running app: upload a wrong file, clear it, confirm Import and the fencer list are as if it never arrived; then enter a fencer by hand on Fencers and confirm the row, its number, its place in the order, and that Payments shows it as it shows an imported row
- [x] 6.3 Check both new surfaces against the design prohibitions in CLAUDE.md — no shadow, no radius above 2px, no second saturated colour, static confirmation, no emoji or filled icons
