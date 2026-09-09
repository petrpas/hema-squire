# day-boundaries Specification

## Purpose
Define which clock each "today" is read on. Squire compares a date against the
present moment in many places, and the answer depends on what kind of date it
is: one the organizer entered, which belongs to the tournament's own timezone,
or an operational window with nobody's calendar behind it, which is UTC. The
local timezone of the server process is neither, and decides nothing.
## Requirements
### Requirement: A date threshold is read on the clock its meaning names
Squire asks "what day is it" in many places, and the answer SHALL depend on what
kind of date is being compared, never on where the process happens to run.

**A date an organizer entered** — registration opens and closes, the seating
deadline, the team composition deadline, the early-bird cutoff and any
date-valued discount condition — SHALL be read as **the whole of that day in the
tournament's own timezone**. Such a date was typed while looking at a calendar
where the tournament is held, and it means what it says there.

**An operational window with nobody's calendar behind it** — the range a bank
feed is fetched over, which tournaments the lifecycle passes still walk, a feed
token's liveness check, and the boundary the public tournament listing splits on
— SHALL be read in **UTC**.

The local timezone of the server process SHALL NOT decide any boundary. It is
neither of the two meanings above, and it makes the same deployment answer
differently from a different `TZ`.

#### Scenario: An organizer's deadline is not a UTC day
- **WHEN** a tournament held in a zone ahead of UTC carries a deadline dated the 20th, and the moment being judged falls after midnight UTC on the 21st but before midnight where the tournament is held
- **THEN** the deadline has not yet passed

#### Scenario: The server's zone decides nothing
- **WHEN** the same tournament and the same moment are judged on a deployment whose process timezone is neither UTC nor the tournament's
- **THEN** the answer is the same as on any other deployment

#### Scenario: An operational window is fixed
- **WHEN** a bank feed is fetched, or the set of tournaments still running is selected
- **THEN** the window is bounded by the UTC day, whatever the process timezone

### Requirement: A boundary decision is given an instant, never a day
Every function that decides whether one of the organizer's deadlines has passed
SHALL take the moment being judged as an **instant**, and SHALL resolve it to a
day in the tournament's timezone itself. It SHALL NOT accept an already-computed
calendar day from its caller.

The conversion therefore happens once, where the tournament is in hand, and a
caller that holds only a bare day cannot reach the decision at all. Two callers
of the same deadline SHALL NOT be able to disagree about which day it falls on.

#### Scenario: The same deadline answers the same on every path
- **WHEN** one code path asks whether seating has settled and another decides whether to settle it, at the same moment on the same tournament
- **THEN** both reach the same answer, in every process timezone

#### Scenario: A caller cannot supply the day
- **WHEN** a caller holds a calendar day rather than an instant
- **THEN** it cannot invoke the deadline decision without first naming the moment it means
