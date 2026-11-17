# floor-draw Specification

## Purpose
TBD - created by archiving change add-floor-pools. Update Purpose after archive.
## Requirements
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
- the number of pools and their waves from the published plan;
- the waves that run in parallel with other disciplines from the planner's exclusion
  sets;
- the club and nationality weights from floor Setup.

**Team disciplines.** The pool participants are the arrived members of the present
teams' lineups.

#### Scenario: Two clubmates are separated when they can be
- **WHEN** two fencers of one club fall into one pool under the snake, and swapping one of them within their tier separates them
- **THEN** the draw places them in different pools

#### Scenario: A dual-discipline fencer avoids the parallel wave
- **WHEN** a Longsword fencer also fences Sabre, and Longsword's second wave runs parallel to Sabre
- **THEN** that fencer is drawn into Longsword's first wave

### Requirement: Seeds come from the snapshot
**Rated entrants.** The seed order SHALL be the snapshot's ratings for the discipline,
highest first, with the HEMA Ratings rank breaking ties.

**Unrated entrants** follow every rated one. Their order comes from a random seed stored
with the draw. The same draw stored again SHALL reproduce the same pools.

#### Scenario: The draw reproduces from its seed
- **WHEN** a stored draw is recomputed from its snapshot, its seed and its weights
- **THEN** the pools are identical

### Requirement: The organizer may adjust before announcing
Before it is announced, the draw SHALL be shown pool by pool, with each fencer's seed,
club and nationality. Its score is shown broken into snake, club, nationality and wave.

**Swaps.** The organizer MAY swap two fencers. The score is recomputed and shown beside
the previous one.

**What is refused.** A swap that breaks the wave constraint, or moves a locked row-1
seed, SHALL be refused, with the reason stated.

**Starting over.** The organizer MAY redraw, which draws a new random seed.

#### Scenario: A swap shows its cost
- **WHEN** the organizer swaps two fencers of tier 3
- **THEN** the draw shows the new club and nationality penalties beside the old

### Requirement: Announcing the draw is a gate
"Vyhlásit los" SHALL freeze the discipline's pools: who is in which pool, the pool's
piste and its wave. It SHALL also pin the pools for the planner, as the draw gate's pin.

**Requirements.** Announcing requires the discipline's check-in to be closed.

**Reopening.** Reopening the draw lists what it invalidates (printed pool sheets, the
call list). It is refused while any of the discipline's bouts has a result.

#### Scenario: The draw needs a closed check-in
- **WHEN** the organizer tries to announce Rapier's draw while Rapier's check-in is open
- **THEN** the announcement is refused, and links to check-in

