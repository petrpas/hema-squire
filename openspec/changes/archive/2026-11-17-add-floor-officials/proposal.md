## Why

The planner caps concurrent pistes by how many officials there are. It does not name
who stands where. The fourth subproblem of the owner's planner document, `officials.*`,
does that: it assigns officials to piste blocks under the staffing template, keeps them
off pistes while they fence, and avoids club conflicts.

The owner document fixes the grain. An official is assigned to a block (piste ×
contiguous time, typically a wave), not to a bout. A conflict of interest is then
judged at the level of the pool. That is coarser, but it prints on one sheet of paper.

**Context:** floor. No office module is touched beyond column classification.

## What Changes

- **Blocks.** A block is a piste's run of consecutive activities of one discipline in
  the published plan, typically a wave of pools or a run of elimination rounds. The
  blocks are derived from the plan.
- **The assignment.** A pure engine step (`engine/officials.py`) fills each block's
  staffing template with officials.
  - **Hard constraints:**
    - the official is available that day;
    - qualified for the discipline;
    - able to fill the role;
    - not in two blocks at once;
    - not on a block that overlaps any activity they fence in. This uses the person link
      from floor Setup and, once known, their pool and bracket placement.
  - **Soft penalties:**
    - an official whose club appears in the block's pools, once the draw is announced;
    - an uneven load;
    - needless piste changes.
  - It reads the planner's conflict inputs: the persons and clubs per pool from the
    draw.
- **Where it lives.** The assignment appears on the `plan` tab as the section "Obsazení":
  - a block × role grid with names;
  - unfilled roles stated;
  - conflicts listed.

  The organizer can pin an official to a block or swap two officials. The schedule panel
  names each block's officials.
- **When it is redone.** Re-planning or announcing a draw re-runs the assignment for the
  blocks it affects. Pinned assignments stay.
- **Printing.** A one-page rozpis per official and a sheet per piste, as PDF.
- **The `plan` badge** gains its conditions: an unfilled role, or a hard conflict.

## Capabilities

### New Capabilities
- `floor-officials`: blocks, the assignment and its constraints and penalties, pins and
  swaps, re-running, printing, and the `plan` badge conditions.

### Modified Capabilities
None. Officials' facts are already in `floor-setup`. `floor-plan`'s Plan tab gains a
section through this capability's own requirement.

## Impact

- **Backend:**
  - `app/floor/engine/officials.py`;
  - `app/floor/officials.py`;
  - table `floor_assignments`, migration `floor_0006`.
- **Frontend:**
  - `frontend/src/floor/plan/AssignmentSection.tsx`;
  - schedule panel labels;
  - print links.
