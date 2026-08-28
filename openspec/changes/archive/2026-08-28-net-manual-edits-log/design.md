## Context

`rules.replay` returns the table state plus an `AppliedChange` per quadruple a
handler emits, and `/sheet` hands that list to the console's edits rail, which
renders it one line per change. See proposal.md — Why for what that costs the
organizer.

Two facts of the existing engine shape the approach:

- The audit is already ordered by rule id, and every handler reports honest
  `before`/`after` values for the field it touches. So the first `before` in a
  cell's chain **is** that cell's source-derived value, and the last `after` is
  its current value — the net difference is recoverable from the audit alone,
  without a second replay.
- `_apply_dedup_decision` marks an absorbed row `_deleted` without emitting a
  quadruple for it, emitting only `_merged_into`. A merge therefore already
  produces exactly one entry per absorbed row.

## Goals / Non-Goals

**Goals:**

- One projection, computed in one place, that both the API and any future
  consumer (an export footnote, a printed change list) can use.
- The rail keeps working entry-by-entry: an entry is still something you can
  point at and remove.

**Non-Goals:**

- Changing when rules are created, or collapsing rules at write time. A restore
  still writes a `row_restore` rule; the pair simply stops showing. The rule
  table grows as it always has, and cleaning it up is a separate question.
- Changing replay, rule ordering, or the journal.

## Decisions

### Net at read time, not cancellation at write time

`create_rule` could detect that a new rule inverts the newest active rule on the
same cell and soft-delete that rule instead of appending — real undo semantics,
keeping rail entries 1:1 with rules and the ✕ button single-rule.

Rejected as the primary mechanism: it only catches exact inverses, needs a
per-kind notion of "inverse", does nothing for rule sets already in the
database, and rewrites one organizer's rule under another's name. The read-time
net cancels by construction, including chains no pairwise rule could see, and
needs no migration. It stays available later as pure hygiene.

### Grouping key is (row, field)

Group the audit by `(target, field)` preserving order; an entry carries the
group's first `before`, its last `after`, the rule ids of every member, and the
actor, timestamp, and phase of the **last** member. Drop the group when
`first.before == last.after`.

The last member decides attribution and phase because it is the operation that
put the cell in the state now on screen — the one an organizer would ask about.
Grouping per row instead was considered and rejected: two unrelated corrections
to one fencer are two facts, and the ✕ must be able to undo one without the
other.

### `match_verdict` is folded into its `hr_id` entry

`match_resolution` emits both `hr_id` and `match_verdict`, which as two entries
say the same thing twice. Suppress the `match_verdict` group on a row that also
has an `hr_id` group; a `match_verdict` group standing alone (the value returned
to its source HR id but the verdict did not) still shows.

### Removal loops over the entry's rule ids

The entry carries `rule_ids`; the console issues one `DELETE /rules/{id}` per id
and refreshes once. No new endpoint: the existing delete already carries the
`payment_link` side effect, and a batch route would have to reproduce it. Sets
are small — a cell with more than a handful of rules is not a real case.

### Row identity is resolved in the console, not the API

The entry keeps `target` as the row id. The console already holds the row list
it numbers the table from, so it looks the row up there for the number and name.
Sending a label from the backend would duplicate the numbering rule and go stale
against the phase's own filtering. A `_merged_into` entry resolves its value the
same way, giving the surviving row's name.

### Field vocabulary lives in i18n, with a fallback

`column.<field>` already labels every field the table shows. The log can name
fields no phase columns cover (`email`, `reg_name`, `merge_note`) and
pseudo-fields that are not assignments at all (`_deleted`, `_merged_into`). Add
the missing labels under `column.*`, and give the pseudo-fields sentence forms
under a new `rail.edit.*` group rather than pretending they are columns. An
unknown field falls back to its raw name rather than rendering a missing key.

## Risks / Trade-offs

- **An organizer loses the ability to see, in the console, that a row was
  deleted and restored.** → That history is what the journal is for, and the
  rail's job is stated by the spec as the difference from source data. The
  journal endpoint already exists and is unchanged.
- **Attribution to the newest rule can name someone who did not originate the
  change.** → It names who put the cell in its current state, which is the
  question the rail answers. The journal has the rest.
- **The rail's ✕ becomes coarser: it removes several rules at once.** →
  Intended. Its title copy should say so ("undo this change", not "remove this
  rule").
- **Partial failure mid-loop leaves some of an entry's rules removed.** → The
  refresh shows the remaining ones as a smaller entry, and pressing ✕ again
  finishes the job. Idempotent enough at this scale.
- **`Console.tsx` is already long and gains rendering logic.** → The edits rail
  moves to its own file under the frontend conventions in CLAUDE.md.

## Migration Plan

None. No stored data changes; the projection is computed per request. Existing
rule sets simply start reading as their net effect.
