## 1. Backend — deriving the values

- [x] 1.1 Add a `SetupSuggestionsOut` response schema to `backend/app/schemas.py` with `locations: list[str]`, `bank_accounts: list[str]` and `organizers: list[OrganizerOut]` (reusing the existing organizer name/link shape); verify by importing the module and instantiating it with an empty payload in a REPL or a scratch test.
- [x] 1.2 Add a `_suggestion_scope(session, fencer)` helper in `backend/app/routers/tournaments.py` returning the caller's tournaments — `owner_id == fencer.id` **or** id in `_organized_tournament_ids()` (design D6), drafts and cancelled included; verify with a unit test asserting an organizer sees their own draft and does not see a stranger's tournament.
- [x] 1.3 Add a `_distinct_recent(values, cap)` helper that de-duplicates preserving order and caps at 8 (design D5); verify with a unit test covering a repeated value, ordering preservation, and a history longer than the cap.
- [x] 1.4 Implement `GET /tournaments/suggestions` returning all three lists in one payload, ordering the scope by `Tournament.date` descending, reading organizers through `schemas.tolerant_organizers()` so legacy bare-string entries yield `{name, link: null}` (design D2/D5); verify with a test that a tournament whose `organizers` holds a bare string is suggested without error.
- [x] 1.5 Key the organizer suggestions on the `(name, link)` pair with empty link normalized to `null`, so one club with two links yields two entries and one club with `""` vs `null` yields one; verify with a test covering both cases (spec: One name, two links).

## 2. Backend — scoping and tests

- [x] 2.1 Add `backend/tests/test_setup_suggestions.py` covering the per-account scoping requirement: two organizers with disjoint tournaments are offered nothing of each other's, including bank accounts (design D7, spec: One organizer's values stay their own); verify the test passes.
- [x] 2.2 Add tests for the derived-not-stored requirement: correcting a value on its source tournament changes what is suggested next request, and a tournament created before this change is suggested with no backfill (spec: A corrected value stops being offered / Tournaments that predate the capability); verify both pass.
- [x] 2.3 Add a test that an account newly granted console access to an existing tournament gains its values (spec: Access granted after the fact); verify it passes.
- [x] 2.4 Add a test asserting the endpoint requires authentication and that a call leaves every tournament unmodified (spec: Suggestions are read-only and leave no trace); verify it passes.
- [x] 2.5 Run the full backend suite and confirm no existing test regresses.

## 3. Frontend — the suggestion component

- [x] 3.1 Add `suggestions()` to `frontend/src/api.ts` calling the new endpoint, with the response types; verify by type-checking the project.
- [x] 3.2 Create `frontend/src/SuggestionList.tsx` — a generic list rendered beneath an input, taking the candidate values, the current text and an `onChoose` callback, with case-insensitive substring filtering (design D3/D4) and rendering nothing when the filtered set is empty; keep it under the one-component-per-file convention.
- [x] 3.3 Implement keyboard behavior in the component: arrow keys move an active index, Enter chooses, Escape dismisses leaving typed text untouched, blur closes; verify against the spec's Keyboard choice and Dismissing the list scenarios.
- [x] 3.4 Give the component the ARIA combobox roles (`role="combobox"` on the input wiring, `role="listbox"`/`role="option"`, `aria-activedescendant`, `aria-expanded`) so the offered values are announceable (design D3).
- [x] 3.5 Style the list in `frontend/src/index.css` on the `HelpHint` precedent — `--paper-raised`, `1px solid var(--ink)`, 2px radius, `--focus` for the active entry — using only `tokens.css` values, with no shadow, no blur and no entrance animation; verify by auditing the new rules against the CLAUDE.md prohibition list.
- [x] 3.6 Add `frontend/src/suggestions.test.ts` unit-testing the filter and ordering helpers (substring match, case-insensitivity, empty query returns all up to the cap); verify the tests pass.

## 4. Frontend — wiring the three fields

- [x] 4.1 Fetch the suggestions once where the Setup sections mount, and swallow a failed fetch into an empty set so a fetch error renders plain fields (design D2, Risks); verify by observing Setup still loads with the endpoint returning 500.
- [x] 4.2 Wire `location` in `frontend/src/setup/IdentitySection.tsx` through the component without disturbing the existing `values`/`dirty`/validation flow; verify the save bar's dirty count still moves by one when a suggestion is chosen.
- [x] 4.3 Wire `bank_account` in `frontend/src/setup/BankAccountSection.tsx`; verify that choosing a suggestion runs the same `checkString` validation a typed value does (spec: A recalled value that no longer validates).
- [x] 4.4 Wire the organizer name in `frontend/src/setup/OrganizersSection.tsx` so choosing sets **both** name and link in one `patch(index, …)` call (design D3, spec: Name and link arrive together); verify a chosen club with no stored link leaves the link field empty rather than stale.
- [x] 4.5 Confirm no other Setup field gained the affordance (spec: A field outside the three), and that a first-time organizer sees no list and no hint of the feature (spec: The very first tournament).

## 5. Localization and finish

- [x] 5.1 Add the new keys to `frontend/src/i18n/cs.json` and `frontend/src/i18n/en.json` — the list's accessible label and any empty/loading text — with no hardcoded strings in the component; verify `backend/tests/test_i18n.py` (and the frontend's key-parity check, if it applies) passes.
- [x] 5.2 Run the frontend test suite, type-check and lint; confirm all pass.
- [x] 5.3 Exercise the flow in the running app: create a second tournament under an account that already has one, and confirm the club, venue and account are offered, chosen by keyboard, and saved (spec: Organizer's second tournament).
- [x] 5.4 Run `openspec validate add-setup-field-suggestions --strict` and confirm the change validates.
