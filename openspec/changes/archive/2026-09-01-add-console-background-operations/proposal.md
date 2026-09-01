## Why

The three console operations that call an LLM — parsing an imported table,
matching against HEMA Ratings, deduplicating — each run inside the HTTP request
that started them. Nothing anywhere else knows they are running.

On a small table this is invisible. On a large one it is a broken screen. The
button greys out, and that greyness is a React state variable in one component:
reload the page, or step to another phase and back, and the console says nothing
is happening. The work is not lost — the browser abandons the response, but the
server thread runs on and commits — so the organizer is looking at a console
that has finished importing and does not know it, and will keep looking at it
until they press Refresh. There is no way to ask how far along it is, because
nothing records how far along it is: the import commits once, at the end, and
`GET /import/status` reports the last *finished* batch.

An organizer waiting several minutes on an operation they cannot see, on a page
that reports nothing is running, has no way to tell a slow import from a dead
one.

## What Changes

- **An operation becomes a record rather than a request.** Starting one writes a
  row naming the tournament, the kind of work, its total, how much of it is
  done, and who started it. The request returns at once with that row's
  identity; the work proceeds in the background. The console asks the row how
  things stand, so the answer is the same on any page, in any tab, after any
  reload, and for any organizer of that tournament.
- **All three operations work this way** — import parsing, matching,
  deduplication. One mechanism, one endpoint to poll, one shape of answer.
- **Progress is counted, not animated.** An operation states its total up front
  and its completed units as they land: *parsed 60 of 220 rows*. The console
  shows that as text, honouring the design spec's refusal of spinners and
  animated progress bars.
- **A standing indicator, bottom right of the console**, present on every phase,
  naming what is running and how far it has come, and leaving by fade-out when
  the work lands. Wandering off the phase that started an operation no longer
  hides it.
- **Results arrive without a refresh.** When an operation finishes, the console
  reloads the fencer list on its own. The manual Refresh button stays, but
  stops being the only way to see what happened.
- **A second start is refused while one is running.** The record makes this a
  real lock rather than a disabled button — two tabs and two organizers are
  covered, which `disabled={busy}` never was.
- **A crash resolves itself at startup.** The server runs one worker, so no
  operation can outlive the process that ran it; startup marks every unfinished
  row interrupted. An interrupted import keeps the batches it had already
  parsed, and re-running reuses them through the existing decision cache, so
  recovery costs only the unparsed remainder.
- **Parsing commits per batch instead of once at the end.** This is what makes
  progress observable and interruption survivable. It is also the shape
  concurrent parsing would need, which this change prepares for and does not
  attempt: progress is counted in completed units rather than tracked as a
  position in a sequence, and no part of the mechanism assumes units finish in
  order.

## Capabilities

### New Capabilities

- `console-operations`: long-running console work as an observable record — how
  an operation is started, refused, reported on while it runs, concluded, and
  recovered from after a crash; and the standing indicator that shows it.

### Modified Capabilities

- `table-import`: import, matching and deduplication are started rather than
  performed by their requests, and parse decisions are durable per batch rather
  than only on completion — which changes what survives an interrupted import.
- `etl-console`: where the indicator lives, that a phase panel reports the
  operation of its own phase, and that the fencer list refreshes itself when an
  operation lands.

## Impact

- **Backend**: an `Operation` model and its migration; a new `operations.py`
  holding the record's lifecycle and the background runner; `import_api.py`
  (three endpoints return 202 and a fourth reports the tournament's
  operations); `importer.py` (the batch loop moves out of `LLMImportParser`
  into the caller so each batch commits and reports); `hr_match.py` and
  `dedup.py` (progress reporting); `main.py` (the startup sweep, beside the
  existing lifespan checks).
- **Frontend**: a `useOperations(slug)` hook; a new `OperationsIndicator.tsx`;
  `ImportPanel.tsx`, `MatchPanel.tsx` and `DedupPanel.tsx` (their button state
  and their report come from the hook, not from local `busy` flags);
  `Console.tsx` (mounting the indicator, refreshing on completion); `api.ts`;
  `index.css`; `i18n/{cs,en}.json`.
- **Not touched**: the parser's prompt and output shape, the decision cache's
  keying, the rule engine, replay, the fencer list's contents, and every
  operation's actual result — this changes when and how the console learns of
  the work, not what the work does.
- **Rests on** `--workers 1` in `deploy/Dockerfile`, already an invariant there.
  The startup sweep is only sound while it holds.
