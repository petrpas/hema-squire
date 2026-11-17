# floor-officials Specification

## Purpose
TBD - created by archiving change add-floor-officials. Update Purpose after archive.
## Requirements
### Requirement: Officials are assigned to blocks, not bouts
A block SHALL be one piste's run of consecutive activities of one discipline and one
stage, pools or elimination, in the published plan. Consecutive means no gap between
them longer than the format's pause between pools.

**What is assigned.** Each block SHALL be staffed with referees, as many as its
discipline's format states per bout for that stage. Assignment never splits a block.
Every official is a referee. No other role is assigned (owner decision 2026-11-17).

#### Scenario: A wave is one block
- **WHEN** Longsword pools 1 and 5 run back to back on piste 2 in the same wave
- **THEN** they form one block, and the same referees are assigned to both

#### Scenario: The stage sets the count
- **WHEN** Sabre states one referee for pools and two for the elimination
- **THEN** each Sabre pool block is staffed by one referee and each elimination block by two

### Requirement: Hard constraints are never broken
An assignment SHALL NOT place an official:
- on a day they are unavailable;
- on a discipline they serve neither as regular nor as reserve;
- in two overlapping blocks;
- on a block that overlaps an activity the official fences in.

The last check uses the official's "Šermuje jako" link (`floor-setup`):
- **before the draw,** any activity of a discipline the person entered;
- **after the draw,** their own pool, and their bracket bouts once seeded.

**When a place cannot be filled.** It SHALL be left unfilled and stated, never filled in
breach of a hard constraint.

#### Scenario: An official who fences is kept off during their pool
- **WHEN** the official Jan Novák fences as the roster person who is drawn into Longsword pool 3 at 10:00–10:45
- **THEN** no block overlapping 10:00–10:45 is assigned to Jan Novák

#### Scenario: An unfillable place is stated
- **WHEN** no available official serves Rapier on Sunday afternoon, as regular or as reserve
- **THEN** the block's referee place is left unfilled, and the `plan` tab carries a badge naming it

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
The "Obsazení" section of the `plan` tab SHALL show blocks with their referees, the main
place, unfilled places, reserve places, blocks without a main referee, and conflicts.

**Pins.** The organizer can pin an official to a place in a block. This includes an
official who serves the block's discipline as reserve. A pinned assignment is kept by
every re-run.

**Swaps.** The organizer can swap two officials' assignments. A swap that would break a
hard constraint is refused, with the constraint named.

#### Scenario: A pin survives a re-run
- **WHEN** the organizer pins Eva to a referee place in the Sabre final block on piste 1, and then re-plans
- **THEN** Eva is still a referee of that block

### Requirement: The assignment follows the plan
The assignment SHALL be re-run for the affected blocks when:
- a new plan version is published, or
- a draw is announced (club and fencing conflicts become known).

Blocks the change does not touch keep their officials.

**On screen.** The `schedule` tab SHALL name each block's officials.

**Asking for a re-run.** The organizer can also ask for a re-run, from the `plan` tab's
operations panel (`floor-console`, A tab's operations stand in a panel on the right).

#### Scenario: A draw reveals a conflict
- **WHEN** Sabre's draw puts a referee's clubmate in the pool of the referee's block
- **THEN** the assignment for that block is re-run, and the conflict is removed or listed

#### Scenario: Officials on Rozvrh
- **WHEN** the organizer opens `schedule` after the assignment has run on a published plan
- **THEN** each block on the grid names its officials

### Requirement: The assignment prints
The floor SHALL print:
- a one-page rozpis per official, listing their blocks with day, piste, time and
  discipline, and marking the blocks where they hold the main place;
- a sheet per piste, listing its blocks and officials.

Both are PDF. They are printed from the `plan` tab's operations panel.

#### Scenario: An official's rozpis
- **WHEN** the organizer prints Eva's rozpis from the `plan` tab's operations panel
- **THEN** one page lists every block Eva is assigned to, in time order

### Requirement: Officials are planned only when asked for
The officials assignment SHALL exist only with "Plánovat rozhodčí" on (`floor-setup`).
Otherwise:
- no assignment is made or stored;
- the `plan` tab has no "Obsazení" section, and its operations panel offers no re-run
  and no officials' prints;
- the `schedule` tab names no officials;
- nothing in this capability badges a tab.

An assignment stored while the tick was on is kept, hidden, and is shown again when the
tick is turned back on and the assignment re-run.

#### Scenario: No officials, no Obsazení
- **WHEN** "Plánovat rozhodčí" is off and a plan is published
- **THEN** the `plan` tab shows no "Obsazení" section and the `schedule` tab names no officials

### Requirement: Reserve officials are used last
An official who serves a discipline as reserve SHALL be assigned to that discipline's
block only where no official who serves it as regular can fill the place without
breaking a hard constraint. Among reserve officials, the soft penalties decide.

**Stating it.** Every place filled by a reserve official SHALL be marked as such in
"Obsazení".

#### Scenario: A reserve fills a gap
- **WHEN** Sabre's afternoon block needs two referees, one regular Sabre referee is free, and Eva serves Sabre as reserve
- **THEN** the block is staffed by the regular referee and Eva, and Eva's place is marked reserve

### Requirement: A block has one main referee
Each block SHALL have one of its referee places filled by a main referee: an official
with "Hlavní rozhodčí" ticked (`floor-setup`). Further places may be filled by any
referee, main or not.

**A tolerated error.** Where no main referee can take the place without breaking a
hard constraint, the place SHALL be filled by another referee. It is never left
unfilled for this reason. The block SHALL be marked "bez hlavního rozhodčího" in
"Obsazení" and listed among the assignment's warnings. The `plan` tab SHALL carry a
badge naming the block (owner decision 2026-11-17). Publication is not refused for it.

**Order of preferences.** A main referee on every block comes before the soft
penalties. A reserve official is still used last (see Reserve officials are used last):
- a regular non-main referee is preferred to a reserve main one;
- a reserve main referee is preferred to leaving the main place to a reserve non-main.

#### Scenario: One main referee leads the piste
- **WHEN** Sabre's elimination block needs two referees, and Eva is a main referee and Petr is not
- **THEN** the block is staffed by Eva and Petr, and Eva holds the main place

#### Scenario: No main referee is tolerated
- **WHEN** the only referees free for a Rapier pool block are not main referees
- **THEN** the block is staffed by one of them, marked "bez hlavního rozhodčího", and the `plan` tab carries a badge naming it

