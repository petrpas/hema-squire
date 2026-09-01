## Context

See proposal.md — Why. The constraints that shape the approach:

- **One worker, stated as an invariant.** `deploy/Dockerfile:35` runs uvicorn
  with `--workers 1`, and the line above it calls that an invariant rather than
  a tuning. Everything below leans on it: a background task in the app process
  is the whole executor, and no operation can outlive the process that ran it.
- **A background loop already exists.** `scheduler_loop` runs off the app
  lifespan and calls `asyncio.to_thread(run_tick)` around sync work over a
  fresh session. The runner here is the same idiom, started on demand rather
  than on a timer.
- **The LLM calls are sync.** `agent.run_sync` in `LLMImportParser.parse`,
  and the matcher and dedup LLM behind them. `import_api` already wraps the
  parse in `run_in_threadpool` for this reason; the runner keeps the pattern.
- **Parse decisions are content-keyed and already durable.** `store_decision`
  writes one row per `(tournament, kind, key)`, and `import_table` reuses any
  that exist. A rerun after an interruption is cheap by construction — the only
  thing missing today is that a run commits once at the end, so an interrupted
  run keeps nothing.
- **`ImportDecision` is the store for all three operations** — `parse`,
  `hr_match`, `merge`, `dedup` all live in it, keyed by row key. The operation
  record is not that store; it records the *run*, not its findings.
- **The design prohibitions in CLAUDE.md govern the indicator**: no spinner, no
  animated bar, no shimmer, no shadow, no second saturated colour, radius ≤ 2px,
  and departure by fade-out rather than by animated entrance.

## Goals / Non-Goals

**Goals:**

- One record and one polled endpoint serving all three operations and both
  consumers (the phase panel and the indicator), so the three panels stop being
  three near-copies of the same broken flow.
- Progress that is a fact in the database, readable by anyone, not a fact in one
  browser tab's memory.
- Interruption that costs only the unfinished remainder.
- A shape that concurrent parsing can be dropped into without touching the
  record, the endpoint, or the console.

**Non-Goals:**

- **Concurrent parsing.** Batches stay sequential. This change only removes the
  reasons it would be hard later: per-batch commits and an order-free progress
  counter. See D6.
- **A job queue, a broker, or a second process.** One worker makes them
  unnecessary; adding one would be the change that breaks the startup sweep.
- **Cancellation.** An operation runs to its end or dies with the process.
  Stopping one mid-flight is a separate change with its own questions about
  what a half-applied match means.
- **Operations outside the console.** The record is tournament-scoped; the
  picker and the profile page show nothing.
- **Retrying automatically.** An interrupted operation is reported, not
  restarted. The organizer presses the button again, and the decision cache
  makes that cheap.

## Decisions

### D1 — One `Operation` row per run, not a status column per operation

A table:

| column | meaning |
| --- | --- |
| `id` | the identity the start request returns |
| `tournament_id` | scope; the poll endpoint filters on it |
| `kind` | `parse` \| `match` \| `dedup` |
| `status` | `running` \| `done` \| `failed` \| `interrupted` |
| `total` | units of work, known at start |
| `done` | units completed |
| `started_at`, `finished_at` | `finished_at IS NULL` is the running predicate |
| `started_by` | the fencer id, as `ImportBatch.uploaded_by` already records |
| `outcome` | JSON: exactly what the endpoint used to return synchronously |

The alternative was a status column on `ImportBatch` and equivalents elsewhere.
Rejected: matching and dedup have no batch to hang a column on, which is how
three panels became three mechanisms in the first place. A row per run also
keeps a history — the closest existing precedent is `HRIndexRefresh`, a log of
attempts with a status and a detail JSON, and this is that idea made per
tournament and readable while it runs.

`outcome` holding the old synchronous response body is deliberate: the panels'
result lines keep rendering the same shape they render today, so the change to
each panel is where the shape comes from, not what it is.

### D2 — Start returns 202 and the identity; a conflict is 409

`POST /import`, `/import/match` and `/import/dedup` keep their paths and their
permission check, read what they need, create the row, hand the work to the
runner, and return `202 {"operation_id": n}`.

A start while an operation of any kind is running for that tournament is
refused with `409` naming the running kind. Any kind, not the same kind: the
three operations read and write the same decisions and the same replayed rows,
and two of them at once is a question this change does not want to answer. The
refusal is a real lock — `disabled={busy}` never covered a second tab or a
second organizer.

`POST /import` still reads the uploaded file inside the request. The file is
already in memory; the batch and its rows are written there too, so a browser
that abandons the response still leaves a complete `ImportBatch`. Only the
parsing moves to the background.

### D3 — The runner is a background task over a fresh session

Starting an operation schedules `asyncio.create_task` over a coroutine that
calls `asyncio.to_thread` around the sync body, exactly as `scheduler_loop`
does. The body opens its own `SessionLocal` — the request's session is closed
by the time it runs — and the session held for the whole run belongs to the
runner alone.

Rejected: `BackgroundTasks`. It runs after the response but is still tied to
the request's lifecycle and offers no handle, and the point of this change is a
handle that outlives the request.

The runner catches everything. An exception sets `status='failed'` with the
error's text in `outcome`, and is logged. An operation that raises must never
leave `finished_at NULL`, because that is the state the startup sweep exists to
clean up and nothing else should be producing it.

### D4 — Progress is committed per unit, by the unit that finished

The parse loop moves out of `LLMImportParser.parse` and into the caller.
`parse` becomes a single-batch call — `parse_batch(rows, disciplines, rentals)`
— and `importer` owns the loop:

```
for batch in batches(undecided, PARSE_BATCH_SIZE):
    records = parser.parse_batch(batch, offered, lent)
    for row, record in zip(batch, records, strict=True):
        store_decision(...)
    operation.done += len(batch)
    session.commit()          # decisions and progress in one transaction
```

Progress and the decisions it reports are committed together, so `done` can
never claim work that is not stored. `total` is the number of undecided rows,
not the file's row count: reused rows are not work, and a re-upload of an
unchanged file would otherwise report a long operation that does nothing.

Matching and dedup report per row against the replayed row list they already
build, on the same rule — the write and the count in one commit.

`ImportParser` is a Protocol with test fakes behind it; narrowing it to one
batch is a small change to those fakes and removes the batch-size knob from the
parser, where nothing but the loop was using it.

### D5 — Crash recovery is a startup sweep, not a heartbeat

At lifespan startup, beside `_populate_hr_index_if_empty()`:

```
UPDATE operations SET status='interrupted', finished_at=now()
WHERE finished_at IS NULL
```

Sound only because one process runs every operation: an unfinished row cannot
belong to a live run, because there is no other run. This gets a comment saying
so, since it is exactly the assumption that would rot silently if a second
worker were ever added — and the sweep would then be actively wrong, marking a
peer's live work dead.

A heartbeat column with a staleness threshold was the alternative. It buys
nothing here and would have to guess a threshold longer than the slowest
plausible LLM batch.

An interrupted import is not a failure to the organizer. Its committed batches
stand as decisions, and pressing the button again reuses them and parses only
the remainder — so the copy for `interrupted` says the work stopped partway and
that re-running finishes it, and does not read as an error. `failed` is the
state that reads as one.

### D6 — What "ready for concurrency" means, concretely

Three properties, all of which the above already has:

1. `done` is a counter incremented by the finishing unit, never an index into a
   sequence. Out-of-order completion stays correct.
2. Each unit's decisions commit independently, so no unit's result waits on
   another's, and a partial run is a valid state.
3. Nothing in the record, the endpoint, or the console reads batch order.

Making it concurrent later is then the loop in D4 becoming a bounded gather,
and nothing else. That is the whole of the readiness — deliberately, because
the executor is the part that explodes, and none of these three properties
requires touching it.

One thing to be careful of when that day comes, noted here so it is not
rediscovered: `store_decision` and the `done` increment share a session, and a
gather over threads would need a session per worker with the counter updated on
one. Not a problem now; a reason not to spread the session around meanwhile.

**Checked against the code as built** (task 7.3). All three hold:
`operations.advance` is the only writer of `done` and it adds rather than
assigns; every write site — `importer.parse_undecided`, `hr_match.run_matching`,
`dedup.run_dedup` — commits through the `progress` callback per unit and never
in bulk at the end; and the only ordering in the record is
`latest_concluded`'s `ORDER BY id DESC`, which picks *which run* to report and
says nothing about the order of units within one.

One honest limitation surfaced while building it: `matcher.match` asks the LLM
about every identity in a single call, so a matching operation's count goes
from zero to complete in one step. The total is still truthful and the
indicator still says matching is running, which is the complaint being fixed —
but matching's progress is coarse in a way an import's is not. Splitting that
call is the same change as making parsing concurrent, and belongs with it.

### D7 — One poll, two consumers

`GET /api/tournaments/{slug}/operations` returns the tournament's running
operation and the most recent concluded one per kind. A single
`useOperations(slug)` hook in `Console.tsx` polls it — every 2 seconds while
something is running, and not at all when nothing is. Panels and the indicator
both read the hook's result; neither polls.

The hook calls `refresh()` when a kind transitions out of `running`, which is
how the fencer list stops needing a manual refresh. The transition is detected
in the hook, once, rather than in three panels.

Rejected: SSE. It gives smoother progress and dies at exactly the moment being
fixed — a reload. Polling a record survives reloads, tabs and organizers, and 2
seconds against an operation measured in minutes is not a load problem.

Panels stop holding a `busy` state. Their button is disabled when the hook
reports something running, and their result line comes from the concluded
operation's `outcome`. The last outcome per kind persists across a remount, so
a returning organizer sees what happened rather than a blank panel.

### D8 — The indicator is a fixed card of text

Bottom right of the console, present on every phase, mounted by `Console.tsx`
outside the workspace so no phase owns it. `--paper-raised` on a 1px
`--hairline` frame, 2px radius, no shadow. An uppercase `--label-size` line for
the kind, a `--font-data` line for the count, `--ink-faded` for the start time.

It updates when the count updates and moves in no other way. That is a
stepwise text change, not an animated progress bar: nothing interpolates,
nothing loops, nothing runs while the numbers stand still. On conclusion it
holds its final line briefly and leaves by fade-out, which is what the design
spec prescribes for confirmations.

Rejected: putting it in the stepper on the phase that owns the operation. It
would be invisible from the other phases, which is the complaint.

## Risks / Trade-offs

- **The startup sweep is wrong under more than one worker.** → It is guarded by
  a stated invariant in `deploy/Dockerfile` and carries a comment naming the
  dependency at the point of the sweep. Adding a worker is then a change that
  has to confront it.
- **A poll every 2s per open console adds requests.** → Only while something
  runs, and the endpoint is one indexed query on `finished_at IS NULL` plus a
  small per-kind lookup. Compared to an operation making dozens of LLM calls,
  it does not register.
- **Refusing every kind while any runs is stricter than necessary.** → It is
  the conservative reading, and loosening it later is additive. Getting it
  wrong the other way means two operations rewriting the same decisions with no
  spec for what that means.
- **A long-running task in the app process delays shutdown.** → It already
  does, via `run_in_threadpool`. The difference is that the task is now
  recorded, so a shutdown that kills it produces an `interrupted` row the
  organizer can see, rather than silence.
- **Per-batch commits make partial state visible mid-run.** → Intended: it is
  what makes progress real. The fencer list already tolerates rows without
  parse decisions, since `llm_not_configured` produces exactly that today.
- **The operations table grows without bound.** → A row per run, a handful of
  runs per tournament, on a database whose fencer count is in the hundreds. If
  it ever matters, keeping the newest few per kind is a later, separate
  decision.

## Migration Plan

One Alembic revision creating `operations`. No backfill: there is no history of
runs to reconstruct, and no row means no operation ever ran, which is the
correct reading for every existing tournament.

Deploying is the ordinary path — migrations run before the server in the same
`CMD`. A console loaded from the previous build polls an endpoint that now
exists and gets an empty list, which renders nothing; a console from the new
build against the old backend gets a 404 and renders nothing. Neither breaks,
and neither combination lasts past a reload.

Rollback is the revision down. The endpoints revert to performing their work
synchronously, which is the behaviour being replaced — the decisions written by
per-batch commits before the rollback are valid decisions and are reused.

## Open Questions

- **How many concluded operations to keep per kind.** The console shows one.
  Whether the endpoint returns more, and whether old rows are ever pruned, can
  be decided once there is a reason to look at a history.
- **Whether `total` for matching should count rows or LLM calls.** Rows are
  what the organizer understands and what the copy will say; if the matcher
  turns out to batch internally, the count stays truthful either way because it
  is incremented by whatever finished.
