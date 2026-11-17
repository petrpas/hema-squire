## 1. Standing

- [x] 1.1 `app/floor/engine/standing.py`: places from the bracket, then the pool ranking, with shared third place and skipped numbers (D1).
- [x] 1.2 `tests/floor/test_floor_standing.py`: the spec scenario, team disciplines, and Hypothesis properties (every entrant placed once, places non-decreasing).

## 2. Results service

- [x] 2.1 `app/floor/models.py`: `floor_published_results`. Add migration `floor_0007` and the classifications.
- [x] 2.2 `app/floor/results.py`: the standing, CSV export (standing and bouts), the PDF print, the publish and withdraw gate, and the Výsledky step states.
- [x] 2.3 `tests/floor/test_floor_results.py`: one test per `floor-results` scenario.

## 3. Public surface

- [x] 3.1 `adapters/office.py`: re-export `require_public` and add `person_key_for` (D2). Extend `test_floor_boundary.py`'s real-tree run.
- [x] 3.2 `app/floor/public.py`: summary (which tabs), program, results and itinerary. Mount it in `main.py`.
- [x] 3.3 `tests/floor/test_floor_public.py`:
  - only the published plan;
  - only published results;
  - the itinerary for its owner only;
  - an unpublished tournament answers 404.

## 4. Frontend

- [x] 4.1 `frontend/src/floor/results/`: the standing, export and print, and the publish gate.
- [x] 4.2 `TournamentDetail.tsx`: the Program and Výsledky tabs from the floor's public summary, and the itinerary block for a signed-in fencer. The tabs are state, not addresses (design D6).
- [x] 4.3 Add tests and the i18n strings.

## 5. Retention

- [ ] 5.1 Once the owner decides the open question: classify the floor tables in `retention.py` and `account_deletion.py`, and revoke piste keys after the last day.

## 6. Acceptance

- [x] 6.1 `pytest tests/floor -q` passes, and so do the public-browsing tests. `ruff`, `basedpyright` and the boundary test pass.
- [x] 6.2 `npm run typecheck`, `npm run check` and `npm test` pass.
- [x] 6.3 `openspec validate add-floor-results --strict` passes.
