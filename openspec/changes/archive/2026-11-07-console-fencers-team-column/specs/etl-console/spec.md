## ADDED Requirements

### Requirement: The teams a row entered, on the fencer list

On a tournament that has a team discipline, the Fencers phase's table SHALL state,
in a column of its own placed directly after Club, the teams the row's registration
entered. The column SHALL be labelled as the team the row entered, in both
languages the console speaks.

A row MAY have entered several teams — in different team disciplines, or more than
one in the same discipline. The cell SHALL state every one of them, one team per
line, in the order the teams were entered.

Where the tournament has **more than one** team discipline, each team SHALL be
named with the discipline it was entered into: there a bare name does not say
which of the tournament's team disciplines this team stands in. Where the
tournament has **one** team discipline, the team SHALL be stated by name alone —
every team is in that discipline, and naming it on every row repeats what the
reader already knows.

The column SHALL state the teams the row **entered** — those billed on this
registration — and nothing else. A team's members are roster names local to that
team and are not registrations; a fencer named on someone else's roster SHALL NOT
be shown as being in that team by this column, and a member who holds no
registration of their own SHALL NOT appear on the fencer list at all.

A row that entered no team SHALL read a dash, on the same terms as an absent club:
an imported row, a row entered by hand, and a registration holding only individual
entries all read a dash rather than an empty cell.

The column SHALL be read-only. A team's name belongs to the fencer who entered it
and is corrected in that fencer's own roster editor (`team-disciplines`); the cell
SHALL NOT open for editing and an edit to it SHALL NOT be offered, so that the
console never shows a correction the roster never received.

The column SHALL be offered only where the tournament's team disciplines feature is
on and the tournament has at least one team discipline. A tournament with no team
discipline SHALL show the fencer table it shows today, unwidened. In keeping with
**Phase-tabbed fencer table**, this SHALL be a second declared set of columns for
the phase rather than a condition inside one set, so that no column has to be
understood as sometimes present.

The column SHALL belong to the Fencers phase alone. The Export tables, the public
entrants rosters and the read-only Teams view SHALL be unchanged by it.

#### Scenario: The team stands after the club
- **WHEN** the organizer of a tournament with a team discipline opens the Fencers phase
- **THEN** the table's columns read name, nationality, club, team, and then the phase's own columns

#### Scenario: Two teams in two disciplines
- **WHEN** a row's registration entered "Rudá růže" into the longsword team discipline and "Ulice 2" into the sabre team discipline
- **THEN** its team cell states both, each with the discipline it was entered into, one above the other

#### Scenario: The tournament's only team discipline is not named
- **WHEN** the tournament has one team discipline and a row entered "Rudá růže" into it
- **THEN** its team cell reads the name alone, without the discipline

#### Scenario: Two teams in one discipline
- **WHEN** a row's registration entered two teams into the same team discipline, on a tournament that has another team discipline as well
- **THEN** its team cell states both, each naming that discipline, in the order they were entered

#### Scenario: A row that entered no team
- **WHEN** the row holds only individual entries, or arrived by import, or was entered by hand
- **THEN** its team cell reads a dash

#### Scenario: A roster member is not a team entry
- **WHEN** a fencer holds a registration of their own and is also named on a team another fencer entered
- **THEN** that team is stated on the entering fencer's row and not on theirs

#### Scenario: The cell does not open
- **WHEN** the organizer clicks a team cell on the Fencers phase
- **THEN** nothing opens for editing, and the manual-edits log gains no entry

#### Scenario: No team discipline, no column
- **WHEN** the organizer of a tournament whose team disciplines feature is off, or which has the feature on but no team discipline configured, opens the Fencers phase
- **THEN** the table has no team column, and the columns read name, nationality, club, and then the phase's own
