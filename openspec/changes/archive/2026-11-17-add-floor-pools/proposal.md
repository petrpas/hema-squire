## Why

Once check-in has closed for a discipline, its entrants have to be drawn into pools, the
pools fenced and scored, and a pool ranking produced for the bracket.

The owner already runs this outside Squire. `hema-agent` has two parts:
- **Pool alchemy** (`pre_tournament/pool_alch_agent`) draws pools. Seed tiers protect
  the snake, and weighted penalties separate clubs, spread nationalities and keep
  dual-discipline fencers out of parallel waves.
- **The results pipeline** (`in_tournament/results_agent`) records bouts as score1,
  score2 and outcome. It ranks by V/M, then index, then touches scored.

The owner decided on 2026-11-16 that pool ranking and bout recording are not
re-specified here. The existing solution is adopted. This change brings both into the
floor, with the console and a piste screen around them.

**Context:** floor. No office module is touched beyond column classification.

## What Changes

- **The draw.** The `hema-agent` pool alchemy solver is ported into
  `app/floor/engine/draw.py`.
  - It keeps:
    - seed tiers (row 1 locked, row 2, rows 3–4, the rest free);
    - snake distance;
    - the club penalty C(n,2) × weight;
    - the normalised nationality spread;
    - the wave constraint.
  - The planner supplies the waves and their parallelism (exclusion sets from
    `floor-planner`). Floor Setup supplies the weights.
  - **Seeds** come from the snapshot's ratings. Unrated entrants follow the rated, in an
    order drawn from a stored random seed.
  - **Before announcement**, the organizer can swap two fencers and see the score
    change.
  - **Announcing** the draw is a gate. It freezes the pools and pins them for the
    planner.
- **Pools (`pools`):**
  - **Per discipline**, the tab moves through the pool states: draw, running, ranking.
  - **Pool sheets** come with the bout order and print as PDF through Typst, from the
    `hema-agent` templates.
  - **Bout results** are recorded by the adopted model: score1, score2, outcome per side
    (Win / Loss / Draw / No), and an optional note such as a walkover or a medical. They
    are entered bout by bout or by transcribing a whole paper sheet.
  - **Pool standings and the discipline's overall pool ranking** come from the adopted
    `compute_pool_stats`. The adopted consistency checks raise warnings: the bouts
    expected per fencer, and touches scored equal to touches received per pool.
  - **"Uzavřít skupiny"** is a gate. It needs every bout recorded and freezes the
    ranking that seeds the bracket.
  - **A call list** names the fencers of the next wave's pools and the planned time.
- **The piste screen** at `/floor/ring/:piste`:
  - It opens from a keyed link (owner decision 2026-11-16). The key sits in the URL
    fragment, as a guest management link's does.
  - It shows only the current pool or bout of its piste, with large controls for a
    phone or tablet.
  - The organizer copies the link, shows it as a QR code, and can revoke it.
- **Progress.** A pool starts when its first bout is recorded and ends when its last
  is. That feeds the planner's frozen activities (re-planning) and the slip on `today`.
- **Team disciplines.** Pools are individual pools of the arrived lineup members. The
  team elimination's seeding is `add-floor-bracket`'s.

## Capabilities

### New Capabilities
- `floor-draw`: the adopted draw with its seeds, tiers, penalties and waves. It also
  covers swaps, and announcement as a gate.
- `floor-pools`: pool states, sheets, bout recording, the adopted standings and checks,
  the close gate, the call list, and progress.
- `floor-ring`: the keyed piste screen, and its links, QR codes and revocation.

### Modified Capabilities
- `floor-today`: the Skupiny column gains its states. Those states are defined in
  `floor-pools`, not by changing `floor-today`'s requirement text, so there is no
  delta.

## Impact

- **Backend:**
  - `app/floor/engine/draw.py`: a standard-library port of the solver. `scipy`'s
    Hungarian assignment is replaced by a standard-library implementation.
  - `app/floor/engine/pool_stats.py`: a port of `compute_pool_stats`.
  - `app/floor/pools.py` and `app/floor/ring.py`.
  - Typst templates under `app/floor/typst/`.
  - Tables `floor_draws`, `floor_pools`, `floor_pool_members`, `floor_bouts` and
    `floor_ring_keys`, migration `floor_0004`.
- **Dependencies:** `typst` is already a backend dependency, used by office roster
  print. The floor imports the package directly, never `app.rosterprint`.
- **Frontend:**
  - `frontend/src/floor/pools/`;
  - `frontend/src/floor/ring/RingScreen.tsx` on a public-shell route outside the
    organizer layout;
  - `routes.ts`: `ringPath(slug, piste, key)`.
