## 1. Fixed fencer number

- [x] 1.1 Add the per-tournament number allocation model (row id → number, unique on both (tournament, row id) and (tournament, number)) and one allocator helper; unit test asserts a freed number is never reissued
- [x] 1.2 Allocate on registration creation; test that a new registration receives the next number and keeps it after an unrelated row is deleted
- [x] 1.3 Allocate at import intake, one per new fingerprint in file order; test that re-uploading an unchanged file allocates nothing new and changed rows get fresh numbers
- [x] 1.4 Alembic revision creating the table and backfilling existing tournaments (registrations by `registered_at`, then latest batch in file order); verify `alembic upgrade head` then `downgrade` runs clean on a copy of `hema_squire.sqlite`
- [x] 1.5 Expose the number on each projected row in `sheet.base_rows` and in `SheetOut`; test that a row with no allocation carries null rather than a positional fallback

## 2. Ordering of the fencer list

- [x] 2.1 Sort the merged projection by wall clock in the tournament's zone, ties by number, rows without a readable moment last in file order; test with an in-app registration, an imported row with an earlier moment, and an imported row with none
- [x] 2.2 Test that a malformed parser-produced registration time is treated as absent and sorts last rather than raising

## 3. Phase split

- [x] 3.1 Rename `load` → `import` and replace `parsing` with `fencers` in `PHASES`, `PHASE_COLUMNS`, `routes.ts`, and both locale files; `npm run build` and the locale-parity test pass
- [x] 3.2 Set `DEFAULT_PHASE` to `fencers`; test that `/organizer/:slug/console` opens Fencers and that `/console/load` renders not-found
- [x] 3.3 Filter the table per phase — Import lists `imp:` rows only (including deleted and absorbed, marked), Fencers and later phases list every row; test both with a mixed fixture
- [x] 3.4 Number the Import view by the imported row's line in its batch, and the fencer list by the fixed number; test that deleting a row leaves both numberings untouched
- [x] 3.5 Move the import controls to the Import phase only and confirm the Fencers phase shows no parameter panel

## 4. Note and problem markers

- [x] 4.1 Render `notes` and `problems` as markers in `CellDisplay`, shown only when content is present; test that an empty note renders nothing at all, not a dash
- [x] 4.2 Add the read-only disclosure panel (Esc and click-outside dismiss, keyboard reachable, no shadow or animation); test open, close by each route, and that the text is not editable
- [x] 4.3 Put `[i]` in the column set of both Import and Fencers and `[!]` in Import's only; remove `notes` from `EDITABLE_COLUMNS`; test that a registration's own note is reachable on the fencer list
- [x] 4.4 Czech and English copy for both markers and the disclosure; locale-parity test passes

## 5. Manual-edits logs

- [x] 5.1 `ManualEditsRail.rowText` reads the row's fixed number instead of `findIndex + 1`; test that an entry keeps naming the same fencer after an earlier row is deleted
- [x] 5.2 Migrate stored rule phases in the same Alembic revision — `load` → `import`; `parsing` → `import` for `imp:` targets and `fencers` for `reg:` targets; test the mapping on a fixture with both target kinds
- [x] 5.3 Test that a correction made on Import appears in Import's log only, and one made on Fencers in the fencer list's log only

## 6. Specs and verification

- [x] 6.1 `openspec validate split-import-and-fencers --strict` passes
- [x] 6.2 Full backend and frontend test suites pass; run the console against the dev database and check a mixed tournament renders both tabs, the markers, and stable numbers across a delete and a re-upload
