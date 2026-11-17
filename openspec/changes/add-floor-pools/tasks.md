## 1. Engine ports

- [x] 1.1 Record fixtures by running `hema-agent`'s `solver.solve` and `compute_pool_stats` offline on real inputs (NaDuel 2026 SA and SB). Check them in as JSON under `tests/floor/fixtures/`.
- [x] 1.2 `app/floor/engine/hungarian.py`: a standard-library assignment solver. Hypothesis property: its result costs no more than brute force on n ≤ 6.
- [x] 1.3 `app/floor/engine/draw.py`: port tiers, snake distance, penalties, the wave constraint, construction and improvement. Seeded `Random` for unrated fencers.
- [x] 1.4 `app/floor/engine/pool_stats.py`: port `compute_pool_stats` and the `calc_pools` checks. Add `engine/pool_order.py` with bout orders for sizes 3–10.
- [x] 1.5 `tests/floor/test_floor_draw_port.py` and `tests/floor/test_floor_pool_stats.py`: the ports reproduce the fixtures exactly; plus the `floor-draw` scenarios.

## 2. Storage and service

- [ ] 2.1 `app/floor/models.py`: `floor_draws`, `floor_pools`, `floor_pool_members`, `floor_bouts`, `floor_pool_rankings`, `floor_ring_keys`. Add migration `floor_0004` and the classifications.
- [ ] 2.2 `app/floor/pools.py`:
  - the draw from the snapshot, the plan's waves and the exclusion sets;
  - swaps, redraw and the announce gate with its pin;
  - recording and correction with the version check;
  - standings and warnings;
  - the close gate;
  - the call list.
- [ ] 2.3 Register the progress (pool start and end), the Skupiny step states and the gate hooks (D6).
- [ ] 2.4 Sheet PDFs through Typst from the adopted templates under `app/floor/typst/`.
- [ ] 2.5 `tests/floor/test_floor_pools.py`: one test per `floor-pools` scenario.

## 3. Piste screen

- [ ] 3.1 `app/floor/ring.py` and its router: issue, revoke, current work, record. Keys are hashed and rate-limited through the adapter's re-export.
- [ ] 3.2 `tests/floor/test_floor_ring.py`: revocation, the scope to one piste, the refusal after the gate, and the rate limit.

## 4. Frontend

- [ ] 4.1 `frontend/src/floor/pools/`: one file per state view (draw with swaps and the score breakdown, running, complete, closed), the transcription form, the call list and the print link.
- [ ] 4.2 `frontend/src/floor/ring/RingScreen.tsx`: the keyed route, touch-sized controls and the invalid-link state. Add `ringPath` to `routes.ts`.
- [ ] 4.3 The issue, copy, QR and revoke controls per piste. These are on the `pools` tab or in Setup's piste rows; choose one and record the choice here.
- [ ] 4.4 Add tests and the i18n strings.

## 5. Acceptance

- [ ] 5.1 `pytest tests/floor -q` passes. `ruff`, `basedpyright` and the boundary test pass. `engine/` is standard-library only.
- [ ] 5.2 `npm run typecheck`, `npm run check` and `npm test` pass.
- [ ] 5.3 `openspec validate add-floor-pools --strict` passes.
