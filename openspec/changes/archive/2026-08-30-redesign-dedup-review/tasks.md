## 1. Backend: the candidate group model

- [x] 1.1 Extend `_record_view` in `backend/app/dedup.py` to project `number`, `hr_name`, `hr_nationality` and `hr_club` beside the merge fields it already carries (design D2)
- [x] 1.2 Add `merge_rule_for(session, tournament, key)` to `dedup.py`: scan `rules.active_rules(session, tournament, "dedup_decision")` and return the rule whose `group_key([rule.target] + rule.payload["absorb"])` equals `key`, else None (design D3)
- [x] 1.3 Replace `pending_queue` with `candidate_groups(session, tournament, rows)` returning every group of all three lanes — same-hr_id `merge` decisions, and the `surely` and `likely` bands of the stored `dedup` decision — each as `{key, kind, verdict, decided_by, members, recommendation: {fields, note}, conclusion}` (design D2, D3)
- [x] 1.4 Derive `verdict` per D3: `merged` where a merge rule stands, `separate` where a `dedup_resolution` says `accepted: False`, `pending` otherwise; set `decided_by` from the resolution's `source` and `conclusion` from the standing rule's payload where merged, null otherwise
- [x] 1.5 Keep members ordered oldest-first by `registered_at` and keep dropping groups whose surviving membership falls below two, and groups whose members a deletion removed
- [x] 1.6 Leave `pending_count` and `_work_units` alone: they are the operation's total — the LLM questions a run will ask — and not the review queue's size. The pending count the phase states is the groups the view already holds, counted where it is stated (design D9)
- [x] 1.7 Rewrite `decide` as a total, idempotent verdict over any candidate group (design D4): on accept, `rules.update_rule` the standing merge rule's payload or `create_rule` where none stands, then store `dedup_resolution {accepted: True}` with `source="organizer"`; on reject, `rules.delete_rule` any standing merge rule and store `{accepted: False}`
- [x] 1.8 Confirm `run_dedup`'s auto-merge guard still reads the `dedup_resolution` record, so a withdrawn surely merge is not re-applied by the next run, and add the surely band to what `candidate_groups` lists

## 2. Backend: the API

- [x] 2.1 Rename `GET /import/dedup/queue` to `GET /import/dedup/groups` in `backend/app/routers/import_api.py`, returning `dedup.candidate_groups(...)`
- [x] 2.2 Let `POST /import/dedup/decide` reach any group: it no longer 404s `not_pending` for a settled key, and still 404s a key no group answers to
- [x] 2.3 Update `backend/tests/test_dedup.py` and any other backend test naming the queue endpoint or `pending_queue`

## 3. Backend tests

- [x] 3.1 A surely group is listed as `merged` with `decided_by: "llm"`, and its members and conclusion are the ones the merge recorded
- [x] 3.2 Deleting the merge rule (as the manual-edits log's undo does) returns the group to `pending` and to `pending_count`
- [x] 3.3 Rejecting a merged group deletes its rule, un-merges the rows, and leaves the group `separate`; merging a separate group merges it, with exactly one `dedup_decision` rule standing
- [x] 3.4 Confirming twice updates the standing rule rather than creating a second, and the rule id is unchanged so the log keeps one entry
- [x] 3.5 A decision carrying edited `fields` and `note` produces a survivor holding the edited values, not the recommendation
- [x] 3.6 A rerun after a withdrawn auto-merge does not re-merge the group
- [x] 3.7 A group whose member was deleted on Fencers is no longer listed
- [x] 3.8 Group members carry `number` and the HR evidence fields

## 4. Frontend: the API client

- [x] 4.1 Replace `DedupItem` with `DedupGroup` in `frontend/src/api.ts` — `key`, `kind`, `verdict`, `decided_by`, `members` (typed with the fields D2 lists), `recommendation`, `conclusion` — and drop the under-specified `rows` shape
- [x] 4.2 Replace `dedupQueue` with `dedupGroups`; give `dedupDecide` the signature `(slug, key, accept, fields?, note?)` and send them

## 5. Frontend: the Console seam

- [x] 5.1 Extract the `<main className="sheet-area">` block from `Console.tsx` into `frontend/src/SheetArea.tsx` with the props it already reads, leaving behaviour identical (design D8)
- [x] 5.2 Empty `PHASE_COLUMNS.dedup`, and branch the workspace to render `<DedupView>` in place of `<SheetArea>` on the dedup phase while keeping the rail
- [x] 5.3 Check `consoleCells`, `consolePhases`, `consoleMarkers` and `consoleOperations` tests still pass against the extracted component, updating imports rather than expectations

## 6. Frontend: the deduplication view

- [x] 6.1 Create `frontend/src/dedup/mergeFields.ts`: the group table's columns, each merge field's kind (text, number, list, boolean, fixed), and `choicesFor(field, members)` returning the distinct member values in member order (design D6)
- [x] 6.2 Create `ConclusionCell.tsx`: displays the drafted value, opens onto the member choices plus a free-text entry seeded with the current value, validates text and number fields with `checkString`/`checkNumeric`, renders list fields as includable values and booleans as a toggle; the popover takes the `suggestion-list` treatment and no other
- [x] 6.3 Create `ConclusionRow.tsx`: holds the conclusion draft, renders one cell per column, renders identity cells read-only where the group is bound to a profile (design D7), renders `hr_id` and `registered_at` read-only always, and carries the editable merge note beneath
- [x] 6.4 Create `DedupGroup.tsx`: the bordered block — what raised the group (shared HR id or band) as its heading, the member table using `identityValue` for the identity columns and `NoteMarker` for notes, the conclusion under a `--rule-strong` rule, the verdict and its actions
- [x] 6.5 Give each verdict its actions: pending → confirm the conclusion / keep separate; merged → keep separate / reopen the conclusion and confirm again; separate → merge with the conclusion. State on a merged group whether the machine or the organizer decided it
- [x] 6.6 Create `DedupView.tsx`: header with the pending count (design D9), the pending groups first, then the settled ones, and the one-sentence empty state offering the run when no group stands
- [x] 6.7 Move `DedupPanel.tsx` into `frontend/src/dedup/` and reduce it to the run control, the busy notice, the not-configured error and the operation's outcome — the queue and its count leave it
- [x] 6.8 Reload the groups when a decision lands and when a dedup operation concludes, as the panel does today via `operations.concluded.dedup`

## 7. Frontend: styling and copy

- [x] 7.1 Add the group block and conclusion row rules to `index.css` — 1px `--hairline` frame, no radius above 2px, the conclusion separated by `2px solid var(--rule-strong)`, no shadow, no stripe — and remove `.dedup-actions` if nothing uses it
- [x] 7.2 Add the Czech and English strings: the view heading and count, the lane headings, the verdict labels, the actions, the machine-decided marking, the conclusion's affordances, the note label, and the empty state (one sentence, no exclamation mark)
- [x] 7.3 Check the result against the prohibitions in `CLAUDE.md` — no emoji, no filled icons, no pill, no second saturated color, no hex outside `tokens.css`

## 8. Frontend tests

- [x] 8.1 A group renders its members and its conclusion in the same columns, and the conclusion reads the recommendation before it is touched
- [x] 8.2 A conclusion cell offers each member's distinct value and a typed value, and the draft survives until confirmation
- [x] 8.3 Confirming sends the edited fields and note in one `dedupDecide` call
- [x] 8.4 Identity cells of a bound group's conclusion do not open; those of an unbound group do; `hr_id` never does
- [x] 8.5 A machine-merged group states so and offers the opposite verdict in one action
- [x] 8.6 The empty state appears with no groups, and the count states the pending ones only
- [x] 8.7 The dedup phase renders no fencer table and keeps its rail

## 10. One decision, one entry

- [x] 10.1 `_apply_dedup_decision` in `backend/app/rules.py` applies the merged values and the merge note without appending them to the audit, reporting only the absorption (design D11)
- [x] 10.2 A backend test: confirming a merge that changes a field and writes a note leaves one entry for that group, naming the absorption, and undoing it reverses the values too
- [x] 10.3 Check the log against a real merge already taken in the console: the dedup phase carries one entry for it, naming the absorption

## 9. Verification

- [x] 9.1 Run the backend suite and the frontend suite
- [x] 9.2 Drive the console against a tournament with a same-hr_id pair, a likely group and an auto-merged group: confirm one with an edit, keep one separate, withdraw the automatic merge, undo a merge from the manual-edits log and see the group return to pending
- [x] 9.3 Confirm Fencers, Matching, Payments and Export are unchanged, and that a row deleted on Fencers drops out of the candidate groups
