## Context

See `proposal.md` — Why. Four facts about the code as it stands shape everything
below.

**The decision the panel asks for cannot be examined.** `DedupPanel.tsx` prints
`item.rows.map(r => r.name).join(" + ")` and two buttons. The merged record —
which the backend has already computed and put in the queue payload as `fields`
— is never rendered. `api.dedupDecide` sends `{key, accept}` and nothing else,
though `DedupDecisionIn` has carried `fields: dict | None` and `note: str | None`
since the endpoint was written. The editable conclusion is therefore mostly a
matter of sending what the backend already accepts.

**Merged and settled are two different facts, and the code conflates them.**
`pending_queue` filters on the `dedup_resolution` decision alone. The merge
itself is a `dedup_decision` rule, and rules are deletable from the manual-edits
log. Delete one today and the merge is undone while the resolution record still
says the group was accepted: the group has un-merged and will never be offered
again. Basing "merged" on the live rule closes that hole and is what makes an
auto-merge withdrawable at all.

**The surely band is invisible by construction.** `run_dedup` merges it and
stores `dedup_resolution {accepted: True, auto: True}`; `pending_queue` reads
only the `merge` decisions and the `likely` band. Nothing anywhere lists a
surely group. Listing it is not a new computation — the band is already stored
in the `dedup` decision's payload.

**The rows the queue carries are the same rows the sheet carries.**
`_replayed_import_rows` is `sheet.base_rows` plus a replay, so a queue member
already has `number`, `email`, `hr_name`, `hr_nationality`, `hr_club` on it.
`_record_view` simply does not project them.

## Goals / Non-Goals

**Goals**

- The phase shows the work and only the work, and shows enough of it to decide.
- The conclusion is a record the organizer can read down a column against its
  members, and correct before accepting.
- Every candidate group has a verdict, states whose it is, and can be changed.
- No LLM call is added, re-made, or re-keyed. No stored shape changes.

**Non-Goals**

- No change to how duplicates are found: the prompts, the bands, the keying and
  the incrementality of `dedup_seen` are untouched. This change is about what
  happens to a candidate after the classifier has raised it.
- The possible band stays discarded (owner decision).
- No shared "ledger" component extracted from Matching. Matching's ledger line is
  a table row and this one is a table; nothing is common but the idiom, and the
  spec already carries the idiom.
- No filtering, sorting, or bulk action over groups. Two candidates is a busy
  day.
- No general Console refactor beyond the one seam this change needs.

## Decisions

### D1 — Deduplication becomes a view, not a filtered table

The alternative was to keep the fencer table and filter it to the candidate rows,
grouping visually. Rejected: a filtered fencer table cannot show the conclusion.
The conclusion is a record that exists nowhere in the sheet — it is what a merge
*would* produce — so it has no row to sit on, and the group's members must be
adjacent to it to be read against it. Once the conclusion needs a place, a table
per group is the shape, and the fencer table has nothing left to do on the
phase.

This is the point where the change earns its BREAKING label: `etl-console`'s
phase-table requirement says every processing tab after Fencers shows the same
fencer list. The delta scopes that to the phases that show a fencer table and
states why deduplication is not one — the work is a handful of rows out of fifty
and listing the fifty hides it.

*Consequence:* rows can no longer be deleted on Deduplication, so
`_removed_in == "dedup"` stops being producible. `listsRemovedRow` keeps working
for rows that already carry it — `dedup` is still in `PHASES` — and such a row is
listed and restorable on Fencers, Import and Matching as before.

### D2 — One endpoint returns every group, self-contained

`GET /import/dedup/queue` becomes `GET /import/dedup/groups` and returns all
three lanes with their verdicts. The frontend does not join against the sheet to
fill in a member row.

The join was considered — `Console` already holds `sheet.rows`, and reusing
`CellDisplay` would guarantee the member rows render exactly like the fencer
table's. Rejected on two counts. `SheetRow` has no `email`, which is a first-rank
dedup signal, so the join would need the sheet widened for a column only this
view shows. And a group's identity is not always the sheet's: a merged group's
absorbed members are `_deleted` and its survivor already carries the merged
values, so the sheet no longer holds the pre-merge records the settled line has
to display. The queue is computed from the same replayed rows either way; letting
it project what it needs is one function, `_record_view`, gaining five keys.

`_record_view` therefore adds `number`, `hr_name`, `hr_nationality`, `hr_club`
and keeps `id` and `registered_at`. The identity rendering rule from
`etl-console` is then applied in the frontend from those fields, as
`identityValue` already does for the table.

### D3 — Merged is a fact about the rule set; rejected is a fact about the record

A group's verdict:

| verdict | derived from |
|---|---|
| `merged` | an active `dedup_decision` rule whose group key is this group's |
| `separate` | a `dedup_resolution` decision with `accepted: False` |
| `pending` | neither |

The group key is reconstructed from the rule itself — `group_key([rule.target] +
rule.payload["absorb"])` — which is by construction the same key
`pending_queue` computes from the group's member ids. No new field on the rule
payload, no fallback path for rules written before this change, no migration.

*Alternative considered: store the key in the rule payload.* It is the more
explicit identifier, but it splits every lookup into "new rules by key, old
rules by absorbed set" for the life of the deployment, to save a hash that is
already deterministic.

The `dedup_resolution` record keeps one job it cannot delegate: it is what stops
`run_dedup` from auto-merging a surely group a second time after the organizer
withdrew it. That guard reads the resolution; the listing reads the rule. Each
answers the question it is actually about — "has anyone decided this?" versus "is
this merged right now?" — and the two stop being the same variable.

*Consequence:* undoing a merge from the manual-edits log returns the group to the
pending lane, which is the behaviour the spec now requires and is a bug fix
falling out of the model rather than a feature added on top.

### D4 — `decide` becomes total and idempotent

Today `decide` looks the key up in `pending_queue` and returns `not_pending` for
anything settled. It becomes a verdict over any candidate group:

- **accept** — update the standing `dedup_decision` rule's payload where one
  exists, create it where none does; store `dedup_resolution {accepted: True}`
  with `source="organizer"`.
- **reject** — delete the standing rule where one exists; store
  `dedup_resolution {accepted: False}`, `source="organizer"`.

Updating rather than replacing on re-confirmation matters: `rules.update_rule`
keeps the rule id, so the manual-edits log keeps one entry for the group and the
organizer's undo still reaches it. Two rules for one group could otherwise stand
at once, absorbing the same rows twice.

`fields` and `note` arrive from the client and are stored as given. Where they
are absent — a settled group flipped back to merged without opening the
conclusion — the recommendation stands in, as it does today.

### D5 — The conclusion is drafted locally and committed once

Editing a conclusion cell does not call the API. The whole conclusion is client
state until the organizer confirms, and confirming is the single request that
becomes the single rule. This is what makes "one action ratifies" true here:
correcting three cells and accepting must be one entry in the log, not four.

Escaping the group, or navigating away, discards the draft. Nothing warns about
it — a discarded draft costs the organizer the same clicks again, and the phase
that guards unsaved state (Setup) guards a form that took minutes to fill.

### D6 — What a conclusion cell offers

Each editable cell opens onto the distinct values its member records carry for
that field, one click each, plus a free-text entry seeded with the current value.
The choices are the point: a merge is nearly always a choice among what the
records already say, and typing is the exception the cell must still allow.

Field kinds:

- **text and number** (`name`, `nationality`, `club`, `email`, `notes`,
  `problems`) — choose a member's value or type one. Validated by the same
  `checkString` / `checkNumeric` calls the table's cells use, so a name cannot be
  emptied here when it cannot be emptied there.
- **lists** (`disciplines`, `weapon_rentals`) — the union of the members' values,
  each includable or excludable. A merge that drops a discipline one record
  claimed is a real decision and has to be expressible; typing a discipline the
  tournament does not offer is not, so free text is not offered here.
- **boolean** (`afterparty`) — a toggle, defaulting to the recommendation's
  value.
- **`hr_id`** — not editable (D7).
- **`registered_at`** — not a merge field; the conclusion states the survivor's,
  read-only, because the merge keeps the earliest by rule.
- **the note** — a text area beneath the conclusion row, not a cell.

The popover reuses the `suggestion-list` treatment already in `index.css`:
`--paper-raised` under a 1px `--ink` rule at the 2px radius, no shadow, no
animation. It is a different component from `SuggestionList` — that one is bound
to `useSuggestions` and its typeahead — but it must not look like a second idea.

### D7 — The identity register stays the profile's where a profile stands

`etl-console`'s HR-identity requirement makes the identity columns read-only on
every phase after Matching, and the conclusion row is the single exception the
delta carves out: where no profile is bound, choosing which registered spelling
survives is the merge's own decision and is taken nowhere else. Where a profile
*is* bound — which for the same-hr_id lane is every group by definition — the
identity cells state the profile's values, upright and read-only, and the
registered name the merge still records underneath is not shown. It is not
nothing: it is what the row falls back to if the binding is ever withdrawn. But
displaying a value that the phase's own identity rule then overrides would put
two names on one line and make the reader arbitrate between them.

`hr_id` is never editable in the conclusion. A merge does not bind a profile;
Matching does, and an id typed here would be a match verdict wearing a merge's
clothes.

### D8 — One seam in `Console.tsx`, no more

The workspace currently branches three ways (Setup, Teams, Queue each replacing
the whole `<>`, rail included) and otherwise renders a 130-line `<main
className="sheet-area">` inline. Deduplication is a fourth shape: it replaces the
main area and keeps the rail, since the run control and the phase's edits log
still belong there.

The fencer table's main area moves to `frontend/src/SheetArea.tsx` with the props
it already reads (`rows`, `visibleRows`, `columns`, `phase`, `timezone`,
`onEdit`, `onDelete`, `onRestore`, `onMatch`, `onRatify`, `refresh`). The
workspace then chooses `<SheetArea>` or `<DedupView>`. `Console.tsx` drops from
673 lines to roughly 520 — still over the convention's 300, but this change pays
for the seam it needs and does not open the rest.

`PHASE_COLUMNS.dedup` becomes `[]`, which is what Setup, Teams and Queue already
hold.

### D9 — Where the count is stated

Once, in the view's header, above the groups it counts. The rail card keeps the
run control, the busy notice and the operation's outcome, and loses the queue it
used to hold and count.

Matching states its count in the rail because its main area is the fencer table
and the queue is scattered through it. Here the view *is* the queue, and a rail
count beside it would be a second number that can only ever agree or be a bug.

### D10 — Frontend file layout

`frontend/src/dedup/`, per the convention that a panel composed of sections keeps
the orchestrator thin:

| file | what it is |
|---|---|
| `DedupView.tsx` | the main area: header and count, the groups, the empty state |
| `DedupGroup.tsx` | one bordered block: what raised it, the member table, the conclusion, the verdict and its actions |
| `ConclusionRow.tsx` | the conclusion's cells and its note, holding the draft |
| `ConclusionCell.tsx` | one cell: the value, the choices, the free-text entry |
| `mergeFields.ts` | the columns, each field's kind, the choices a field draws from its members |
| `DedupPanel.tsx` | moved here; the rail card, now the run control alone |

### D11 — A merge reports its absorption and nothing else

`_apply_dedup_decision` returned a change per merged field, plus one for the
merge note, plus one per absorbed row. One click on Merge therefore wrote five or
six lines into the manual-edits rail, and one of them was routinely
`Notes: — → —` — a field whose merge replaced one empty value with another, which
`before != value` counts as a change and the rail renders as two em dashes.

This is the same defect `ledger-matching-review` fixed for Matching in its D3a,
and it takes the same fix: apply the consequences without appending to the audit,
and report the decision. For a resolution the decision was the id it bound; for a
merge it is the absorption — which row went into which — which the absorbed row
already reported and which names both rows.

Nothing is lost. Undo still reaches the whole merge, since the surviving entry
carries the rule id and removing the rule reverses every consequence. And the
values the merge decided now have a better home than the log ever was: they are
the conclusion on the group, beside the records they came from, which is the
whole point of this change.

*Consequence:* a merge no longer contributes to a cell's net-change chain, so a
later manual edit of a merged cell reports the merged value as its `before`
rather than the source value. That is the correct reading — the merge is the
row's new baseline, not an organizer's edit of that cell — and it is how a
promoted canonical name already behaves.

## Risks / Trade-offs

**A duplicate the classifier never raised is now invisible on the phase** → The
organizer scanning fifty rows for a pair the machine missed does it on Fencers,
which lists all fifty, sorted by registration moment — the order in which a
double registration is most likely to stand out. The phase never offered a merge
action from the table anyway: spotting a duplicate there and acting on it was
already impossible, so nothing that worked has been taken away.

**Withdrawing an automatic merge leaves the resolution record saying
`accepted: True, auto: True`** → It is immediately overwritten by the
organizer's `{accepted: False}` with `source="organizer"`, which is the honest
record: the machine proposed, the organizer disagreed. The `auto` flag survives
nowhere, and nothing reads it.

**A group's identity changes when its membership does** → `group_key` is a hash
over the member ids, so a third duplicate joining a pair yields a new key and a
new group, while the old pair's rule and resolution still stand under the old
one. The pair reads as merged, the triple as pending, and confirming the triple
would absorb a row already absorbed. This is pre-existing and not made worse
here; it is called out because the settled lane now makes it visible where the
queue used to hide it. Left for a later change, which will want to key a group by
its surviving row rather than by its membership.

**Ten columns in a group table** → The blocks are the only content on the page
and each is as wide as the workspace, where the fencer table already carries ten
on Matching and scrolls. Notes render as the marker the table uses, not as prose.

**Two ways to undo a merge** → the group's own action and the manual-edits log
entry. They now agree, which is the fix; before this change only one of them
existed and it was broken. The log's undo is the general mechanism and stays.

## Migration Plan

None. Verdicts are derived from rules and decisions that already exist. No stored
payload changes shape, no decision is re-keyed, no LLM call is re-made, and no
backfill runs.

On first load after deploy, an existing tournament's Deduplication phase shows
its surely groups as merged-by-machine — merges that already happened and were
never displayed — and any likely or same-id group still awaiting a decision. A
tournament whose merge rule was undone from the log at some point will find that
group back in the pending lane, which is the correct state it was never able to
reach.

Rolling back restores the rail queue with every organizer decision intact:
resolutions and merge rules are what both versions read.

## Open Questions

None. The four that stood — whether the fencer table survives on the phase, what
becomes of the automatic merge, how much of the conclusion opens for editing, and
whether the possible band is surfaced — were settled by the owner before this
document was written and are recorded as D1, D3, D6 and the Non-Goals.
