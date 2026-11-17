## MODIFIED Requirements

### Requirement: The draw is the adopted pool alchemy
The floor SHALL draw a discipline's pools with the pool alchemy solver adopted from
`hema-agent` (`pre_tournament/pool_alch_agent`). Its rules are kept as they stand there:
- **Seed tiers.** The seed order is laid along the snake over k pools.
  - Row 1 is locked.
  - Row 2 is swapped only within row 2.
  - Rows 3 and 4 are swapped only within rows 3–4.
  - Later rows are free.
- **Snake deviation.** Displacing a fencer of tiers 1–2 costs its snake distance.
- **Club penalty.** A club with n members in one pool costs the club weight × n(n−1)/2.
- **Nationality penalty.** It is the spread of foreign fencers, and of each foreign
  nationality, across pools, normalised by the number of foreign nationalities. The most
  frequent nationality counts as domestic.
- **Wave constraint.** A fencer the planner's exclusion sets keep out of a wave SHALL
  NOT be placed in it.

**What the draw reads:**
- the number of pools from the published plan, and their waves where a schedule is
  planned;
- the waves that run in parallel with other disciplines from the planner's exclusion
  sets, where a schedule is planned;
- the club and nationality weights from the `plan` tab's preferences (`floor-plan`).

**Without a schedule.** With "Plánovat rozvrh" off there are no waves and no exclusion
sets, and the wave constraint binds nothing.

**Team disciplines.** The pool participants are the arrived members of the present
teams' lineups.

**Disciplines that take over.** A discipline that takes over another's pool results has
no draw.

#### Scenario: Two clubmates are separated when they can be
- **WHEN** two fencers of one club fall into one pool under the snake, and swapping one of them within their tier separates them
- **THEN** the draw places them in different pools

#### Scenario: A dual-discipline fencer avoids the parallel wave
- **WHEN** a Longsword fencer also fences Sabre, and Longsword's second wave runs parallel to Sabre
- **THEN** that fencer is drawn into Longsword's first wave

#### Scenario: A draw without a schedule
- **WHEN** "Plánovat rozvrh" is off and Longsword Open's draw is made
- **THEN** the draw places fencers by seeds, clubs and nationalities only, with no wave constraint

### Requirement: The organizer may adjust before announcing
Before it is announced, the draw SHALL be shown pool by pool, with each fencer's seed,
club and nationality. Its score is shown broken into snake, club, nationality and wave;
without a schedule there are no waves, and neither the pools nor the score name one.

**Swaps.** The organizer MAY swap two fencers. The score is recomputed and shown beside
the previous one.

**What is refused.** A swap that breaks the wave constraint, or moves a locked row-1
seed, SHALL be refused, with the reason stated.

**Starting over.** The organizer MAY redraw, which draws a new random seed.

**A new plan.** Publishing a new plan version SHALL discard every draw not yet
announced, since its pool count and waves came from the plan it replaces. The next
draw reads the new plan. An announced draw is pinned and stays. The publishing
confirmation says so.

#### Scenario: A swap shows its cost
- **WHEN** the organizer swaps two fencers of tier 3
- **THEN** the draw shows the new club and nationality penalties beside the old

#### Scenario: Publishing discards an unannounced draw
- **WHEN** Longsword Open's draw of nine pools is made but not announced, and a plan version with eight pools is published
- **THEN** the draw is gone, and the next draw makes eight pools

#### Scenario: Publishing keeps an announced draw
- **WHEN** Longsword Open's draw is announced and a new plan version is published
- **THEN** the draw and its pools are unchanged
