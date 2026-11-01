## 1. Complete tournament cascade

- [x] 1.1 Move `_cascade_delete` from `backend/app/routers/tournaments.py` to `backend/app/tournament_delete.py`; the owner's `DELETE /api/tournaments/{slug}` calls it unchanged in behaviour
- [x] 1.2 Extend the cascade to everything under registrations (team members, teams, registration disciplines and extras, payment credits, waivers, manual payments, payment events, bank transactions) and to `Operation`, in dependency order, one transaction (design D6)
- [x] 1.3 Test: build a fully populated tournament (registrations with teams, extras, credits, a waiver, a manual payment, a matched bank transaction, an import, a rule, an operation), delete it, and assert via `Base.metadata` that no table reachable from `tournaments.id` holds a row referring to it, while every fencer account survives

## 2. Admin API

- [x] 2.1 Add `created_at` to `AdminAccountOut`
- [x] 2.2 `GET /api/admin/tournaments`: one row per tournament with slug, name, date, derived state, owner (nullable), registration count, and live credited sums per currency, from grouped queries (design D4); schema in `schemas.py`
- [x] 2.3 `DELETE /api/admin/tournaments/{slug}?confirm=`: Admin role, no team check; `409 has_registrations` when registrations exist and `confirm` is not true; otherwise the shared cascade; no mail queued (design D5)
- [x] 2.4 Tests in `backend/tests/test_admin.py`: organizer below Admin refused on both endpoints; admin deletes an empty draft without confirm; unconfirmed delete with registrations refused and nothing removed; confirmed delete succeeds for an admin not on the team; no outbox row written; list reports state and credited sums (reversed credits excluded)
- [x] 2.5 `uv run ruff check .` and `uv run basedpyright` clean from `backend/`

## 3. Frontend structure and tabs

- [x] 3.1 `api.ts`: `AdminAccount.created_at`, `AdminTournament` type, `adminTournaments()`, `adminDeleteTournament(slug, confirm)`
- [x] 3.2 Split `AdminPanel.tsx` into an orchestrator plus `frontend/src/admin/` sections (design D8); move plea and account sections out unchanged first
- [x] 3.3 `AdminTabs.tsx`: tab strip on the existing `role="tablist"` markup and arrow-key handling; opens on pending tasks; tasks tab label carries the open-item count
- [x] 3.4 `sortable.ts`: sort-state hook and header cell with `aria-sort`, outline chevron, reverse on repeat selection

## 4. Tabs' content

- [x] 4.1 `TasksTab.tsx`: plea queue plus shared HR IDs grouped by `hr_id` from the account list, each account with unbind; empty groups collapse to heading plus a line
- [x] 4.2 `PeopleTab.tsx`: search (names via `nameMatches`, email and HR ID substring on folded text), sortable columns including created date, default display name ascending, no-match line
- [x] 4.3 `TournamentsTab.tsx`: search (name and owner name via `nameMatches`, slug and owner email substring), sortable columns, default date newest first, state shown as text, delete control per row
- [x] 4.4 `DeleteTournamentDialog.tsx` on `Modal`: shown only when registrations exist; states count and per-currency credited sum via `money.ts`; reminds that a real event is cancelled; confirm sends `confirm=true`; an empty tournament deletes on click; list refreshes after either
- [x] 4.5 `cs` and `en` locale keys for every new string, sentence case, no exclamation marks; locale parity test passes

## 5. Frontend tests and checks

- [x] 5.1 Tests: panel opens on tasks with count; shared HR ID group disappears after unbind; people search finds `Nováček` by `novacek`; sorting reverses on second click; empty tournament deletes without dialog; tournament with registrations opens the dialog with count and sum and deletes only on confirm
- [x] 5.2 `npm run typecheck`, `npm run check`, `npm test` clean from `frontend/`

## 6. Specs

- [x] 6.1 `openspec validate extend-admin-console` passes; check the delta specs still match what was built before archiving
