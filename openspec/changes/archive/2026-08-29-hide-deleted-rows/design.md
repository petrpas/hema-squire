## Context

See proposal.md — Why. Four facts of the implementation shape the approach:

- `_deleted` is a replay product, not a column: `rules._apply_row_delete` sets
  it on the row, `_apply_row_restore` clears it, and `_apply_dedup_decision`
  sets it on every absorbed row alongside `_merged_into`. The base projection
  (`sheet.base_rows`) always writes `_deleted: False`.
- Nothing in the replayed row says which rule removed it. The rule knows its
  phase (`Rule.phase`, set from the console tab the action was taken on), and
  `replay` holds the rule while it applies it — but the row it produces keeps
  only the boolean.
- `Console.rowsForPhase` already decides per phase what the table lists; today
  it filters only Import (`imp:` rows, file order) and hands every other phase
  the whole set. `activeRows` — the footer count and the paid count — already
  excludes deleted rows, as do `dedup`, `hr_match` and `sheets_export`.
- The manual-edits rail receives the full `rows`, not the phase's view, so its
  entries can name a row the current tab does not list. That already holds and
  must keep holding: an entry naming a hidden row is exactly the entry that
  undoes its removal.

## Goals / Non-Goals

**Goals**

- One place that decides whether a phase lists a row, on the client, over data
  the server already computes.
- A removal that can be located in the phase order without persisting anything
  new: no column, no table, no migration.
- No change to what is exported, counted, matched or deduplicated — those
  already ignore deleted rows and must keep ignoring exactly the same set.

**Non-Goals**

- A "show deleted rows" toggle. It would put the decision back on the organizer
  on every tab; the phase order already answers it.
- Making the removal visible in the row's own columns (a "removed on Payments"
  cell). The strike-through and the phase's own log say it where it matters.
- Hard deletion, or any change to what `/sheet` returns as its row set.

## Decisions

### The removing phase is a replay product carried on the row

`replay` sets `_removed_in` on a row when a rule it just applied removed it, and
clears it when a rule returned it. It is derived on every replay from the rule
set alone, so it needs no migration, cannot drift from `_deleted`, and vanishes
with the rule that caused it — the property the spec's determinism requirement
already demands of everything else on the row.

The assignment happens in `replay`'s loop rather than inside the handlers,
because the handler signature (`rows, target, payload`) does not carry the rule,
and widening it to pass a phase would touch all six handlers to serve two. The
loop already has both the rule and the handler's change quadruples: a row is
removed by this rule when the quadruples contain `(_deleted, → True)` or
`(_merged_into, → target)`, and returned when they contain `(_deleted, → False)`.

Alternatives rejected:

- **Reconstruct it on the client from the edits log.** `NetChange` already
  carries a phase and a target, and the console already receives the log. But
  the log is *net*: a merge reports `_merged_into` and never `_deleted`, and a
  delete–restore–delete chain reports one entry whose phase is the last rule's —
  close enough by accident, not by construction. Two rules deriving one fact
  from different data is how they come apart.
- **Persist a `removed_in_phase` column on the rule or the row.** A rule already
  has `phase`; a second copy of it would need keeping in step with rule
  withdrawal, which is precisely what replay does for free.
- **Store the removing rule's id and look its phase up on the client.** More
  plumbing for the same answer, and it invites the client to resolve rules.

### The console compares phase positions, and an unplaceable phase hides nothing

`rowsForPhase` drops a row when it is removed and `PHASES.indexOf(row._removed_in)`
is strictly less than `PHASES.indexOf(phase)`. That single comparison gives the
whole rule: the deleting phase lists the row (equal indices), the phases before
it list the row (greater index), the phases after do not. Import needs no
special case — it is the first table phase, so nothing was ever removed before
it, and its existing `imp:` filter and file ordering stand unchanged.

`indexOf` returning `-1` for an unknown phase would hide the row from every
phase, which is the wrong way to fail: a row nobody can see is a row nobody can
restore. An unplaceable phase therefore keeps the row listed everywhere, as
today. This covers a rule written by a retired phase name and a payments-phase
deletion on a tournament whose payments feature was later turned off.

### A merge removes the row from every table but Import

Absorbed rows are the one removal that does not follow the phase order. Applying
the order to them would list an absorbed row on Fencers and Matching — before
Deduplication — which the existing Import-view requirement already denies
("gone from the fencer list"), and which the current implementation gets wrong
by listing it struck through everywhere.

The distinction is not arbitrary: a deletion says *handled at this step*, and
the steps before it have not handled anything yet, so the row is still theirs to
show. A merge says *these two rows are one fencer*, which was as true on Fencers
as on Export. So `rowsForPhase` drops a row carrying `_merged_into` on every
phase but Import, before the phase-order comparison is reached.

### The restore button follows the listing, not the phase

The actions column keeps rendering restore for a listed removed row and delete
for a listed live one — no new condition. Because a row is listed only where its
removal is not yet in the past, the restore button lands only where the spec
says it should, and no phase offers to restore something it does not show.
Withdrawing the entry from that phase's edits rail keeps working as the second
route, unchanged.

## Risks / Trade-offs

- **A row deleted late is invisible on the phase an organizer looks at first.**
  Deleting on Payments and then hunting for the row on Fencers finds it there —
  Fencers is before Payments — so the surprising case is only the reverse, and
  the deletion is in the Payments log. → Accepted; the alternative is showing
  every deletion on every tab, which is the current complaint.
- **Two removal rules with different visibilities.** A deletion follows the
  phase order, a merge does not. → They are told apart by `_merged_into`, which
  the row already carries and the Import view already renders; and the merge
  rule is the one the specs already state.
- **The phase order is now load-bearing for data, not just navigation.**
  Reordering `PHASES` would change which rows a tab lists. → The order is fixed
  by spec and a mode may only remove phases from it, never reorder them; the
  filter reads the canonical `PHASES`, not the offered subset, so turning a
  feature off does not shift any comparison.
- **Footer counts and the table can now disagree less obviously.** The footer
  already counts live rows only; on a phase after a deletion the count and the
  listed rows finally agree, and on the deleting phase they differ by the struck
  rows as before. → No change in behaviour, only in how often it is noticed.

## Migration Plan

None. `_removed_in` is derived on every replay and no stored data changes.
Deploy is a backend and frontend release together; rollback is the revert, after
which every phase lists deleted rows again as it does today.
