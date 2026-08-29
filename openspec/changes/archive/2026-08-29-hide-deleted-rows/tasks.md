## 1. The removing phase on the replayed row

- [x] 1.1 In `rules.replay`, set `_removed_in` to the rule's phase on a row the rule just removed (its changes carry `_deleted → True` or `_merged_into`) and drop it on a row the rule returned (`_deleted → False`); unit test in `test_rules.py` covers delete, restore, and a merge's absorbed row
- [x] 1.2 Test that the latest removal wins: delete on `import`, restore, delete again on `dedup` leaves `_removed_in == "dedup"`, and that withdrawing the deleting rule leaves neither `_deleted` nor `_removed_in` on the next replay
- [x] 1.3 Test that a row never removed carries no `_removed_in` at all, so its absence — not a sentinel — is what "still here" means
- [x] 1.4 Note the field in the `sheet` module docstring as a replay product of the projection, and confirm `test_determinism.py` still passes (the field is derived, so it must not disturb byte-identical replay)

## 2. What a phase lists

- [x] 2.1 Extend `SheetRow` in `api.ts` with `_removed_in?: string` and `_deleted?: boolean`, documented as the phase that removed the row and never a stored column
- [x] 2.2 Rewrite `rowsForPhase` to drop a removed row whose `_removed_in` sits strictly earlier in `PHASES` than the phase being viewed, keeping the existing `imp:`-and-file-order handling of Import; test in `consolePhases.test.tsx` with a row deleted on `fencers` — listed on `import` and `fencers`, absent from `matching`, `dedup`, `payments`, `export`
- [x] 2.3 Drop a row carrying `_merged_into` from every phase but Import, ahead of the phase-order comparison; test that an absorbed row is absent from Fencers and still listed, marked absorbed, on Import
- [x] 2.4 Test that a row whose `_removed_in` names no known phase stays listed on every phase, so an unplaceable removal can never hide a row from the tab that could restore it
- [x] 2.5 Test that the footer's row and paid counts are unchanged by the filter — they count live rows, which no phase ever hides

## 3. Restoring where the row is listed

- [x] 3.1 The actions column asks `rowAction` what a row offers: restore on a listed removed row, delete on a live one, nothing on an absorbed one — whose removal the merge owns, not the row (revised from "needs no new condition"; see the note below). Test that the restorable rows of a phase are exactly the removed rows it lists
- [x] 3.2 Test that restoring from the deleting phase returns the row to every phase, unmarked
- [x] 3.3 Test that the manual-edits rail still names a row the current phase does not list, and that withdrawing that entry restores the row — the rail keeps receiving the full row set, not the phase's view

## 4. Verification

- [x] 4.1 Full backend and frontend suites pass (`pytest`, `npm test`, `npm run build`)
- [x] 4.2 Run the console against the dev database: delete a row on Fencers and confirm it is struck through there, absent from Matching through Export, and back everywhere after a restore; delete a row on Payments and confirm Fencers still lists it and restores it

> Note on 3.1: the task assumed the actions column needed no change. It did.
> Rendering restore on `_deleted` alone offered it on absorbed rows too, and
> restoring one would leave it un-deleted and still merged — which the spec's
> "a merge is undone by withdrawing the merge" denies. `rowAction` states the
> three cases instead, and the Import view now offers no action on an absorbed
> row. No spec change; the specs already said this.
