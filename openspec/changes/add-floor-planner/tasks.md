## 1. Engine model and structure

- [x] 1.1 `app/floor/engine/model.py`: the frozen dataclasses of design D1.
- [x] 1.2 `app/floor/engine/structure.py`: pool counts, pool sizes and the bracket (size, byes, rounds, third place). Team disciplines have `n_pool` and `n_bracket` separate.
- [x] 1.3 `tests/floor/test_floor_structure.py`: the spec's examples, plus Hypothesis properties:
  - sizes always differ by at most 1 and sum to N;
  - every returned k is in range;
  - the bracket size is the least power of two ≥ A.

## 2. Scheduling

- [x] 2.1 `app/floor/engine/schedule.py`: list scheduling (D3) with days, breaks, availability, precedence, finals-last, rest and the officials cap.
- [x] 2.2 `tests/floor/test_floor_schedule.py` with Hypothesis properties:
  - no piste holds two activities at once;
  - every activity lies within its day and outside breaks;
  - precedence and rest hold;
  - concurrency never exceeds the cap;
  - reserve pistes are unused in a first plan.

## 3. Variants, explanations, handover, sensitivity

- [x] 3.1 `app/floor/engine/variants.py`: enumeration with the cap, the Pareto filter and preference ordering.
- [x] 3.2 Infeasibility explanation by removing one pin or rule at a time (D4).
- [x] 3.3 Exclusion sets, shortage and bracket collisions (D5).
- [x] 3.4 `app/floor/engine/sensitivity.py`: N thresholds, ±1 piste, and the limiting resource.
- [x] 3.5 `tests/floor/test_floor_variants.py`:
  - determinism;
  - a pin named as the obstacle;
  - preferences order without removing;
  - the shortage reported;
  - the officials limit named.

## 4. Storage and service

- [x] 4.1 `app/floor/models.py`: `floor_plans`, `floor_plan_activities`, `floor_pins` (D6). Add migration `floor_0002` and classify the columns in `account_deletion.py`.
- [x] 4.2 `app/floor/planning.py`:
  - build the `Problem` from Setup and the roster port (N, shared counts);
  - run the engine;
  - store the working version;
  - publish with the obstacle list;
  - diff;
  - re-plan with frozen activities from `app/floor/progress.py` (empty here).
- [x] 4.3 `app/floor/api.py`: `GET /floor/plan` (versions, diff), `POST /floor/plan/variants`, `POST /floor/plan/choose`, `POST /floor/plan/publish`, `POST /floor/plan/replan`, `GET/POST/DELETE /floor/plan/pins`, all behind the console gate. `/floor/summary` reports the published-plan flag and the `plan` badge (obstacles).
- [x] 4.4 `tests/floor/test_floor_plan.py`: one test per `floor-plan` scenario.

## 5. Frontend

- [ ] 5.1 `frontend/src/floor/plan/`: variants side by side, pins list, sensitivity and the publish gate, with each section in its own file.
- [ ] 5.2 `frontend/src/floor/schedule/SchedulePanel.tsx`: the piste × time grid for a chosen day, with diff marks and reserve pistes last.
- [ ] 5.3 Add tests for the variant choice, the publish gate obstacles and the diff marks. Add the i18n strings.

## 6. Acceptance

- [ ] 6.1 `pytest tests/floor -q` passes, and the engine tests use the Hypothesis `dev` profile and no database.
- [ ] 6.2 `ruff`, `basedpyright` and the boundary test pass. `engine/` imports only the standard library.
- [ ] 6.3 `npm run typecheck`, `npm run check` and `npm test` pass.
- [ ] 6.4 `openspec validate add-floor-planner --strict` passes.
