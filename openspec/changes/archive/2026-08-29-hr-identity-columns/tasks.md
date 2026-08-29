## 1. The resolution module

- [x] 1.1 Add `frontend/src/identity.ts` with `IDENTITY_COLUMNS`, `usesHRIdentity(phase)` and `identityValue(row, column, hrIdentity)` per design Decision 2; verify it type-checks with `npm run build` in `frontend/`
- [x] 1.2 Add `frontend/src/identity.test.ts` covering: a bound row reading the HR register on an HR-identity phase; an unbound row reading the registered values with `declared: true`; a bound row whose profile carries no club reading an em dash upright, not the registered club; `usesHRIdentity` true for dedup/payments/export and false for setup, import, fencers, matching, teams and queue — verify with `npm test`

## 2. The table

- [x] 2.1 Give `CellDisplay` in `Console.tsx` an optional `hrIdentity` prop and a branch for the three identity columns that renders `identityValue`, wrapping a declared value in `<span className="identity-declared">`; verify the existing `consoleCells.test.tsx` and `consoleMarkers.test.tsx` still pass unchanged
- [x] 2.2 Pass `usesHRIdentity(phase)` into both `CellDisplay` call sites in the table body; verify by opening Deduplication on a tournament with matched and unmatched rows and seeing HR values upright beside registered values in italic
- [x] 2.3 Replace the flat `EDITABLE_COLUMNS.has(column)` test in the table body with the `editableHere(column, phase)` predicate from design Decision 4, exported for test; verify identity cells no longer open an editor on Deduplication, Payments and Export while `hr_id` cells still do

## 3. The italic register

- [x] 3.1 Add `.identity-declared { font-style: italic; }` to `frontend/src/index.css` with no color, weight or hex of its own (design Decision 5); verify by inspecting an unmatched row on Payments and confirming the cell is italic and reads at the same ink as its neighbours

## 4. Coverage

- [x] 4.1 Extend `frontend/src/consolePhases.test.tsx` with a case asserting that name, nationality and club are read-only on dedup/payments/export and editable on import/fencers/matching; verify with `npm test`
- [x] 4.2 Add a rendering case asserting that resolving a match on a previously unbound row makes its Payments identity cells state the profile's values without the italic class (spec scenario "Resolving a match changes how later phases read the row"); verify with `npm test`
- [x] 4.3 Run the full frontend suite and `npm run build`, and confirm no backend test was touched — this change has no server-side surface

## 5. Close-out

- [x] 5.1 Run `openspec validate hr-identity-columns --strict` and confirm it passes
- [x] 5.2 Walk the console once end to end — Import, Fencers, Matching, Deduplication, Payments, Export — confirming Matching's claim-beside-evidence layout is unchanged and every later phase identifies each row the same way
