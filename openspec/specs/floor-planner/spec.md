# floor-planner Specification

## Purpose
TBD - created by archiving change add-floor-planner. Update Purpose after archive.
## Requirements
### Requirement: The planner reads a problem and has no other input
The planner SHALL compute plans from a `Problem` and from nothing else. Every value
that can change a plan SHALL be part of the `Problem`. The planner reads no clock,
draws no random numbers, and reads and writes no file or database.

A `Problem` has four parts, as the owner document names them:
- **Facts:**
  - days and breaks;
  - pistes and their availability;
  - per discipline: its kind, its entrant count N (and for a team discipline, its
    member count as well), its format;
  - the number of persons shared by each pair of disciplines;
  - officials available per day and role.
- **Decisions:** each one free or pinned.
- **Preferences:** the soft parameters.
- **Constants:** slot lengths, overhead, minimum rest.

**Which N.** Before check-in has closed for a discipline, N SHALL be the discipline's
entry count on the floor roster. Afterwards it is the count check-in froze.

**Determinism.** The same `Problem` SHALL produce the same plans in the same order.

#### Scenario: Determinism
- **WHEN** the planner is run twice on one `Problem`
- **THEN** both runs produce identical variants in identical order

#### Scenario: A plan made ahead counts registrations
- **WHEN** a plan is made a week before the tournament for a discipline with 31 seated entrants
- **THEN** the planner plans that discipline for N = 31

### Requirement: Pool structure follows the format and the hard rule
For a discipline with N pool participants, the planner SHALL consider exactly the pool
counts k for which every pool size lies within the format's range. Pool sizes are
⌊N/k⌋ and ⌈N/k⌉. They SHALL differ by at most one.

**Who the pool participants are.** For an individual discipline, its entrants. For a
team discipline, the members of its teams, fencing individual pools.

**The bracket.** The bracket SHALL hold the advancing count A. A is the format's number,
or every pool participant where the format says "all". For a team discipline, A is the
number of teams. The bracket size is the smallest power of two that is at least A.
Top seeds receive byes to fill it.

**When no k fits.** A discipline for which no k fits SHALL be reported as infeasible,
with its N and the format's range stated. It SHALL NOT be silently given out-of-range
pools.

#### Scenario: Feasible pool counts
- **WHEN** a discipline has N = 29 and a format of 5–7
- **THEN** k = 5 (sizes 6 and 5) is feasible, and k = 4 (sizes 8 and 7) and k = 6 (sizes 5 and 4) are not

#### Scenario: No k fits
- **WHEN** a discipline has N = 4 and a format of 5–7
- **THEN** the discipline is reported infeasible, stating N = 4 and the range 5–7

#### Scenario: Byes fill the bracket
- **WHEN** 20 advance
- **THEN** the bracket has 32 places and 12 byes go to the top 12 seeds

### Requirement: Activities are scheduled within days, pistes and precedence
The planner SHALL place every activity on one piste with a start and an end. The
activities are each pool and each elimination bout, including finals and any
third-place bout. An activity's duration is set by the format:
- a pool takes the number of its bouts times the pool-bout slot, plus the per-pool
  overhead;
- an elimination bout takes the elimination slot, or the team-match slot in a team
  discipline.

**What a placement SHALL respect:**
- **Days and breaks.** Every activity lies within its discipline's day and outside that
  day's breaks.
- **Pistes.** Every activity lies on a piste available that day. In a first plan,
  reserve pistes are not used.
- **One at a time.** A piste holds at most one activity at a time.
- **Precedence.** A discipline's elimination starts after all its pools have ended.
  Round r+1 starts after round r has ended. With the "finals last" rule on, a final
  starts after every non-final activity of its day has ended.
- **Rest.** A discipline's elimination starts no earlier than the minimum rest after its
  last pool. Where two disciplines share persons and one is placed after the other, the
  gap between them is at least the minimum rest.
- **Officials.** The number of pistes in use at once does not exceed what the officials
  available that day can staff under each running discipline's template.

**An activity that cannot be placed.** An activity that cannot be placed within its day
SHALL make the variant infeasible. The overrun SHALL be stated.

#### Scenario: Finals go last
- **WHEN** two disciplines run on one day with "finals last" on
- **THEN** neither discipline's final starts before both disciplines' other activities have ended

#### Scenario: Officials cap the pistes
- **WHEN** five pistes are available but seven officials can staff only two pistes at a time under the template of one referee and two judges
- **THEN** no moment of the plan has more than two activities running

#### Scenario: A day too short
- **WHEN** a discipline's activities cannot all end before the day's end
- **THEN** the variant is infeasible and states by how many minutes it overruns

### Requirement: Variants are the non-dominated plans, ordered by preference
The planner SHALL enumerate the free decisions: k per discipline, and the day of every
discipline whose day is not pinned. It SHALL schedule each combination, keep those that
are feasible, and present the variants no other variant dominates.

**What dominance is judged on:**
- each day's last end time;
- the number of persons who must be kept out of a parallel wave;
- the number of possible bracket collisions.

**Ordering.** Variants SHALL be ordered by the soft preferences. With "prefer larger
pools" on, a variant with larger average pools comes first among otherwise equal
variants. Preferences order the variants. They never remove one.

**Explaining an empty result.** Where no variant is feasible, the planner SHALL say why.
It names the hard rule or pin without which some variant would be feasible, or, where
no single one would suffice, the discipline whose structure is infeasible. "Varianta
neexistuje kvůli pinu X" is a different message from "varianta je o 40 minut horší", and
the two SHALL NOT be merged.

#### Scenario: A pin is named as the obstacle
- **WHEN** Sabre Open is pinned to Saturday, and Saturday cannot hold it with the other pinned disciplines
- **THEN** no variant is presented, and the result names the pin of Sabre Open to Saturday

#### Scenario: Preferences order and do not remove
- **WHEN** two variants differ only in pool size, and "prefer larger pools" is on
- **THEN** both are presented, the larger-pool variant first

### Requirement: The plan hands exclusion sets and collision lists to the draw
For every pair of disciplines that share persons, the planner SHALL state which of one
discipline's pool waves run at the same time as activities of the other. That pair's
shared persons must be drawn into pools outside those waves. These are the draw's
exclusion sets (`floor-draw`).

**Shortage.** Where the waves outside the overlap cannot hold all the shared persons,
the planner SHALL report the shortage on the variant.

**Bracket collisions.** The planner SHALL also list every pair of elimination rounds of
two disciplines that share persons and overlap in time. These are possible bracket
collisions.

#### Scenario: Shared fencers are kept out of the parallel wave
- **WHEN** Longsword's second pool wave runs at the same time as Sabre's pools, and six fencers are in both
- **THEN** the exclusion sets state that those six must be drawn into Longsword's first wave

### Requirement: Sensitivity is reported with the chosen variant
For the chosen variant the planner SHALL report sensitivity:
- **Pool structure.** Per discipline, the nearest entrant counts below and above N at
  which its pool structure would change.
- **Pistes.** The change in each day's last end time with one piste more and with one
  piste fewer.
- **The limit.** Whether pistes or officials limit that day: "šestá planš ušetří 40
  minut, sedmá už nic, protože dojdou rozhodčí".

#### Scenario: The officials limit is named
- **WHEN** adding a sixth piste ends the day 40 minutes earlier, and a seventh changes nothing because the officials are exhausted
- **THEN** the sensitivity states both figures and names the officials as the limit

