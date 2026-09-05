## Context

Three payments endpoints exist and nothing calls them:

| Endpoint | What it does | Frontend caller |
| --- | --- | --- |
| `POST /payments/import-statement` | parse a Fio CSV, ingest, match, apply links | **none** |
| `POST /payments/fio-poll` | pull `days_back` days from Fio's API | **none** |
| `POST /payments/process` | expiries, reminders, holding-payment events | **none** |

`bank.parse_fio_csv` (`bank.py:174`) locates the header by scanning for the
literal string `ID pohybu` and raises `ValueError` when it is absent, then maps
Fio's Czech column names through a fixed table. Any other bank's export is
rejected before a single row is read.

The machinery to do better is already in the repository, built for the fencer
table. `importer.read_table` (`importer.py:54`) reads CSV or XLSX into
header-keyed dicts and knows nothing about what the columns mean.
`importer.ImportParser` is a one-method Protocol with an LLM implementation and
a `get_import_parser()` factory that returns `None` when no key is configured —
which is what lets every test inject a fake. `ImportDecision` is a generic
`(tournament, kind, key, payload, source)` row, and `row_fingerprint` is a hash
of the raw row, so a re-upload re-parses only what actually changed.

Operations are equally ready: `operations.start` refuses a second concurrent run
per tournament, `advance` commits results and progress in one transaction, and
a startup sweep marks anything the process did not survive as `INTERRUPTED`.
`OperationKind` is a three-value enum stored as a string.

Constraints: `CLAUDE.md` / `openspec/squire-design-spec.md` ("Bureau 1952") bind
the new card. The one-operation-at-a-time rule means a statement parse and a
table parse cannot overlap, and the intake card must say so rather than fail.

## Goals / Non-Goals

**Goals:**
- A statement from any bank can be imported, without the organizer reshaping it.
- The Fio format keeps an exact, free, offline parse.
- A long statement survives a dropped connection.
- Every payments endpoint that exists is reachable from the console.
- Re-uploading a corrected statement costs only the rows that changed.

**Non-Goals:**
- No change to matching, crediting, tolerance, expiry or refund behaviour.
- No change to the four resolution queues `add-payments-console-ui` built.
- No new storage: statement decisions reuse `ImportDecision`.
- No bank integrations beyond Fio. Other banks are supported by reading their
  exports, not by talking to them.

## Decisions

### Decision 1 — Sniff the format, then choose the parser

`bank.parse_statement(filename, data)` decides:

```
"ID pohybu" in the file?  ──yes──▶  parse_fio_csv()      exact, offline, free
                          ──no───▶  read_table() ──▶ LLM ──▶ IncomingTransaction[]
```

A format with a published, stable column layout is not a guessing problem, and
the pilot tournament banks with Fio, so the common path costs no tokens and
cannot be wrong. The sniff is the same `"ID pohybu" in line` test the existing
parser already performs to find its header, so the two never disagree about
what a Fio file is.

*Alternative considered*: one path for every bank, deleting `parse_fio_csv`.
Simpler to reason about and to test — one code path, not two. Rejected on the
owner's call: it spends a model call and accepts a non-zero error rate on the
one format we can already read exactly.

*Consequence*: two parsers to keep producing the same `IncomingTransaction`
shape. Contained by making that shape the seam — both return the same pydantic
model, and everything downstream of `parse_statement` is untouched.

### Decision 2 — The LLM statement parser mirrors `LLMImportParser` exactly

A `StatementParser` Protocol with one method, an `LLMStatementParser` over
pydantic-ai, and a `get_statement_parser()` returning `None` when
`llm_configured()` is false. Same shape, same injection point, same testing
story: `app.dependency_overrides` puts a fake in, as `get_import_parser` already
allows.

The prompt's job is narrower than the fencer parser's. It maps a row to
`external_id`, `date`, `amount_cents`, `currency`, `vs`, `message`,
`payer_name`, `payer_account` — no taxonomy to match against, no offered list to
respect. Two rules carry the weight: amounts arrive as text in local
conventions (`1 200,00`, `-1200.00`, a separate debit/credit column) and must
become signed integer cents; and a row that is not a credit to the tournament's
account is dropped rather than invented into a transaction.

*Where it deliberately differs*: `external_id`. Fio supplies a stable movement
id; other banks may supply nothing usable. Where the model finds no id, the
row's `row_fingerprint` becomes the `external_id`, which keeps ingestion
idempotent — the existing dedupe is on `external_id`, so a re-upload of an
unchanged row collides with itself and is counted duplicate, exactly as
required by the payments spec's "Overlapping statement re-import".

### Decision 3 — Statement parsing is a recorded operation

`OperationKind.STATEMENT` joins the enum, and the import endpoint starts an
operation instead of parsing inline. Batched like the fencer parse, each batch's
decisions committed with its progress through `operations.advance`.

This buys three things the console already knows how to show: progress in units
of work, recovery of an interrupted run at startup, and the refusal of a second
concurrent operation. `useOperations` and `OperationsIndicator` need no change —
they are written against the enum, not against a list of kinds.

*Consequence*: the endpoint's response changes from `IngestAndMatchOut` (counts)
to a started-operation handle, and the counts move to the operation's `outcome`.
This is the same move `ImportPanel` already lives with for the table import, and
the intake card reads the conclusion the same way.

*Consequence*: a statement import and a table parse cannot run at once. Correct
rather than unfortunate — both write rows the other reads — and the card states
which operation is under way rather than failing on click.

*Note*: the Fio fast path is fast enough to parse inline, but still runs as an
operation. One shape for one action; a control that sometimes returns instantly
and sometimes starts background work is harder to describe than one that always
does the latter.

### Decision 4 — Statement rows reuse `ImportDecision`

`kind="statement_row"`, `key=row_fingerprint(raw)`, `payload` the parsed
transaction. No new table, no migration beyond the enum value, and
incrementality comes free: a corrected statement re-parses only rows whose raw
content changed, which is the behaviour the table import's spec already
requires and organizers already expect.

### Decision 5 — One intake card, three actions, each stating why it cannot run

`payments/IntakePanel.tsx` in the rail beside `TolerancePanel`:

- **Import statement** — file input, any CSV or XLSX.
- **Poll Fio now** — offered only where `fio_token` is set; where it is not, the
  action is absent and a line says the tournament has no Fio token configured.
  Better than a live button that answers `409 fio_token_not_configured`.
- **Run lifecycle now** — expiries, reminders, holding-payment events.

Each states its unavailability rather than failing on click: no LLM key
configured disables the non-Fio import path, another operation running disables
all three.

*Alternative considered*: three separate rail cards, one per action. Rejected:
they are one concern — getting the tournament's money into the console — and the
rail already carries `TolerancePanel` and `ManualEditsRail` beside them.

### Decision 6 — `process` is a button, not a schedule change

The scheduler keeps running the lifecycle passes on its own. The action only
lets an organizer stop waiting for the next sweep, which is what makes a
just-imported statement's expiries and reminders visible immediately. Nothing
about when the scheduler runs changes.

## Risks / Trade-offs

- **A model mis-parses an amount, and money is credited wrongly** → The largest
  risk in the change. Mitigated by keeping the Fio path exact (Decision 1), by
  cents being an integer field a malformed value cannot silently round, and by
  every parsed transaction still passing through the existing matching and
  tolerance rules rather than being credited on the parser's say-so. A wrong
  amount surfaces in the flagged queue, which is exactly what that queue is for.
- **A statement carries rows that are not payments at all** (fees, outgoing
  transfers) → The prompt drops non-credits, and a dropped row is invisible.
  Accepted for now: the alternative, ingesting them as transactions, puts noise
  into the unmatched queue where an organizer must judge each one. Worth
  revisiting if it bites.
- **`external_id` from a fingerprint is not stable across a bank's own edits** →
  A bank that restates a row (a corrected payer name) yields a new fingerprint
  and so a second transaction. Rare, and visible: both land in the unmatched
  queue rather than being credited twice, since only one can match a VS.
- **Changing the import endpoint's response shape** → No external caller exists
  to break; `seed_demo.py` reads the counts and is updated with the change.
- **An LLM call per non-Fio batch costs money** → Cached per row fingerprint, so
  the cost is once per genuinely new row, and zero for Fio.
- **The enum gains a value** → A string-stored enum, so the migration is a data
  constraint at most; existing rows are untouched.
