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
  - whether a schedule is planned;
  - days and breaks;
  - per discipline:
    - its kind;
    - its entrant count N, and for a team discipline its member count as well;
    - its format;
    - its day;
    - the discipline whose pools it takes over, if any;
  - the pistes, each with the disciplines it serves as regular or as reserve;
  - the number of persons shared by each pair of disciplines;
  - with "Plánovat rozhodčí" on, the referees available per day and discipline,
    regular and reserve. Otherwise officials are not counted.
- **Decisions:** each one free or pinned.
- **Preferences:** the pool-size preference.
- **Constants:**
  - the lengths;
  - the pause between pools;
  - the minimum rest;
  - the finals placement.

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

**A discipline that takes over.** A discipline that takes over another's pool results
(`floor-setup`) SHALL have no pools and no k. Only its elimination is planned.

**The bracket.** The bracket SHALL hold the advancing count A. A is the format's number,
or every one of the discipline's own entrants where the format says "all". For a team
discipline, A is the number of teams. The bracket size is the smallest power of two
that is at least A. Top seeds receive byes to fill it.

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

#### Scenario: A taken-over discipline plans no pools
- **WHEN** Longsword Teams takes over the pool results of Longsword Open
- **THEN** no variant has a pool of Longsword Teams, and its elimination is planned

### Requirement: Activities are scheduled within days, pistes and precedence
With a schedule planned, the planner SHALL place every activity on one piste with a
start and an end. The activities are each pool and each elimination bout, including
finals and any third-place bout. An activity's duration is set by the format:
- a pool takes the number of its bouts times the pool-bout length;
- an elimination bout takes the elimination length, or the team-match length in a team
  discipline.

**What a placement SHALL respect:**
- **Days and breaks.** Every activity lies within its discipline's day and outside that
  day's breaks. The one exception is a final under "na konci turnaje" (below).
- **Pistes.**
  - Every activity lies on a piste that serves its discipline.
  - A piste that serves no discipline is never used.
  - A piste serving the discipline as reserve is used only where the discipline's day
    cannot be planned within its end on the regular pistes. The variant states each
    reserve piste it uses.
- **One at a time.** A piste holds at most one activity at a time. After a pool, the
  piste is kept for the format's pause between pools before its next activity.
- **Precedence.**
  - A discipline's elimination starts after all its pools have ended. For a discipline
    that takes over, that means its source's pools.
  - Round r+1 starts after round r has ended.
- **Finals,** by the finals placement:
  - "v rámci eliminace": a final follows its semifinals like any other round;
  - "na konci dne": a final starts after every non-final activity of its day has
    ended;
  - "na konci turnaje": every final and third-place bout is placed on the last day,
    after every non-final activity of the tournament has ended. On a one-day
    tournament this is "na konci dne".
- **Rest.**
  - A discipline's elimination starts no earlier than the minimum rest after the last
    pool it seeds from.
  - Where two disciplines share persons and one is placed after the other, the gap
    between them is at least the minimum rest.
- **Officials.** With "Plánovat rozhodčí" on, the pistes running at once SHALL NOT
  need more referees than are available that day. Each running piste needs its
  discipline's referees per bout for its stage. Reserve referees count only where the
  regular ones cannot staff the day.
- **Main referees, tolerated.** Main referees do not cap the pistes. Where at some
  moment more pistes run than the day has main referees available, the variant SHALL
  state it as a warning, with the moment and the shortfall. The warning never makes a
  variant infeasible and is not a dominance axis.

**An activity that cannot be placed.** An activity that cannot be placed within its day
SHALL make the variant infeasible. The overrun SHALL be stated.

#### Scenario: Finals within the elimination
- **WHEN** two disciplines run on one day with finals "v rámci eliminace"
- **THEN** each final may start as soon as its semifinals have ended and the rest has passed

#### Scenario: Finals at the end of the day
- **WHEN** two disciplines run on one day with finals "na konci dne"
- **THEN** neither discipline's final starts before both disciplines' other activities have ended

#### Scenario: Finals at the end of the tournament
- **WHEN** Sabre Open runs on Saturday and Longsword Open on Sunday with finals "na konci turnaje"
- **THEN** Sabre Open's final and third-place bout are placed on Sunday after every non-final activity of both days

#### Scenario: Referees cap the pistes
- **WHEN** five pistes serve a discipline as regular, but four referees are available that day and its pools need two referees per bout
- **THEN** no moment of its pools has more than two pools running

#### Scenario: Too few main referees is a warning
- **WHEN** four pistes run at 10:00 and only three main referees are available that day
- **THEN** the variant is feasible and warns that at 10:00 one piste lacks a main referee

#### Scenario: A day too short
- **WHEN** a discipline's activities cannot all end before the day's end, even with its reserve pistes
- **THEN** the variant is infeasible and states by how many minutes it overruns

### Requirement: Variants are the non-dominated plans, ordered by preference
With a schedule planned, the planner SHALL enumerate the free decisions, which are the
k of each discipline that has pools. It SHALL schedule each combination, keep those
that are feasible, and present the variants no other variant dominates. A discipline's
day is a fact of Setup, not a decision (owner decision 2026-11-17).

**What dominance is judged on:**
- each day's last end time;
- the number of persons who must be kept out of a parallel wave;
- the number of possible bracket collisions;
- the number of reserve pistes used.

**Ordering.** Variants SHALL be ordered by the pool-size preference, "větší skupiny" or
"menší skupiny". A variant with larger or smaller average pools, as preferred, comes
first among otherwise equal variants. The preference orders the variants and never
removes one.

**Explaining an empty result.** Where no variant is feasible, the planner SHALL say why.
It names the hard rule or pin without which some variant would be feasible, or, where
no single one would suffice, the discipline whose structure is infeasible. "Varianta
neexistuje kvůli pinu X" is a different message from "varianta je o 40 minut horší", and
the two SHALL NOT be merged.

#### Scenario: A pin is named as the obstacle
- **WHEN** Sabre Open's k is pinned to 3, and its day cannot hold three pools of that size with the other disciplines
- **THEN** no variant is presented, and the result names the pin of Sabre Open's k

#### Scenario: Preferences order and do not remove
- **WHEN** two variants differ only in pool size, and the preference is "menší skupiny"
- **THEN** both are presented, the smaller-pool variant first

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

### Requirement: Without a schedule the planner plans pool structure only
With "Plánovat rozvrh" off (`floor-setup`), the planner SHALL plan only each
discipline's pool count k and its pool sizes. It places no activity on a piste or in
time. It reads no day, piste, official, length or rest.

**Variants.** A variant is one choice of k per discipline. Every combination of
feasible k's is a variant. They are ordered by the pool-size preference, and among
equals by the discipline order and then the smaller k.

**What is reported.** Each variant states, per discipline, k and its pool sizes. There
are no exclusion sets, no collisions and no sensitivity. A pool has no wave.

**Feasibility.** Feasibility is the pool structure's alone. A discipline for which no k
fits is reported as infeasible, as with a schedule.

#### Scenario: Pool counts without times
- **WHEN** "Plánovat rozvrh" is off and Longsword Open has N = 29 with a format of 5–7
- **THEN** the planner offers k = 5 (sizes 6 and 5) and states no piste, start or day
