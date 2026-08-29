## Context

See proposal.md — Why. What matters for the approach:

- The sheet is phase-independent. `api.sheet()` returns every row with both
  registers on it: `name` / `nationality` / `club` and `hr_name` /
  `hr_nationality` / `hr_club`. A phase differs only in the columns it draws
  (`Console.tsx`, `BASE_COLUMNS` + `PHASE_COLUMNS`). Nothing has to be fetched
  or computed server-side for this change.
- `hr_nationality` is already reduced to a two-letter ISO code by the backend
  (`rules.py`, `hr_index.py`), so the "one vocabulary" scenario is satisfied by
  reading that field rather than by new normalization.
- The canonical **name** is already promoted onto `row.name` when a match
  resolution binds an id (`rules.py`, `_apply_match_resolution`; spec
  `hr-integration`, Canonical naming), with the registered form kept in
  `reg_name`. So for a bound row the name column already reads the profile's
  name today. Nationality and club are the two values that actually change.
- `EDITABLE_COLUMNS` in `Console.tsx` is a flat set of field names, applied
  identically on every phase. Editability has never been phase-dependent.

## Goals / Non-Goals

**Goals:**

- One resolution rule for the three identity columns, readable in one place and
  testable without rendering the console.
- The italic marking carries no new color, no badge, no extra column — the
  design prohibitions in CLAUDE.md leave italic as the available register.
- No backend change, no migration, no new row field.

**Non-Goals:**

- Changing what `hr_id` cells do. The id stays editable wherever its column is
  drawn, and a typed id stays a verdict (spec `etl-console`, A typed id is a
  verdict).
- Promoting nationality and club onto `row.nationality` / `row.club` the way the
  name is promoted (see Decision 1).
- Revisiting name promotion or `reg_name`.
- Splitting `Console.tsx`, beyond keeping the new logic out of it.

## Decisions

### Decision 1: Resolve at display time, not by promoting onto the row

The identity columns read the HR register when `hr_id` is bound and the
registered register otherwise, at render time. The row's stored `nationality`
and `club` are untouched.

*Alternative — extend `_apply_match_resolution` to promote nationality and club
onto the row, as it already does for the name.* Rejected: the claim would then
be overwritten by the evidence, and Matching's claim-beside-evidence comparison
(spec `etl-console`, HR matching review) would compare a value against itself.
The name already has this wrinkle and pays for it with `reg_name`; there is no
reason to buy two more copies of it. Promotion is also a rule-replay concern —
it would want the profile in the payload of every historical resolution — where
display resolution is a pure function of a row already in hand.

### Decision 2: A separate module, `frontend/src/identity.ts`

The resolution and the phase predicate live in a new small module, not in
`Console.tsx` (645 lines already, against the ~300-line seam in CLAUDE.md):

```ts
/** The phases that identify a row by its HR profile. Matching is not among
 *  them: it shows claim beside evidence. */
export function usesHRIdentity(phase: Phase): boolean;

export const IDENTITY_COLUMNS = ["name", "nationality", "club"];

/** What an identity cell states, and whether the profile stands behind it. */
export function identityValue(
  row: SheetRow,
  column: string,
  hrIdentity: boolean,
): { text: string; declared: boolean };
```

`usesHRIdentity` is defined as membership in an explicit set —
`dedup`, `payments`, `export` — rather than as a position past `matching` in
`PHASES`. The order array also carries `teams` and `queue`, which draw no fencer
table at all, and an index comparison would quietly answer for them.

`declared` is true when `hr_id` is null, whatever the column: a row's identity is
one thing, so the three cells are marked together. A bound row whose profile
carries no club states an em dash upright, not an italic fallback to the
registered club — the profile is the authority, and its silence is an answer.

### Decision 3: `CellDisplay` takes an `hrIdentity` flag, not a `phase`

`CellDisplay` already receives `row`, `column` and `timezone` and is called by
two test files with that signature. It gains one optional boolean
(`hrIdentity`, default false) rather than a `phase`, keeping it a function of
what to draw rather than of where the console is. The existing tests keep
passing unchanged, and the new cases pass the flag explicitly.

Non-identity columns are untouched by the flag; the switch gains one branch for
the three identity columns ahead of its default.

### Decision 4: Editability becomes a function of column *and* phase

`EDITABLE_COLUMNS` stays, and a predicate wraps it:

```ts
function editableHere(column: string, phase: Phase): boolean {
  if (IDENTITY_COLUMNS.includes(column)) return !usesHRIdentity(phase);
  return EDITABLE_COLUMNS.has(column);
}
```

An italic cell is read-only on those phases too, though its value is the
organizer's to correct elsewhere. Making only the italic ones editable would put
an edit affordance on exactly the rows that are hardest to identify, and the
resulting field-edit rule would silently stop being displayed the moment the row
was matched.

### Decision 5: The italic register

One class, `identity-declared`, setting `font-style: italic` and nothing else —
no color, no weight, no icon. `--ink-faded` is not used: a registered value is
not a lesser value, it is a value with a different source, and fading it would
make unmatched rows harder to read at exactly the point where the organizer is
resolving them. No hex enters `index.css`.

## Risks / Trade-offs

- **A reader may take italic for "provisional" rather than "not HR-backed".** →
  The Matching phase, immediately before, shows both registers explicitly, so
  the reader arrives at Deduplication having just seen which rows have a
  profile. The column headers are unchanged and continue to read Name / Nat. /
  Club.
- **Losing the registered nationality and club from the later phases.** → They
  remain on the fencer list, on Import, and on Matching, which is where a
  discrepancy is meant to be resolved. If organizers turn out to need them on
  Export, the export payload is a separate concern and unaffected by this
  change.
- **Read-only identity cells remove a shortcut some organizer may be using.** →
  Deliberate, per the proposal; the correction still exists two tabs away and
  the change is trivially revertible (Decision 4 is one predicate).
- **`name` already reads canonically on the earlier phases** because of
  promotion, so a bound row's name cell will look identical before and after
  this change while its nationality and club move. → Expected, and the reason
  the three cells share one `declared` verdict rather than each deciding for
  itself.
