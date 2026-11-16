## Why

The closed pool ranking decides who advances. The elimination still has to be seeded,
fenced round by round, and finished with a final and, where the format asks, a
third-place bout.

The owner already prints brackets from `hema-agent` Typst templates. This change brings
the bracket into the floor, so that its bouts are scheduled, recorded and visible like
the pools.

Team disciplines meet their team elimination here. Their pools were individual pools of
the lineup members (owner decision 2026-11-16).

**Context:** floor. No office module is touched beyond column classification.

## What Changes

- **Seeding.** The advancing count A comes from the format, which always states it, with
  "all" as the default.
  - The top A of the closed pool ranking are placed into a single-elimination bracket of
    size P, the least power of two ≥ A.
  - Placement uses the standard bracket order, so seeds 1 and 2 can meet only in the
    final. Byes go to the top P − A seeds.
  - The order follows the adopted `hema-agent` elimination templates.
- **"Potvrdit postup"** is a gate. It freezes the seeded bracket.
- **Bouts:**
  - An elimination bout is recorded by the same adopted model as a pool bout.
  - A bout must name a winner; a draw is not an elimination outcome.
  - A walkover or a withdrawal is recorded with outcome "No" and a note, and the
    opponent advances.
  - The winner of each bout advances to the bout's place in the next round.
  - With a third-place bout in the format, the semifinal losers meet in it.
- **States on `bracket` and `today`:** čeká, nasazen, běží, uzavřen. The bracket closes
  when its final (and third-place bout) is recorded.
- **Team disciplines.** The team elimination is seeded from the teams' members' results
  in the individual pools: the average place of each team's best k members, for team
  size bounds k–l.
  A team match is recorded as one result with the teams' final scores.
- **Recording.** The keyed piste screen (`floor-ring`) serves elimination bouts as it
  serves pools. The console records and corrects bouts until the bracket closes.
- **Progress and printing.**
  - Bout start and end moments feed re-planning and slip.
  - The bracket prints as PDF and PNG from the adopted templates.

## Capabilities

### New Capabilities
- `floor-bracket`: seeding, byes, the confirm gate, bout recording and advancement, the
  third place, team elimination seeding and matches, states, closing, printing and
  progress.

### Modified Capabilities
None. `floor-ring` already covers elimination bouts, and `floor-today` takes the Pavouk
states through the step registry.

## Impact

- **Backend:**
  - `app/floor/engine/bracket.py`: seeding order, byes, advancement and third place, in
    pure code;
  - `app/floor/bracket.py`;
  - Typst templates for elimination sizes;
  - tables `floor_brackets` and `floor_bracket_slots`, which reuse `floor_bouts` for
    results, migration `floor_0005`.
- **Frontend:** `frontend/src/floor/bracket/`.
