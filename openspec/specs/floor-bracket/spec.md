# floor-bracket Specification

## Purpose
TBD - created by archiving change add-floor-bracket. Update Purpose after archive.
## Requirements
### Requirement: The bracket is seeded from the closed pool ranking
Once a discipline's pools are closed (`floor-pools`), the `bracket` tab SHALL propose the
seeded bracket:
- **Who advances.** The top A of the closed pool ranking, where A is the format's
  advancing count. With "all", every ranked entrant advances.
- **Size.** The bracket's size P is the least power of two ≥ A.
- **Placement.** Seeds are placed in the standard bracket order, the order of the
  adopted `hema-agent` elimination templates. Seeds 1 and 2 can meet only in the final,
  and seeds 1–4 only from the semifinals.
- **Byes.** The top P − A seeds receive byes in the first round.

#### Scenario: Twenty advance into thirty-two
- **WHEN** 20 advance
- **THEN** the bracket has 32 places, seeds 1–12 have first-round byes, and seed 1 and seed 2 are in opposite halves

### Requirement: Confirming the advancement is a gate
"Potvrdit postup" SHALL freeze the seeded bracket.

**Requirements.** It requires the discipline's pools to be closed.

**Reopening** is refused once any bout of the bracket has a result.

#### Scenario: The bracket waits for the pools
- **WHEN** the organizer opens Sabre's bracket while Sabre's pools are complete but not closed
- **THEN** the tab states that the pools must be closed first, and links to them

### Requirement: Elimination bouts advance their winner
An elimination bout SHALL be recorded by the model `floor-pools` adopts. In addition:
- **A winner is required.** A Draw outcome is refused.
- **Walkovers.** A bout one side does not fence is recorded with outcome "No" for that
  side and a note. The other side advances.
- **Advancing.** Recording a bout SHALL place its winner in their slot of the next
  round.
- **Corrections.** Correcting a bout that changes its winner SHALL be refused while the
  next round's bout involving that slot has a result. The refusal names that bout.

#### Scenario: A winner advances
- **WHEN** seed 5 beats seed 12 in the round of 16
- **THEN** seed 5 appears in the quarterfinal slot that bout feeds

#### Scenario: A correction that would orphan a later result is refused
- **WHEN** the organizer changes the winner of a quarterfinal whose semifinal is already recorded
- **THEN** the correction is refused, naming the semifinal

### Requirement: The third place and the end of the bracket
Where the format asks for a third-place bout, the two semifinal losers SHALL meet in it.

**Closing.** The bracket closes when its final, and its third-place bout where there is
one, are recorded.

**States.** The `bracket` tab and the Pavouk column of `today` SHALL state "čeká",
"nasazen", "běží" and "uzavřen".

#### Scenario: The bracket closes after the final
- **WHEN** the final and the third-place bout are recorded
- **THEN** the Pavouk cell reads "uzavřen"

### Requirement: Team disciplines eliminate teams
In a team discipline, the bracket's entrants SHALL be the present teams.

**Team seeding** (owner decision 2026-11-16). A team's seeding figure is the average
overall pool place of its best k members, where the discipline's team size bounds are
k–l. Members who did not fence in the pools do not count. A lower figure seeds higher.
A tie is broken by the team's best single member place.

**A team short of k** placed members cannot happen in the bracket: a team is present
only with at least k arrived lineup members (`floor-checkin`).

**Team matches.** A team match is recorded as one result with each team's final score.
A draw is refused, as in any elimination bout.

#### Scenario: Teams seeded by their best members
- **WHEN** team sizes are 3–5, team Draci's five members placed 2, 4, 9, 20 and 31 and team Vlci's three placed 3, 5 and 6
- **THEN** Draci's figure is 5.0 (2, 4, 9) and Vlci's 4.67, so Vlci are seeded above Draci

#### Scenario: A team match result
- **WHEN** team Draci beats team Vlci 45:38
- **THEN** Draci advance and the match is recorded with both scores

### Requirement: Brackets print and report progress
The bracket SHALL print as PDF and PNG from the adopted elimination templates, as
recorded so far.

**Progress.** Bout start and end moments SHALL be reported to the planner and to
`today`, as the pools report theirs.

#### Scenario: A printed bracket shows results so far
- **WHEN** the organizer prints Sabre's bracket after the quarterfinals
- **THEN** the PDF shows the quarterfinal winners in the semifinal slots

