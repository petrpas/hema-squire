## Context

**Context: floor.** After `add-floor-pools`, a discipline's pools close with a frozen
ranking. The published plan already has the elimination's rounds placed on pistes. Team
disciplines have individual pools of their lineup members, followed by a team
elimination (owner decision 2026-11-16).

**What already exists.** `hema-agent` `in_tournament/render_elim.py` fills
per-size Typst templates (`elimination_<size>.typ`) from the pool ranking.

## Goals / Non-Goals

**Goals:**
- Seeding, byes, the confirm gate, recording with advancement, the third place, closing
  and printing.
- Team elimination with its seeding and match recording.
- Progress for slip and re-planning.

**Non-Goals:**
- Repechage, double elimination, or a second pool round. The format offers single
  elimination only.
- Recording the individual bouts within a team match. Only the match result is recorded
  for now.

## Decisions

### D1. Seeding order in the pure engine
`engine/bracket.py` computes the standard order recursively:
1. Start from `[1, 2]`.
2. To double it, replace each seed s with `(s, size + 1 − s)`.

That is the placement the `hema-agent` templates assume: the fencers block fills the
slots in that order. A port test compares the engine's order with the template's
expected slot list for every supported size.

**Byes.** A slot whose seed exceeds A is empty, and its opponent advances without a
recorded bout.

### D2. Storage
| Table | Holds |
|---|---|
| `floor_brackets` | `tournament_id`, `discipline_id`, `size`, `advancing`, `confirmed_at`, `confirmed_by` |
| `floor_bracket_slots` | `bracket_id`, `round`, `position`, `entrant_key` (NULL until filled), `bye` |
| `floor_bouts` | (from `add-floor-pools`) gains `bracket_id`, `round` and `position` beside `pool_id`, with exactly one of the two set |

**Advancement** is computed when a bout is recorded, in one transaction with the
recording. The next slot is written by the same request.

**Corrections.** A correction that changes a winner is refused when the next slot's bout
is recorded. That keeps every stored slot consistent with the bouts below it.

### D3. Team seeding
The team's seed is computed from its arrived lineup members' entries in the
discipline's closed pool ranking: the average place of its best k members, for team
size bounds k–l (owner decision 2026-11-16). It lives in `engine/bracket.py` as one
function, so changing it changes one place.

### D4. Steps, gates, progress
- `steps.py` registers the Pavouk states.
- `gates.py` registers:
  - bracket results as a refusal for reopening the pools;
  - the bracket as invalidated by reopening the pools before any bracket bout is
    recorded.
- `progress.py` gains elimination bout moments.

### D5. Imports that cross the floor boundary
None new. `typst` is imported as in `add-floor-pools`.

## Risks / Trade-offs

- **[The template's slot order and the engine's order disagree for some size.]** → The
  port test runs every supported size before release.
- **[A slot written by advancement can disagree with a corrected bout.]** → Advancement
  and correction are refused together whenever the next bout is recorded. The slot is
  rewritten in the same transaction as the bout.

## Open Questions

None left. Resolved 2026-11-16 (owner): teams are seeded by the average overall pool
place of their best k members, for team size bounds k–l. The tie-break by the best
single member place is this change's own addition, and is the place to adjust if the
owner's practice differs.
