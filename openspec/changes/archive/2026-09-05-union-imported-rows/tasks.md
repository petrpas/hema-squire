## 1. Intake takes in only new rows

- [x] 1.1 In `importer.intake`, after computing each row's key, skip the rows whose key the tournament already holds; load those keys once per upload rather than per row
- [x] 1.2 Keep `ImportBatch.row_count` at the file's row count and return only the rows actually taken in, so `undecided_rows` and the parse loop see the new rows alone
- [x] 1.3 Add `skipped` to `importer.import_outcome` and report the fixed number rather than `row_number` in its `problems` entries
- [x] 1.4 Surface the skipped count in the import operation's console message (`i18n` both languages)
- [x] 1.6 Scope the parse to the tournament's undecided rows rather than the batch's, so a re-upload still resumes an interrupted parse (design D8); `import_outcome` takes counts and reports the tournament's problems
- [x] 1.5 Tests: appending rows to the same file takes in only the new ones; a file bringing nothing new makes no LLM call and reports every row recognised; a row edited between uploads arrives as a second row; a file carrying a row twice against a tournament holding it once takes in one further copy

## 2. Uniqueness per tournament

- [x] 2.1 Change `ImportedRow.__table_args__` from `UniqueConstraint("batch_id", "key")` to `("tournament_id", "key")`
- [x] 2.2 Alembic revision: collapse each `(tournament_id, key)` group to its lowest `batch_id` row, then swap the constraint; downgrade restores the old constraint only
- [x] 2.3 Test the migration against a database holding the same key in three batches: one row survives per key, it is the earliest, and the numbers allocated to those keys are untouched

## 3. The sheet reads every batch

- [x] 3.1 `sheet._imported_rows`: replace the `latest_batch` lookup with every `ImportedRow` of the tournament, joined to its batch for `_source`, ordered by arrival
- [x] 3.2 `rownumbers.arrival_order`: cover every batch rather than the latest, in arrival order, so a restore without recorded numbers reproduces them
- [x] 3.3 Tests: a tournament with two batches lists the rows of both once each, with the numbers they were allocated; a row issued a registration still appears among them

## 4. Import numbers by the fixed number

- [x] 4.1 `Console.tsx`: drop the `phase === "import"` branch from `rowNumber` and sort Import by `number` in `rowsForPhase`
- [x] 4.2 Update `consoleMarkers.test.tsx` and `consolePhases.test.tsx` to the fixed-number expectations, including a row that carries a number but no `_source`
- [x] 4.3 Verify in the running app that the Import view of a tournament whose rows were issued registrations shows numbers rather than dashes, and that a second upload appends rather than renumbering

## 5. Specs and cleanup

- [x] 5.1 Remove `importer.latest_batch` if `/import/status` is its last caller, or keep it for that endpoint alone with a comment saying it describes the newest upload, not the tournament's rows
- [x] 5.2 Run the full backend and frontend suites; fix the tests that assumed batch replacement
- [x] 5.3 `openspec validate union-imported-rows --strict` (the delta specs sync into `openspec/specs/` at archive, not here)
