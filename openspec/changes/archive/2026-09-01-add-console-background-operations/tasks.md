## 1. The operation record

- [x] 1.1 Add the `Operation` model per design D1 (`tournament_id`, `kind`, `status`, `total`, `done`, `started_at`, `finished_at`, `started_by`, `outcome` JSON) with an index on `(tournament_id, finished_at)`, and its Alembic revision; verify the migration applies and reverts against a copy of the dev database
- [x] 1.2 Add `operations.py` with `start(session, tournament, kind, total, fencer)` returning the record and refusing with a conflict when the tournament already has one unconcluded, `advance(session, operation, units)` committing the caller's work and the raised count in one transaction, and `conclude(session, operation, status, outcome)`; verify with unit tests per function
- [x] 1.3 Test that a second start for the same tournament is refused whatever its kind, and that a start for a different tournament is not (spec console-operations, One operation at a time for a tournament)
- [x] 1.4 Test that `advance` never leaves a count describing uncommitted work — a session rolled back after `advance` leaves neither the decision nor the raised count (spec, The count never runs ahead of the results)

## 2. The runner and crash recovery

- [x] 2.1 Add `operations.run_in_background(kind, tournament_id, fencer_id, body)` per design D3: `asyncio.create_task` over `asyncio.to_thread`, the body opening its own `SessionLocal`, every exception concluding the record as failed with the error text in `outcome` and logging it; verify with a test that a body raising concludes the record failed rather than leaving it running
- [x] 2.2 Add the startup sweep to the lifespan in `main.py` beside `_populate_hr_index_if_empty()`, concluding every unconcluded operation as interrupted, with the comment naming its dependence on `--workers 1` per design D5; verify with a test that a record left running is interrupted on startup
- [x] 2.3 Test that an interrupted operation keeps its committed work and that re-running does only the remainder (spec, Re-running finishes the remainder)

## 3. Parsing per batch

- [x] 3.1 Narrow `ImportParser` to `parse_batch(rows, disciplines, rentals)` and move the batch loop out of `LLMImportParser` into `importer`, dropping the parser's `batch_size` knob; update the test fakes; verify the existing import tests pass unchanged
- [x] 3.2 Rework `importer.import_table` into an intake half that writes the batch, its rows and their numbers and returns, and a `parse_undecided(session, tournament, parser, batch, operation)` half that loops batches, storing each batch's decisions and advancing the operation in one commit per design D4; verify with a unit test that decisions of a completed batch are readable while later batches are outstanding
- [x] 3.3 Set the operation's total to the count of undecided rows, not the file's row count; verify with a test that re-uploading an unchanged file yields a total of zero (spec, Reused rows are not work)
- [x] 3.4 Test that a parse raising midway leaves the earlier batches' decisions standing and concludes the operation failed (spec table-import, Partial parse survives a failure)
- [x] 3.5 Add progress reporting to `hr_match.run_matching` and `dedup.run_dedup` against the rows they already build, advancing per row on the same write-and-count-together rule; verify with a test per operation that the count reaches the row total

## 4. Endpoints

- [x] 4.1 Rework `POST /api/tournaments/{slug}/import` to read the file, write the batch and rows, start the operation and return `202 {"operation_id": n}`, keeping the unparsed-and-no-LLM path returning its present shape without starting an operation; verify with API tests for both paths (spec table-import, Upload returns before the parse / No LLM configured)
- [x] 4.2 Rework `POST /import/match` and `POST /import/dedup` the same way; verify with API tests that each returns 202 and that the work lands afterwards
- [x] 4.3 Return `409` naming the running kind when a start is refused, on all three endpoints; verify with an API test per endpoint
- [x] 4.4 Add `GET /api/tournaments/{slug}/operations` behind `require_console_access`, returning the running operation and the most recent concluded one per kind; verify with an API test covering idle, running, and concluded, and that a non-organizer is refused
- [x] 4.5 Test that a client abandoning the upload response leaves a complete batch and a parse that runs to its end (spec, Batch survives an abandoned upload response)

## 5. The console's one poll

- [x] 5.1 Add `api.operations(slug)` and the operation types to `api.ts`, and change the three start calls to expect `202` and a conflict shape; verify by type-check
- [x] 5.2 Add `useOperations(slug)` polling every 2 seconds while anything runs and not at all when nothing does, and calling a supplied `onLanded(kind)` when a kind leaves `running`, per design D7; verify with a hook test covering the poll starting, stopping, and firing the callback once per conclusion
- [x] 5.3 Wire the hook in `Console.tsx` with `onLanded` calling `refresh()`; verify with a component test that a conclusion arriving from the poll reloads the sheet with no user action (spec etl-console, Results appear without a refresh)

## 6. Panels and the indicator

- [x] 6.1 Remove the local `busy` state from `ImportPanel.tsx`, `MatchPanel.tsx` and `DedupPanel.tsx`, taking readiness from the hook's running operation and the result line from the concluded operation's `outcome`; verify with a component test per panel that a running operation disables the action and names what runs, and that the report survives a remount (spec, A phase panel reports its own phase's operation)
- [x] 6.2 Keep `MatchPanel`'s index refresh on its own local state — it is not a tournament operation and is not subject to the lock; verify the existing panel test still passes
- [x] 6.3 Add `OperationsIndicator.tsx` per design D8: fixed bottom right, `--paper-raised` on a `--hairline` frame, 2px radius, an uppercase `--label-size` kind, a `--font-data` count, `--ink-faded` start time, no shadow and no motion; mount it in `Console.tsx` outside the workspace; verify with a component test that it is absent when idle, states the count while running, and holds then fades on conclusion
- [x] 6.4 Add the indicator's styles to `index.css` using tokens only, with no `box-shadow`, no keyframes beyond the fade-out, and no hex outside `tokens.css`; verify by reading the added rules against CLAUDE.md's prohibition list
- [x] 6.5 Add the `cs` and `en` strings for the three kinds, the counted progress line, the conflict refusal, the failure, and the interrupted wording — the last stating that the work stopped partway and that running it again finishes it, in the design spec's register: lower case, no exclamation marks, no emoji (spec, Interruption is not failure); verify both files carry the same keys

## 7. End to end

- [x] 7.1 Test the reload case whole: start a long parse, drop the client, load the console afresh, and assert it reports the import running with progress (spec, Reload during a long import)
- [x] 7.2 Test the restart case whole: leave an operation running, run the startup sweep, and assert the console reports it interrupted and nothing running (spec, Restart clears a phantom)
- [x] 7.3 Check the three concurrency-readiness properties of design D6 hold in the code as written — a counter rather than an index, per-unit commits, no order assumption in the record, the endpoint or the console — and note in `design.md` any place that drifted
