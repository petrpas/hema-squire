## Why

Every other processing phase does something to every row: Import parses them
all, Matching binds them all, Payments settles them all. The fencer table is the
right shape for those, because every line of it is work. Deduplication is not
like them. It concerns a handful of rows and typically none, yet it presents the
same full table — fifty lines of which none is a duplicate — with the actual
work hidden in a rail card the width of a sidebar.

The rail card is also the wrong instrument for the decision it asks for. It
states the candidate names joined by a plus and offers Merge or Keep separate. It
does not show what merging would produce, so the organizer is asked to approve a
merged record they cannot see — and it cannot be corrected, though the backend
has accepted an edited merge since the day it was written. Meanwhile the surely
band merges rows with no human involved and leaves no trace anywhere in the
view: the one dedup outcome that actually changed the fencer list is the one
outcome the phase does not show.

## What Changes

- **BREAKING (internal): the Deduplication phase stops showing the fencer
  table.** It joins Setup, Teams and Queue as a phase with a view of its own: a
  stack of small tables, one per candidate group. The full list stays one click
  away on Fencers, where it was never anything but a list.
- **A candidate group is one ledger line, rendered as a table.** Its member rows
  are the claim and the evidence — what each record says, and the HR profile
  behind it where there is one. Beneath them, under a rule, sits the conclusion:
  the merged record the system recommends, in the same columns, so the organizer
  reads down a column to see what merging would keep and what it would drop.
- **The conclusion is editable, cell by cell.** Each cell offers the members'
  own values as one-click choices and accepts a typed value; list fields
  (disciplines, weapon rentals) toggle over the union; the merge note is
  editable prose. Confirming sends the conclusion as edited. The
  `/dedup/decide` endpoint has taken `fields` and `note` since it was written
  and no caller has ever sent them.
- **Identity that belongs to a profile stays read-only.** Where the group's
  records are bound to an HR profile, the name, nationality and club cells of
  the conclusion state the profile's values and do not open — identity after
  matching is changed by rebinding the id, not here. Where no profile stands
  behind them, the registered values are the merge's to decide and open for
  editing.
- **Auto-merged groups become visible and reversible.** The surely band still
  merges on the run — that decision stands — but its groups are listed in the
  view as settled, stating that the machine decided them, with the opposite
  verdict one action away.
- **Every group carries a verdict, and a verdict can be changed.** Pending,
  merged, kept separate: the three are listed together, the pending ones first
  and counted. A settled group offers one action to flip it and one to reopen its
  conclusion for editing. Undoing a merge in the manual-edits log returns the
  group to the pending lane rather than leaving it settled-but-unmerged, because
  a group is merged when its merge rule is live and not when a decision record
  says so.
- **BREAKING (internal): `GET /import/dedup/queue` becomes
  `GET /import/dedup/groups`** and returns every candidate group with its
  verdict, its members, the recommendation, and — where merged — the conclusion
  actually confirmed. `POST /import/dedup/decide` becomes total over all groups
  rather than over pending ones alone, so a settled group can be re-decided.
- **The possible band stays discarded.** It exists to keep false positives off
  the screen and this change does not second-guess it.
- Console gains a seam it has needed for a while: the fencer table's main area
  moves out of `Console.tsx` into a component of its own, so the workspace can
  choose between it and the deduplication view without the file growing again.

## Capabilities

### New Capabilities

None. The deduplication review is a requirement over the existing console and
import capabilities, not a capability of its own.

### Modified Capabilities

- `etl-console`: Deduplication replaces the fencer table with a candidate-group
  view; a new requirement fixes what that view presents, how a conclusion is
  edited and confirmed, and how a settled group is re-decided; the phase-table,
  per-row-status, HR-identity and row-deletion requirements are restated to
  exempt the phase that no longer lists rows; the ledger idiom admits a machine
  verdict where a spec grants one, and requires it to be stated and reversible.
- `table-import`: the same-hr_id merge proposal is editable before it is
  confirmed; the surely band's automatic merge is required to be visible in the
  console and withdrawable in one action.

## Impact

- `backend/app/dedup.py` — `pending_queue` becomes `candidate_groups`, listing
  all three lanes with a verdict derived from the live rule set rather than from
  the resolution record alone; `decide` becomes total and idempotent, replacing
  or removing the merge rule; `_record_view` carries the fixed number and the HR
  evidence fields.
- `backend/app/routers/import_api.py` — `/dedup/queue` → `/dedup/groups`;
  `/dedup/decide` accepts a verdict for any group.
- `frontend/src/Console.tsx` — `PHASE_COLUMNS.dedup` empties; the workspace
  branches to the deduplication view while keeping the rail.
- `frontend/src/SheetArea.tsx` (new) — the extracted fencer-table main area.
- `frontend/src/dedup/` (new) — the view, the group block, the conclusion row and
  its cells, the field helpers; `DedupPanel.tsx` moves here and loses the queue
  it used to hold.
- `frontend/src/api.ts` — `DedupItem` becomes `DedupGroup`; `dedupQueue` becomes
  `dedupGroups`; `dedupDecide` gains fields and note.
- `frontend/src/i18n/{cs,en}.json` — the view's headings, verdict labels, the
  conclusion's affordances, the empty state.
- `frontend/src/index.css` — the group block and the conclusion row; no new
  tokens.
- No migration. Verdicts are derived from rules and decisions that already
  exist; nothing stored changes shape and no LLM call is re-made.
