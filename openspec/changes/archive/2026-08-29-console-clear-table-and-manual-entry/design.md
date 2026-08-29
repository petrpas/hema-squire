## Context

See proposal.md — Why. The constraints that shape the approach:

- The fencer table is a **projection**, not a table: `sheet.base_rows` builds
  rows from source records and `rules.replay` applies the organizer's rules on
  top. Adding a population means adding a source, not a column.
- A row id is the join key for everything: `SheetRowNumber.row_id`, `Rule.target`,
  merge payloads, and the export document all reference `"reg:<id>"` and
  `"imp:<fingerprint>"`. Anything new needs a prefix of its own.
- Numbers are allocated **where a row is born** (`rownumbers.allocate`, called
  from `register()` and from `importer.import_table`), never while the sheet is
  read, so `GET /sheet` stays a read.
- `RuleJournalEntry.rule_id` is a foreign key to `rules.id`, so a hard delete of
  rules cannot leave their journal entries standing.
- The design prohibitions in CLAUDE.md govern both new UI surfaces: no shimmer,
  no toast animation, no second saturated color, static confirmations.

## Goals / Non-Goals

**Goals:**

- One deletion path that leaves the database in a state indistinguishable from
  "this tournament never imported", with no dangling decision, rule, journal
  entry, or number.
- A third source population that costs `sheet.py` one more `rows.update(...)`
  call and costs the phases downstream nothing at all.
- Validation of a manual entry stated once, on the server, with the client
  reflecting it rather than reimplementing it.

**Non-Goals:**

- Billing a manually entered fencer. They get no VS and no payment instruction,
  exactly as an imported row does not. Making either population billable is a
  separate change.
- A per-batch clear, an undo, or a trash. See specs — clearing is total and
  final.
- Editing a manual row through the dialog. Once entered, a row is corrected in
  the table like any other, through `field_edit` rules.

## Decisions

### D1 — A manual row is a source record, not a registration

A manual entry writes a `ManualRow` row and nothing else. The alternative — an
organizer-created `Fencer` plus `Registration` — was considered and rejected:
`Fencer.email` is required and unique, so a fencer entered at the door without
an e-mail would need a synthetic address; `register()` allocates a VS, prices
the selection, places against capacity, and sends confirmation mail, all of
which would need suppressing; and a passwordless account would appear in the
global fencer population as a side effect of a table edit.

The cost is that a manual row is not billable and does not show in Payments.
That is the limit imported rows already live under, so the console gains no new
kind of gap — see Risks.

`ManualRow` carries scalars as columns (`name`, `nationality`, `club`, `hr_id`,
`email`, `registered_at`, `notes`) and the two chosen sets as JSON
(`disciplines` as slugs, `weapon_rentals` as item names), plus `afterparty` as a
boolean, `created_by` and `created_at`. Slugs and names rather than foreign keys,
deliberately: the imported population already stores its selections that way,
and `sheet.py` resolves both by the same lookup. Row id is `"man:<id>"`.

### D2 — The projection gains one more source, and nothing else changes

`base_rows` calls a new `_manual_rows(session, tournament)` and `rows.update`s
it beside `_imported_rows`. The dict it returns has the same keys as an imported
row's, with `state: "manual"`, `problems: None`, no `_source`, and
`match_verdict` of `"confirmed"` when an hr_id was given and `"unknown"`
otherwise — the same rule `_imported_rows` uses for a fencer-provided id.

Because ordering, numbering, marker columns, rules, replay, matching, dedup and
export all read the projection rather than the sources, they need no change
beyond the two places that enumerate populations explicitly:
`rownumbers.arrival_order` and `export_json`.

`rowsForPhase` in `Console.tsx` already filters Import to ids starting `imp:`,
so manual rows stay off the Import view with no new condition.

### D3 — Clearing is a single server-side transaction, ordered by dependency

`DELETE /api/tournaments/{slug}/import` in `import_api.py`, in one transaction:

1. Collect the tournament's imported row ids (`"imp:<key>"` for every
   `ImportedRow` of every batch, not only the latest).
2. Delete `RuleJournalEntry` rows whose `rule_id` is in the set of rules to go.
3. Delete `Rule` rows — hard, not the soft `deleted_at` the console's undo uses —
   that name an imported row as `target`, or name one anywhere in `payload`.
4. Prune `ImportDecision` rows: keep only what is **provably about surviving
   rows**, delete the rest. Reachability from the cleared ids was the first
   plan and does not work — `dedup_resolution` is keyed by an unreversible hash
   of its group's ids and carries none of them in its payload. So the rule is
   stated per kind instead: `hr_match` survives when its identity key is that
   of a surviving row; `dedup_seen` when its key is a surviving row id; `merge`
   when every id in its payload survives; `dedup_resolution` when its group key
   is one still reconstructible from the surviving `dedup_decision` rules, which
   are where a merge's membership is also recorded. `parse` belongs to an
   imported row by definition and always goes; `dedup` is a banding of the whole
   no-id population, which the clear has changed, so it goes to be recomputed.
   A dropped decision costs a rerun, never data.
5. Delete `SheetRowNumber` rows whose `row_id` is in the set.
6. Delete `ImportedRow`, then `ImportBatch`.

Step 3 hard-deletes rules on purpose. The soft delete exists so the journal can
tell the story of a rule; here there is no story to tell, because the row the
rule spoke about is gone.

Alternative considered: marking batches inactive and filtering them out of
`latest_batch`. Rejected — it satisfies the fencer list but not the requirement
("nothing cleared remains visible, restorable, or countable"), and it leaves the
numbers consumed, so the next import would start numbering at 41 on a table of
ten.

### D4 — Releasing numbers is a consequence of the delete, not a special case

`rownumbers.allocate` counts from `max(number)` among rows still present. Once
the cleared rows' `SheetRowNumber` records are gone, the next allocation
naturally continues from the highest surviving number. No "released numbers"
list, no reset counter, no free-list. A surviving row's number is never touched,
so the no-reissue rule holds for everyone the clear did not remove.

### D5 — Validation lives in a Pydantic model plus one resolver, and is mirrored, not duplicated, in the dialog

`ManualEntryIn` states shape (required name, integer hr_id, e-mail form,
ISO moment); a `_resolve_manual_entry` helper — the sibling of
`registrations._resolve_selection` — states tournament fit, raising `422` with
the same detail shapes the registration path already uses:
`unknown_disciplines`, `team_discipline_not_individual`, and a
`no_disciplines` for the emptiness that path calls `no_disciplines_or_teams`.
Rentals are the one deliberate difference: the registration path validates them
against the weapon taxonomy, while a manual entry is validated against the items
this tournament actually lends (the list the parser is given), so the refusal is
its own `unknown_rentals`.

The dialog uses the existing `useFieldValidation` / `checkString` /
`checkNumeric` machinery against the generated constraints, as `EditableCell`
does, and renders server refusals through `FieldError` against the named field.
The client never decides acceptance on its own; it only spares a round trip for
what it can see.

The registration moment defaults to now in `setup.zone_for(tournament)` and is
sent as an ISO string. It is stored as an aware datetime, and `sheet.py` emits
`isoformat()`, which `_wall_clock` already reads for either population.

### D6 — Two new frontend files under `frontend/src/manual/`, and one changed panel

`Console.tsx` is at 582 lines; the conventions in CLAUDE.md put a panel's
sections in a directory named after it. So:

- `manual/ManualEntryPanel.tsx` — the rail card with the action, mounted for
  `phase === "fencers"` beside the existing per-phase panels.
- `manual/ManualEntryDialog.tsx` — the modal form, following `MatchDialog` and
  `DisciplineDialog` for structure and the `modal-backdrop` / `modal` /
  `modal-actions` classes already in `index.css`.

Clearing goes into `ImportPanel.tsx` as a second action plus a confirmation
modal reusing the same classes as the Setup-leave confirmation. The panel stays
well under the split threshold.

## Risks / Trade-offs

- **A manually entered fencer cannot be billed, and an organizer may expect
  Payments to show them.** → The columns render as they do for imported rows —
  a dash — which is the console's existing answer for "this row has no
  registration behind it". Stated in the proposal as an explicit limit rather
  than hidden; making both populations billable is one later change, not two.
- **Reachability-based decision deletion could miss a key shape.** → A missed
  decision is an orphan row nothing reads, not a visible failure; but a test per
  decision kind (`parse`, `hr_match`, `merge`, `dedup`) asserts the table is
  empty for the tournament after a clear, which catches a shape added later.
- **Clearing is irreversible and one click away from the upload button.** →
  Confirmation states the row and file counts before it acts, and the action is
  not offered at all when there is nothing to clear.
- **`export_json` restore of an older document has no manual rows.** → The
  restore reads the key as optional and defaults to empty, exactly as it must
  already tolerate a document written before this change. Pre-launch, no real
  data — see memory — so no back-compat shim beyond that default.
- **Releasing numbers means a number the organizer wrote on paper before the
  clear can later name a different fencer.** → Accepted: the clear asserts the
  rows never existed, and the alternative (permanently retired gaps in a
  tournament that imported the wrong file twice) is worse to read.

## Migration Plan

One Alembic revision creating `manual_rows`. No data migration: nothing existing
becomes a manual row. Rollback is dropping the table; no other table's shape
changes, and the clear endpoint only deletes rows.

## Open Questions

None.
