## Why

The Payments phase can now resolve unmatched money four ways, and still has no
way to receive any. `POST /payments/import-statement`, `POST /payments/fio-poll`
and `POST /payments/process` have **zero frontend callers** — an organizer who
opens the phase on a fresh tournament sees four empty queues and a fencer table
of dashes, with no control that would ever change that. Getting a payment into
Squire today means a `curl` with a bearer token.

The import that exists is also narrower than the problem. `bank.parse_fio_csv`
scans an upload for the literal header `ID pohybu` and raises otherwise, so it
reads Fio exports and nothing else. Squire's organizers do not all bank with
Fio, and a statement from any other bank is simply rejected. The fencer-table
import solved this same problem two changes ago by reading an arbitrary table
and letting an LLM shape it; a bank statement is the same kind of artefact and
wants the same treatment.

## What Changes

- **The statement import becomes bank-agnostic.** An uploaded CSV or XLSX from
  any bank is read into header-keyed rows by the existing
  `importer.read_table`, and an LLM shapes them into `IncomingTransaction`
  records — the same shape the Fio parser already produces, so everything
  downstream (ingest, matching, links, tolerance) is untouched.
- **The Fio format keeps its exact parser.** An upload carrying the `ID pohybu`
  header parses deterministically as it does today. A known format is never
  handed to a model to guess at, and the pilot's own bank costs nothing to
  import.
- **Statement parsing becomes a recorded operation.** A new
  `OperationKind.STATEMENT` joins `PARSE`, `MATCH` and `DEDUP`, batched with
  per-row cached decisions like the fencer import, so a long statement survives
  a dropped connection and resumes rather than restarting.
- **New intake card in the Payments rail** (`IntakePanel.tsx`): the statement
  upload, a *poll Fio now* action, and a *run lifecycle now* action. The rail is
  where a phase's operation parameters live, now that `add-payments-console-ui`
  moved the four resolution queues into the main column.
- **`POST /payments/fio-poll` gets its first caller**, offered only where the
  tournament has a `fio_token` and stating plainly why it is unavailable
  otherwise, rather than failing with `409 fio_token_not_configured` on click.
- **`POST /payments/process` gets its first caller** — expiries, reminders and
  holding-payment events run on the organizer's say-so, not only on the
  scheduler's.
- Czech and English strings for every new surface.

Not in scope: any change to matching, crediting, tolerance, expiry or refund
behaviour, and no change to the four resolution queues. This change is about
getting transactions in; what happens to them afterwards is already decided.

## Capabilities

### New Capabilities
- `payments-intake`: how bank transactions reach a tournament — the
  bank-agnostic statement import and its LLM parse, the Fio fast path, the
  console's intake controls, and the manual triggers for the Fio poll and the
  lifecycle passes.

### Modified Capabilities
- `payments`: "Bank transaction ingestion" currently names CSV import as the
  manual path without saying what a statement may look like; it gains the
  requirement that a statement from any bank is accepted, not only a Fio
  export.
- `console-operations`: the recorded-operation kinds gain statement parsing, so
  the one-operation-at-a-time rule, the progress counting and the
  interrupted-at-restart recovery all cover it.

## Impact

**Backend** (`backend/app/`): `bank.py` (a `StatementParser` protocol, an
`LLMStatementParser`, `get_statement_parser()` for injection, and the header
sniff that chooses between it and `parse_fio_csv`); `models.py`
(`OperationKind.STATEMENT`) with an Alembic migration; `operations.py` and
`routers/payments.py` (the import becomes a started operation rather than an
awaited request); `importer.read_table` is reused as-is, not copied.

**Frontend** (`frontend/src/`): new `payments/IntakePanel.tsx` in the Payments
rail; `api.ts` (`importStatement`, `fioPoll`, `processLifecycle`); `Console.tsx`
(the rail's payments branch); `i18n/{en,cs}.json`; the existing `useOperations`
and `OperationsIndicator` carry the new kind without change.

**Design constraints**: `CLAUDE.md` / `openspec/squire-design-spec.md` bind the
new card — no gradients, shadows, radii > 2px, emoji, spinners or hexes outside
`tokens.css`. Upload follows `ImportPanel.tsx`, which already runs a file
upload as an operation and is the closest existing kin.

**Cost**: an LLM call per batch of statement rows, on non-Fio imports only.
Cached per row fingerprint, so a re-upload of a corrected statement re-parses
only what changed.

**Verification**: `pytest` for the parser split, the operation and the cache;
`vitest` for the intake card and its disabled states; `npm run lint`,
`npm run build`; and driving the console with a non-Fio statement — which also
unblocks the seeded end-to-end check `add-payments-console-ui` left open.
