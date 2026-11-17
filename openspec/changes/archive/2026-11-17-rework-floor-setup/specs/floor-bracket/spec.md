## ADDED Requirements

### Requirement: A discipline that takes over seeds from its source
A discipline that takes over another's pool results (`floor-setup`) SHALL be seeded from
the source's closed overall pool ranking, restricted to the target's own present
entrants.

**Seeding an individual target from a team source.** Each fencer's figure is their place
in the team source's member pool ranking.

**Seeding a team target from an individual source.** The team seeding rule of this
capability applies, with the members' places taken from the individual source's
ranking.

**Entrants without a place** (owner decision 2026-11-17). An entrant the source's ranking
does not place SHALL be seeded below every entrant it places:
- **an individual entrant,** among such entrants, by HR rating from the check-in
  snapshot, the higher first. Those without a rating come after, by lot;
- **a team** with fewer than k placed members, below every team with k placed members.
  Such teams are ordered among themselves by the average of the places they have, and
  teams with none by lot.

The lot is drawn once, when the advancement is confirmed, and kept.

**When it can be confirmed.** "Potvrdit postup" for a target SHALL require the source's
pools to be closed. Before then the target's `bracket` tab states that the source's
pools must be closed first, and links to them.

**Before confirming,** the confirmation SHALL name every entrant seeded without a place.

#### Scenario: A team seeded from the individual ranking
- **WHEN** Longsword Teams takes over Longsword Open, team sizes are 3–5, and Draci's members placed 2, 4 and 9 in Longsword Open
- **THEN** Draci's seeding figure is 5.0, computed as if the members had fenced team pools

#### Scenario: A fencer without a place goes below
- **WHEN** Longsword Women takes over Longsword Open, and two of its fencers did not fence Longsword Open
- **THEN** both are seeded below every placed fencer, by their HR rating, and the confirmation names them

#### Scenario: The target waits for its source
- **WHEN** the organizer opens Longsword Teams' bracket while Longsword Open's pools are not closed
- **THEN** the tab states that Longsword Open's pools must be closed first, and links to them

## MODIFIED Requirements

### Requirement: Brackets print and report progress
The bracket SHALL print as PDF and PNG from the adopted elimination templates, as
recorded so far.
- **An individual discipline's sheet** states the elimination bout point target, where
  the format states one.
- **A team discipline's sheet** states the points per bout and the match total.

**Progress.** Bout start and end moments SHALL be reported to the planner and to
`today`, as the pools report theirs.

#### Scenario: A printed bracket shows results so far
- **WHEN** the organizer prints Sabre's bracket after the quarterfinals
- **THEN** the PDF shows the quarterfinal winners in the semifinal slots

#### Scenario: A team bracket states its points
- **WHEN** a team discipline with team sizes 3–5 states 5 points per bout and its bracket is printed
- **THEN** the sheet states 5 points per bout and a match total of 45
