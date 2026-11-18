## 1. Office fetch split (no office behavior change)

- [x] 1.1 Split `hr_sync.take_snapshot` into `fetch_ratings(tournament, fetcher, hr_ids, codes)` (page loop, category match, drift rejection, no writes) and the storing `take_snapshot`; existing `tests/test_hr*` stay green unchanged
- [x] 1.2 `adapters/office.py`: `fetch_discipline_ratings(session, tournament, discipline_id, hr_ids, fetcher)` resolving the discipline's taxonomy code; re-export `get_hr_fetcher`/`HRFetcher`

## 2. Roster port: members' ratings

- [x] 2.1 `TeamEntry.ratings` parallel to `members`, filled by the adapter from each member row's `ratings[slug]`/`ranks[slug]`; schema `FloorRosterOut` and `floorApi.ts` types follow
- [x] 2.2 Test in `tests/floor`: a member's rating travels with the team (spec floor-roster scenario)

## 3. Sheet storage and overlay

- [x] 3.1 Models `FloorSheetEdit`, `FloorSheetEntry`, `FloorSheetTeam`, `FloorSheetFetch`, `FloorSheetRating`; `FloorLocalPerson.hr_id`; migration `floor_0010_data_sheet`; migrate the dev DB
- [x] 3.2 `app/floor/datasheet.py`: `Edits`, pure `apply(base, edits) -> Roster` with precedence hand edit > floor fetch > roster (design D2), added entries and their local persons, added `floorteam:` teams from their lineups, team member ratings
- [x] 3.3 `load`, `roster`, `roster_of`; switch every floor caller (`api.py`, `pools_api.py`, `public.py`, ring) from the adapter's `roster`/`roster_of` to `datasheet`
- [x] 3.4 Boundary test: only `datasheet.py` imports the adapter's `roster`/`roster_of`; adapter remains the only office reader
- [x] 3.5 Factor `seeding_key` into `people.py`, used by `pools.py` and by the sheet's order (design D8)
- [x] 3.6 Hypothesis test of `apply`: an empty `Edits` is the identity; a hand edit always wins over a fetch; persons and entries keep their keys

## 4. Sheet endpoints

- [x] 4.1 `GET /floor/sheet/{discipline_id}`: rows in seeding order with edited/withdrawn/added flags and paid; `closed`, `fetched_at`, `missing`; snapshot rows when closed, paid from the live sheet
- [x] 4.2 `PUT /floor/sheet/cells` with validation (rating bounds as the office, positive HR ID, non-empty name; empty value deletes the edit); local person fields edit the `FloorLocalPerson` row
- [x] 4.3 `POST /floor/sheet/{discipline_id}/entries` (existing person or new local person) and `DELETE .../entries/{person_key}` (additions only, with their withdrawal)
- [x] 4.3a `POST/DELETE /floor/sheet/{discipline_id}/teams` (name + members, existing or new local persons, held to team bounds via `lineup_errors`; delete removes lineup and withdrawal)
- [x] 4.4 `POST /floor/sheet/{discipline_id}/ratings`: fetch the discipline's (or its team members') HR ids, store into `floor_sheet_fetches/ratings`; 502 on rejected fetch with the sheet unchanged
- [x] 4.5 Every write refused with 409 `checkin_closed` on a closed discipline; a person cell refused only when every discipline the person entered is closed
- [x] 4.6 Tests per spec scenarios: club corrected once (office export unchanged), walk-in counts toward N, Data removal = desk withdrawal, team formed on the day, paid not editable and empty for additions, refresh asks only the discipline's HR ids and leaves the office snapshot untouched, hand edit survives refresh, closed discipline refuses writes, snapshot keeps a corrected rating

## 5. Frontend shared pieces from the office

- [x] 5.1 Make `ExportGrid`/`ExportColumn` generic over the row type; office call sites unchanged in behavior (`exportTables.test.tsx` green)
- [x] 5.2 Extract `export/RatingsRefresh.tsx` (icon, hint, result line, `ratingsState` line) from `TableOperations`, which renders it

## 6. Floor Data sheet UI

- [x] 6.1 `data` joins `STEP_TABS`; `FloorConsole` passes `discipline`/`fallback`; `DisciplineStrip` without "Všichni"
- [x] 6.2 Split `floor/data/` into `DataTab` (orchestrator), `SheetTable`, `TeamSheetTable`, `DataPanel`, `AddEntrant` (`Modal`), plus `columns.ts` with the office column ids and `export.column.*` headings
- [x] 6.3 Editable cells (`EditableCell`, `cell-edited` mark), "Odebrat"/"Vrátit" per row with struck-through withdrawn rows, "Přidat účastníka" at the head of the work (a team form on a team discipline); paid cell read-only
- [x] 6.4 Panel: `RatingsRefresh` for the chosen discipline; the closed line ("prezence uzavřena <kdy> · pro změnu ji znovu otevřete"); Import link for organizer-kept tournaments
- [x] 6.5 Closed discipline: snapshot rows, nothing editable, no refresh
- [x] 6.6 i18n cs/en for new strings (sentence case, no exclamation marks)
- [x] 6.7 Tests: strip carries the choice to `checkin`; columns and order; edit marks; withdrawn row; closed sheet read-only; panel refresh calls the floor endpoint, not `ratingsSnapshot`

## 7. Checks

- [x] 7.1 `uv run ruff check .` and `uv run basedpyright` from `backend/`; `pytest tests/floor tests/test_hr* -q`
- [x] 7.2 `npm run typecheck`, `npm run check`, `npm test` from `frontend/`
- [ ] 7.3 By hand in the browser: edit, add, remove, refresh, close check-in, reopen; narrow-screen drawer holds the refresh
