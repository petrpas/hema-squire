## Context

**Context: floor.** After `add-floor-checkin`, a closed discipline has a snapshot of its
entrants. After `add-floor-planner`, the published plan has its pools: count, sizes,
pistes, waves and exclusion sets.

**What already exists.** The owner runs pool draws and results today with `hema-agent`:
- `pool_alch_agent/solver.py`, 330 lines: two phases, a Hungarian construction per
  window and a swap improvement.
- `results_agent/results_agent.py` `compute_pool_stats`, and `calc_pools.py` with its
  checks.
- Typst templates for pool lists and brackets.

**Owner decision of 2026-11-16.** The ranking and bout-recording rules are adopted, not
re-specified.

## Goals / Non-Goals

**Goals:**
- Port the solver and the stats into the pure engine, with behaviour unchanged.
- The pool states, sheets, recording, standings, close gate, call list and progress.
- The keyed piste screen.

**Non-Goals:**
- Changing the adopted rules. If the owner wants other ranking rules, that is a later
  change against `floor-pools`.
- The elimination. That is `add-floor-bracket`.
- Officials on pistes. That is `add-floor-officials`.
- Reading results from photographed sheets. `hema-agent` does this with a vision LLM,
  and that capability stays outside the floor for now.

## Decisions

### D1. Port, don't call
`hema-agent` is a separate repository built around Discord and Google Sheets. The floor
takes its algorithms only:
- `engine/draw.py` ports `solver.py` and `models.py` (`PoolFencer`, `Weights`,
  `PoolConfig`, `Score`) as frozen dataclasses.
- `engine/pool_stats.py` ports `compute_pool_stats`, and the checks from `calc_pools`.

**Hungarian assignment.** The engine is standard-library only, so
`scipy.optimize.linear_sum_assignment` is replaced by a standard-library Hungarian
implementation of about 80 lines. It runs on square matrices of at most k × k, and k is
rarely above 16.

**Proving the port.** A test fixture runs both the original and the port on recorded
inputs and compares their outputs. The originals are run once, offline, and their
outputs are checked in as JSON. The floor tests never import `hema-agent`.

**Alternative:** depend on `hema-agent` as a package. Rejected. It drags in Discord,
gspread, pydantic-ai and numpy, and it would break the engine rule.

### D2. Randomness without a clock
The draw needs an order among unrated fencers. The service draws a 64-bit seed with
`secrets` and stores it with the draw. The engine receives it and uses
`random.Random(seed)`, the standard library's deterministic generator. The engine stays
pure: the same input gives the same output.

### D3. Tables
| Table | Holds |
|---|---|
| `floor_draws` | `tournament_id`, `discipline_id`, `seed`, `weights` (JSON), `score` (JSON), `announced_at` (NULL before), `announced_by` |
| `floor_pools` | `draw_id`, `number`, `wave`, `piste_id`, `planned_start` |
| `floor_pool_members` | `pool_id`, `entrant_key`, `ordinal`, `seed` |
| `floor_bouts` | `pool_id` (or NULL for elimination, see `add-floor-bracket`), `order`, `a_key`, `b_key`, `score_a`, `score_b`, `outcome_a`, `outcome_b`, `note`, `recorded_at`, `recorded_by` (a user id or `ring:<piste>`), `version` |
| `floor_ring_keys` | `tournament_id`, `piste_id` (unique while live), `key_hash`, `issued_at`, `revoked_at` |

**Concurrent writes.** `floor_bouts.version` gives optimistic concurrency. Two writers
correcting one bout get a 409 on the second, which re-reads.

**The standings** are never stored. They are computed from the bouts. Closing the pools
stores the frozen ranking in `floor_pool_rankings` (`discipline_id`, `entrant_key`,
`place`, the stats JSON).

### D4. Bout order
The sheet's bout order is the standard pool order for sizes 3–10, as the adopted
`hema-agent` templates print it. It is ported into `engine/pool_order.py` as a table.
Sizes outside 3–10 are not reachable, because `floor-setup` bounds a format's range to
3–10.

### D5. The piste screen's access
The ring screen follows the guest-registration pattern:
- **The key.** It is in the fragment and sent in an `X-Floor-Ring-Key` header.
- **Storage.** It is stored as a SHA-256 hash, as `managekey` stores a guest key.
- **Scope.** It covers one piste of one tournament.

**Endpoints.** They live under `/api/floor/ring/*`, a router of the floor, and are
rate-limited with the existing limiter. The limiter lives in `app.ratelimit`, which is
outside the allow-list. So the ring router takes its limit through
`adapters/office.py`, re-exported like the dependencies. That is listed under D7.

**What "current work" is.** It is the earliest activity on the piste in the published
plan that has not ended. Before the draw is announced there is nothing to record, and
the screen says so.

### D6. Progress and steps
- `app/floor/progress.py` gains the pools' start and end moments. They come from
  `floor_bouts.recorded_at` minima and maxima per pool.
- `steps.py` registers the Skupiny states.
- `gates.py` registers two hooks:
  - the draw as invalidated by reopening check-in;
  - results as a refusal for reopening check-in and the draw.

### D7. Imports that cross the floor boundary
- `app/floor/adapters/office.py` re-exports `limiter` from `app.ratelimit` for the ring
  router. **This is new.** `app.ratelimit` is reached only through the adapter.
- `typst`, a third-party package already declared by the backend, is imported by
  `app/floor/pools.py` for sheet printing. Rule 1 restricts only `app.*` imports.
- `engine/draw.py`, `engine/pool_stats.py` and `engine/pool_order.py` use the standard
  library only. `random` is used only through a seeded `Random` instance.

## Risks / Trade-offs

- **[The port can differ from the original in an edge case.]** → Recorded inputs from
  real tournaments (NaDuel 2026 SA and SB are in the owner's tree) run through both. The
  outputs must match exactly before the port is trusted.
- **[The Hungarian replacement is slower than scipy's.]** → k ≤ 16 makes each window
  matrix at most 16 × 16. That is negligible.
- **[A leaked piste link lets someone record results.]** → It is scoped to one piste's
  current work, revocable, and rate-limited. Every write is attributed to
  `ring:<piste>` and correctable from the console until the gate.

## Open Questions

None left. Resolved 2026-11-16 (owner):
- **Draw.** The `pool_alch` logic is adopted as it is, fixed seed tiers included. It
  may be adjusted later, for example by making the tier boundaries a parameter, in a
  change of its own.
- **Bout order.** The `hema-agent` templates' order is kept.
