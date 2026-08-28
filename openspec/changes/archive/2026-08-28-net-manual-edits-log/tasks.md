## 1. Net projection in the engine

- [x] 1.1 Add a `net_changes(audit)` projection to `app/rules.py` that groups applied changes by `(target, field)` in order, keeps the first `before`, the last `after`, every member's rule id, and the last member's actor, timestamp and phase, and drops groups whose first `before` equals its last `after`; verify with unit tests in `tests/test_rules.py` covering a single edit, an edit chain, a delete/restore pair (no entry), and delete/restore/delete (one entry attributed to the third rule)
- [x] 1.2 Fold `match_verdict` into its row's `hr_id` entry, keeping a lone `match_verdict` group when no `hr_id` group accompanies it; verify with a test over a match resolution and over a resolution later reverted to the source HR id
- [x] 1.3 Confirm a dedup merge yields one entry per absorbed row (`_merged_into`, no `_deleted`) with a test, so the existing handler behaviour is pinned before the frontend relies on it

## 2. API

- [x] 2.1 Replace `AppliedChangeOut` in `app/schemas.py` with the net entry shape (`phase`, `target`, `field`, `before`, `after`, `rule_ids`, `actor`, `at`); verify `mypy`/`ruff` pass and the schema serialises in the endpoint test below
- [x] 2.2 Return the net entries from `/sheet` in `app/routers/rules_api.py`; verify with an API test asserting a delete/restore pair produces an empty `edits` list while `rows` is unchanged
- [x] 2.3 Verify the rule journal endpoint still reports every creation and deletion for that same delete/restore pair, so history is not lost

## 3. Copy

- [x] 3.1 Add the missing `column.*` labels (`email`, `reg_name`, `merge_note`) and a `rail.edit.*` group holding the deletion and merge sentences and the entry meta format, in `frontend/src/i18n/en.json` and `cs.json`; verify both files carry the same key set
- [x] 3.2 Reword `actions.removeRule` to name undoing the change rather than removing a rule, in both languages

## 4. Console rail

- [x] 4.1 Extract the manual-edits rail from `Console.tsx` into its own component file, passing it the phase's entries and the row list; verify the console renders unchanged and `Console.tsx` shrinks
- [x] 4.2 Render an entry's row identity as its number in the current table plus the fencer's name, resolving `target` against the row list; verify with a component test that a raw row id never reaches the DOM
- [x] 4.3 Render `_deleted` and `_merged_into` as sentences (the merge naming the surviving row by number and name) and every other field by its column label with before/after values formatted as the table formats them, an empty value as a dash; verify with component tests for a field edit, a deletion, and a merge
- [x] 4.4 Make ✕ remove every rule id on the entry and refresh once; verify with a test that a twice-edited cell reverts to its source value in one press

## 5. Verification

- [x] 5.1 Run the backend and frontend test suites and the linters; verify all pass
- [x] 5.2 Walk the console against a tournament with a delete/restore/delete, a two-step field edit, and a merge; verify the rail shows one deletion entry, one field entry, and one merge entry, all readable without internal names — done live on `na-duel-2026` for the deletion (`#52 <UNKNOWN> — řádek smazán`, three rules, one entry) and the two-step field edit (one entry, source value to current, undone whole by ✕); the merge form is covered by test, the dev data holding no confirmed duplicate to merge
