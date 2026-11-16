## 1. Storage and the persons and entrants seam

- [ ] 1.1 `app/floor/models.py`: the six tables of design D1. Add migration `floor_0003` and classify the columns in `account_deletion.py`.
- [ ] 1.2 `app/floor/people.py`: `persons(tournament)` (port persons plus floor-only persons) and `entrants(tournament, discipline)` (live before close, snapshot after).
- [ ] 1.3 `app/floor/gates.py` and `app/floor/steps.py`: the registries for gate invalidation and refusal (D4) and for step states (D5).

## 2. Check-in service

- [ ] 2.1 `app/floor/checkin.py`: arrival, withdrawal, lineups (bounds, one lineup per person per discipline) and floor-only persons.
- [ ] 2.2 The close gate: the impact via the planner (D3), the snapshot and the N pin.
- [ ] 2.3 Reopening: the invalidation list from the registry; refusal while results exist.
- [ ] 2.4 API under `/floor/checkin/*`, behind the console gate, with the `checkin` badge in `/floor/summary`.
- [ ] 2.5 `tests/floor/test_floor_checkin.py`: one test per `floor-checkin` scenario, including "the office is untouched" (registration rows unchanged).

## 3. Today

- [ ] 3.1 `GET /floor/today`: the matrix, slip and waiting list, with an `ETag`.
- [ ] 3.2 `tests/floor/test_floor_today.py`: the matrix states, the waiting links and the 304 on an unchanged state.

## 4. Frontend

- [ ] 4.1 `routes.ts`: `floorPath(slug, phase?, discipline?)`. Add the route in `App.tsx`.
- [ ] 4.2 `frontend/src/floor/checkin/`: search, person rows, a tick, withdrawals, the lineup editor, and the close and reopen dialogs with their impact and invalidations.
- [ ] 4.3 `frontend/src/floor/today/`: the matrix, slip, the waiting list, and the quiet 15-second refresh with its "aktualizováno v" text.
- [ ] 4.4 Add tests and the i18n strings.

## 5. Acceptance

- [ ] 5.1 `pytest tests/floor -q` passes. `ruff`, `basedpyright` and the boundary test pass.
- [ ] 5.2 `npm run typecheck`, `npm run check` and `npm test` pass.
- [ ] 5.3 `openspec validate add-floor-checkin --strict` passes.
