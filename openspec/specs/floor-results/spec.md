# floor-results Specification

## Purpose
TBD - created by archiving change add-floor-results. Update Purpose after archive.
## Requirements
### Requirement: The final standing follows the bracket, then the pools
Once a discipline's bracket is closed (`floor-bracket`), the floor SHALL compute its
final standing:

| Place | Who |
|---|---|
| 1 and 2 | the final's winner and loser |
| 3 and 4 | where there was a third-place bout, its winner and loser. Otherwise both semifinal losers share 3 |
| next places | the losers of each earlier round, beginning with the quarterfinals. Within one round they are ordered by the closed pool ranking. The places start after the last place given above |
| last | those who did not advance, ordered by the closed pool ranking |

**Team disciplines** SHALL rank teams the same way. Their pool ranking is the team
seeding of `floor-bracket`.

#### Scenario: Quarterfinal losers by pool ranking
- **WHEN** a bracket of 16 with no third-place bout closes, and its quarterfinal losers were 3rd, 9th, 6th and 12th in the pool ranking
- **THEN** both semifinal losers share 3rd, and the quarterfinal losers are placed 5th–8th in the order 3rd, 6th, 9th, 12th of the pool ranking

### Requirement: The results tab shows, exports and prints
The `results` tab SHALL show each discipline's final standing, with name, club and
nationality.

**Export.** It SHALL export as CSV:
- the standing;
- every bout of the discipline, with its pool or round, both entrants, the scores and
  the outcomes.

**Print.** It SHALL print the standing as PDF.

#### Scenario: Bouts are exported
- **WHEN** the organizer exports Sabre's bouts
- **THEN** the CSV lists every pool and elimination bout with both entrants, scores and outcomes

### Requirement: Publishing results is a gate
"Zveřejnit výsledky" SHALL be offered for a discipline once its bracket is closed.

**What publishing does.**
- It makes that discipline's standing public (`floor-public`).
- It sets its Výsledky cell on `today` to "zveřejněny". The cell reads "čeká" before.

**Withdrawing.** Withdrawing publication is possible and states that the public page
changes at once.

#### Scenario: Unpublished results are not public
- **WHEN** Sabre's bracket is closed but its results are not published
- **THEN** the public Výsledky tab does not list Sabre

