## Context

**Context: floor.**
- Floor Setup holds officials, their roles, qualifications, availability and person
  links.
- The planner caps concurrent pistes by officials count.
- The draw and bracket place persons in activities.

**The owner document.** "formalizace plánovače turnaje" names `officials.*` as the fourth
subproblem. It assigns per block, judges conflicts per pool, and receives person and
club conflicts from the schedule and the draw.

## Goals / Non-Goals

**Goals:**
- Blocks derived from the plan.
- A pure assignment step with hard constraints and soft penalties.
- Pins, swaps, re-runs, printing and badges.

**Non-Goals:**
- Bout-level assignment.
- Officials' pay, accreditation or rating.
- A screen for officials themselves. The keyed piste screen is for scoring only.

## Decisions

### D1. The engine step
`engine/officials.py` takes:
- the blocks, each with its time span, discipline, piste and template;
- the officials, with their roles, qualifications, availability and blocked spans;
- the clubs per block;
- the pins.

It returns assignments and unfilled roles.

**Algorithm:**
1. **Construction.** Fill blocks in start order. For each role, take the lowest-penalty
   feasible official.
2. **Improvement.** Pairwise swaps that lower the total penalty, until none does.
3. **Pins** are fixed before construction.

All of it is standard library and deterministic. Ties are broken by official id.

**Alternative:** solving it as an exact assignment per time slice with the Hungarian
solver from `add-floor-pools`. Kept as an improvement step if construction proves weak.
That solver is already in the engine.

### D2. Blocked spans
An official's blocked spans are the activities their linked person fences:
- before the draw, all activities of the person's disciplines;
- after it, their pool and their bracket bouts.

Entrants are read through `floor.entrants`. The adapter is not consulted directly, so a
floor-only person is handled too.

### D3. Storage
`floor_assignments` holds:
- `tournament_id`;
- `plan_id`;
- `block_key` (`<piste>:<first activity id>`);
- `role`;
- `slot`;
- `official_id`;
- `pinned`;
- `created_at`.

**Re-runs.** A re-run deletes the non-pinned rows of the affected blocks and writes new
ones.

**Unmatched pins.** A block's key is derived from its first activity. A block whose
activities moved under re-planning gets a new key. Its pins are carried over when the
same activity still starts it, and are otherwise listed as unmatched for the organizer
to resolve.

### D4. Imports that cross the floor boundary
None new. `typst` is used as in `add-floor-pools`.

### D5. Decisions made during implementation (made by me; for the owner's review)
Decided on 2026-11-17 while the owner was away, as asked:
- **The penalties' weights.** A club conflict costs 100, a piste change within a day
  10, and the load is the minutes already assigned, so the even load decides among
  otherwise equal officials. The swap step measures the load as a sum of squares.
- **An official's club is their roster person's.** Officials have no club field of
  their own. An official without a person link conflicts with no club.
- **After the draw, an official who fences** is kept off their own pool and off every
  elimination activity of their discipline, since they may advance into any of them.
- **Choosing an official on the Obsazení section pins them.** A seat set by hand is a
  decision the next re-run keeps. "— nikdo —" clears and unpins it.
- **Re-runs replace every unpinned seat of the published plan.** Pins whose block
  re-planning removed are kept and counted as unmatched.
- **The plan badge** also lights for an empty seat of the published plan.
- **Prints use one plain table template** (`app/floor/typst/table.typ`), since the
  adopted templates have no rozpis.

## Risks / Trade-offs

- **[A greedy construction can strand a scarce role.]** → Blocks are filled
  scarcest-role-first within each start time. The unfilled list makes any remaining gap
  visible, never hidden.
- **[Pins on moved blocks.]** → They are carried over by first activity, or listed as
  unmatched. They are never dropped silently.
