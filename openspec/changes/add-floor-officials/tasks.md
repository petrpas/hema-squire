## 1. Engine

- [ ] 1.1 `app/floor/engine/officials.py`: blocks from plan activities, then construction, swap improvement and pins (D1).
- [ ] 1.2 `tests/floor/test_floor_officials_engine.py` with Hypothesis properties: no hard constraint is ever broken, pins hold, and the result is deterministic. Plus the spec scenarios.

## 2. Storage and service

- [ ] 2.1 `app/floor/models.py`: `floor_assignments`. Add migration `floor_0006` and the classifications.
- [ ] 2.2 `app/floor/officials.py`: build the inputs (blocked spans via `floor.entrants`, clubs per block), run, store, re-run on publish and draw announcement, swaps, pins, and unmatched pins after a re-plan.
- [ ] 2.3 Add the `plan` badge conditions (an unfilled role, a hard conflict) to `/floor/summary`.
- [ ] 2.4 Print the rozpis per official and the sheet per piste through Typst.
- [ ] 2.5 `tests/floor/test_floor_officials.py`: one test per `floor-officials` scenario.

## 3. Frontend

- [ ] 3.1 `frontend/src/floor/plan/AssignmentSection.tsx`: the blocks × roles grid, unfilled roles, conflicts, pin and swap controls.
- [ ] 3.2 Officials' names in the schedule panel's blocks, and the print links.
- [ ] 3.3 Add tests and the i18n strings.

## 4. Acceptance

- [ ] 4.1 `pytest tests/floor -q` passes. `ruff`, `basedpyright` and the boundary test pass.
- [ ] 4.2 `npm run typecheck`, `npm run check` and `npm test` pass.
- [ ] 4.3 `openspec validate add-floor-officials --strict` passes.
