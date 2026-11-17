## ADDED Requirements

### Requirement: Officials are assigned to blocks, not bouts
A block SHALL be one piste's run of consecutive activities of one discipline in the
published plan, with no gap longer than the per-pool overhead between them.

**What is assigned.** Each block's staffing template, from the discipline's format,
SHALL be filled with officials by role. Assignment never splits a block.

#### Scenario: A wave is one block
- **WHEN** Longsword pools 1 and 5 run back to back on piste 2 in the same wave
- **THEN** they form one block, and the same officials are assigned to both

### Requirement: Hard constraints are never broken
An assignment SHALL NOT place an official:
- on a day they are unavailable;
- on a discipline they are not qualified for;
- in a role they cannot fill;
- in two overlapping blocks;
- on a block that overlaps an activity the official fences in.

The last check uses the official's person link (`floor-setup`):
- **before the draw,** any activity of a discipline the person entered;
- **after the draw,** their own pool, and their bracket bouts once seeded.

**When a role cannot be filled.** It SHALL be left unfilled and stated, never filled in
breach of a hard constraint.

#### Scenario: An official who fences is kept off during their pool
- **WHEN** the official Jan Novák is linked to the roster person who is drawn into Longsword pool 3 at 10:00–10:45
- **THEN** no block overlapping 10:00–10:45 is assigned to Jan Novák

#### Scenario: An unfillable role is stated
- **WHEN** no available judge is qualified for Rapier on Sunday afternoon
- **THEN** the block's judge role is left unfilled, and the `plan` tab carries a badge naming it

### Requirement: Soft penalties order the assignment
Among assignments that keep the hard constraints, the floor SHALL prefer the one with:
- the fewest club conflicts: an official whose club is the club of a fencer in the
  block's pools, judged once the draw is announced;
- the most even load across officials;
- the fewest piste changes for an official within a day.

Remaining club conflicts SHALL be listed by official, block and fencer.

#### Scenario: A club conflict is avoided when possible
- **WHEN** two equally available referees are qualified, and one shares a club with a fencer in the block's pool
- **THEN** the other referee is assigned to that block

### Requirement: The organizer can pin and swap
The "Obsazení" section of the `plan` tab SHALL show blocks × roles with names, unfilled
roles and conflicts.

**Pins.** The organizer can pin an official to a block's role. A pinned assignment is
kept by every re-run.

**Swaps.** The organizer can swap two officials' assignments. A swap that would break a
hard constraint is refused, with the constraint named.

#### Scenario: A pin survives a re-run
- **WHEN** the organizer pins Eva to piste 1's referee role in the Sabre final block, and then re-plans
- **THEN** Eva is still the referee of that block

### Requirement: The assignment follows the plan
The assignment SHALL be re-run for the affected blocks when:
- a new plan version is published, or
- a draw is announced (club and fencing conflicts become known).

Blocks the change does not touch keep their officials.

**On screen.** The schedule panel SHALL name each block's officials.

#### Scenario: A draw reveals a conflict
- **WHEN** Sabre's draw puts a referee's clubmate in the pool of the referee's block
- **THEN** the assignment for that block is re-run, and the conflict is removed or listed

### Requirement: The assignment prints
The floor SHALL print:
- a one-page rozpis per official, listing their blocks with day, piste, time, discipline
  and role;
- a sheet per piste, listing its blocks and officials.

Both are PDF.

#### Scenario: An official's rozpis
- **WHEN** the organizer prints Eva's rozpis
- **THEN** one page lists every block Eva is assigned to, in time order
