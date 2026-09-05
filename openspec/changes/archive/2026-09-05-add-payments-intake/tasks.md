## 1. Backend: the statement parser seam

- [x] 1.1 Add `StatementParser` Protocol to `backend/app/bank.py`, one method `parse_batch(rows: list[dict[str, str]]) -> list[IncomingTransaction]`, mirroring `importer.ImportParser`
- [x] 1.2 Add `_STATEMENT_SYSTEM_PROMPT` and `LLMStatementParser` over pydantic-ai, modelled on `importer.LLMImportParser`: map each row to `external_id`, `date`, `amount_cents`, `currency`, `vs`, `message`, `payer_name`, `payer_account`; amounts in local text conventions (`1 200,00`, `-1200.00`, split debit/credit columns) become signed integer cents; a row that is not a credit is dropped rather than invented
- [x] 1.3 Add `get_statement_parser() -> StatementParser | None`, returning `None` when `llm.llm_configured()` is false, as `importer.get_import_parser` does — this is the injection point every test overrides
- [x] 1.4 Add `parse_statement(filename, data)`: sniff for the `ID pohybu` header and route to `parse_fio_csv`, else `importer.read_table` + the injected parser. Keep `parse_fio_csv` and all its existing tests untouched
- [x] 1.5 Where a parsed row carries no usable `external_id`, fall back to `importer.row_fingerprint(raw)` so ingestion stays idempotent on banks that supply no movement id
- [x] 1.6 Tests: a non-Fio CSV ingests via a fake parser; a Fio export never reaches the parser (assert the fake is not called); an XLSX reads like its CSV; the same non-Fio file uploaded twice counts every row duplicate; a non-Fio upload with no parser configured returns a stated error and ingests nothing

## 2. Backend: statement parsing as an operation

- [x] 2.1 Add `STATEMENT = "statement"` to `OperationKind` in `backend/app/models.py`
- [x] 2.2 ~~Alembic migration for the added enum value~~ — **none needed**: `str_enum` builds the column with `native_enum=False` and no check constraint, and the live table confirms `kind VARCHAR(30) NOT NULL` with no `CHECK`. The value is storable as-is; existing rows are untouched
- [x] 2.3 Rework `POST /payments/import-statement` to `operations.start(...)` + `operations.run_in_background(...)`, following `routers/import_api.py:73,137`; the response becomes the started-operation handle and the ingest counts move to the operation's `outcome`
- [x] 2.4 Batch the parse at `importer.PARSE_BATCH_SIZE`, committing each batch's decisions with its progress through `operations.advance`, so an interrupted run resumes rather than restarting
- [x] 2.5 Cache per row: `importer.get_decision` / `store_decision` with `kind="statement_row"`, `key=importer.row_fingerprint(raw)`. Reuse the existing table; add no new one
- [x] 2.6 Tests: progress advances per batch; a second concurrent operation is refused with the running kind named; a re-upload reuses stored decisions and calls the parser only for genuinely new rows; the outcome carries the ingest counts
- [x] 2.7 Update `scripts/seed_demo.py`, which reads the old inline counts from this endpoint
- [x] 2.8 (found during implementation) Migrate the test suite off the synchronous response. The design said no caller would break, which was true of production and false of `tests/`: thirteen files read the inline counts. Added `conftest.import_statement`, which posts and returns the concluded operation's outcome, and pointed each file's local helper at it

## 3. Frontend: API surface

- [x] 3.1 Add `importStatement(slug, file)` to `frontend/src/api.ts` as a multipart post returning the started operation; extracted the multipart dance `importTable` inlined into a shared `upload<T>` helper rather than copying it
- [x] 3.2 Add `fioPoll(slug)` and `processLifecycle(slug)`
- [x] 3.3 Add `fio_token_configured: boolean` to the tournament detail type if the API already states it; otherwise add it to `TournamentDetail` server-side — never the token itself, only whether one is set

## 4. Frontend: the intake card

- [x] 4.1 Create `frontend/src/payments/IntakePanel.tsx` as a rail card beside `TolerancePanel`, modelled on `ImportPanel.tsx` — it already runs a file upload as an operation and reads its conclusion
- [x] 4.2 Statement upload: file input accepting `.csv` and `.xlsx`, starting the operation and refreshing the sheet and the queues when it concludes
- [x] 4.3 Poll Fio now: offered only where the tournament has a token; where it has none, omit the action and state that no token is configured rather than offering a control that answers `409`
- [x] 4.4 Run lifecycle now: calls `processLifecycle`, then refreshes
- [x] 4.5 Disable all three while another operation is running, naming which, via `operations.running` as `DedupPanel` does
- [x] 4.6 Mount it in `Console.tsx` on the payments phase, above `TolerancePanel` in the rail
- [x] 4.7 Tests (`frontend/src/payments/intakePanel.test.tsx`): the poll action is absent and explained without a token; all three disabled while another operation runs; a concluded import refreshes; an upload posts the file

## 5. Localization

- [x] 5.1 Add `payments.intake.*` to `frontend/src/i18n/en.json` — title, upload, poll, lifecycle, the no-token line, the no-parser line, the busy line
- [x] 5.2 Add the Czech equivalents in the same pass; `locale-parity.test.ts` covers that neither drifts
- [x] 5.3 Grep the new component for hardcoded user-facing strings; there should be none

## 6. Design compliance and verification

- [x] 6.1 Review `IntakePanel` against `CLAUDE.md`: no gradients, shadows, blur, radii > 2px, emoji, filled icons, spinners, `#FFF`/`#000`, weight 600+, Title Case, or hexes outside `tokens.css`
- [x] 6.2 Confirm it reuses `rail-card`, `rail-hint`, `row-action`, `secondary` and adds no new CSS beyond `tokens.css` values
- [x] 6.3 Run `npm run lint`, `npm test`, `npm run build` in `frontend/`
- [x] 6.4 Run `pytest` in `backend/` (note: `test_pilot_naduel.py` fails on machines without the private v1 archive, and should be skipping rather than failing — out of scope here)
- [~] 6.5 Drive the console: import a real non-Fio statement, watch the operation run, and confirm the transactions land in the unmatched and flagged queues and the outstanding column moves

  Partly done: driven read-only against the running console on `na-duel-2026`.
  The intake card renders at the top of the payments rail with the statement
  upload and the lifecycle action; the poll action is correctly absent, with
  the no-token line in its place, which confirms `fio_token_configured` reaches
  the frontend from the real API. Importing an actual file writes to the
  owner's pilot data, so it is not done.
- [~] 6.6 With intake in place, finish `add-payments-console-ui` task 9.5 — the populated-state end-to-end check it left open for want of a way to get payments in
