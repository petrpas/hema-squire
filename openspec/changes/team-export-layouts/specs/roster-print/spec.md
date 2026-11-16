## MODIFIED Requirements

### Requirement: The roster's columns, title and language
An individual discipline's roster SHALL carry the columns No., Fencer, Nat., Club,
HRID, Rank and Paid, stating what the tab states for each row; Paid SHALL read yes
or no as the tab's paid column does. A team discipline's roster SHALL carry the
columns `A team discipline prints as a flat roster` fixes. Either roster's title
SHALL read the tournament's name and the discipline's name joined by a dash.

The headers and the yes/no SHALL be in the console's language, or in English where
the English tick is on. The tournament's and the discipline's names, and every
fencer's name and club, and every team's name, SHALL be printed as they are
written.

#### Scenario: A Czech roster
- **WHEN** a Czech-speaking organizer downloads a roster with the English tick off
- **THEN** its headers are Czech and its paid column reads Ano or Ne

#### Scenario: An English roster
- **WHEN** the same organizer ticks English and downloads the roster
- **THEN** its headers read No., Fencer, Nat., Club, HRID, Rank, Paid and the paid column reads Yes or No

#### Scenario: The title
- **WHEN** the organizer downloads the roster of Sabre Open at Na Duel! 2026
- **THEN** its title reads Na Duel! 2026 — Sabre Open

### Requirement: The roster keeps its established look
The roster SHALL be typeset by Typst from a template carried in Squire, set in GFS
Neohellenic from font files carried in Squire, in the layout the organizer's
existing `disciplines.typ` fixes: a page as tall as its content, a bold title above
a framed table, and horizontal rules only under the header, under the last row in
and under the last row. A team discipline SHALL be typeset from a template of its
own in the same layout, which adds a thin rule between one team and the next. The
output SHALL NOT depend on fonts installed on the host.

The text the roster prints SHALL be data to the template and never part of its
source: a name, club or team name containing Typst syntax SHALL print as the
characters it is.

The PNG SHALL be one image, however long the roster.

#### Scenario: Typst syntax prints as text
- **WHEN** a fencer's club is entered as `#import "x"`
- **THEN** the roster prints `#import "x"` in the club column and renders normally

#### Scenario: A team name prints as text
- **WHEN** a team is named `#set page(width: 1cm)`
- **THEN** the team roster prints that name in the team column and renders at its usual width

#### Scenario: A long roster is one image
- **WHEN** a discipline lists 60 fencers and the organizer downloads its PNG
- **THEN** one PNG holds all 60 rows

#### Scenario: The same on every host
- **WHEN** the roster is rendered on a host with no GFS Neohellenic installed
- **THEN** it is set in GFS Neohellenic

## ADDED Requirements

### Requirement: A team discipline prints as a flat roster
A team discipline's roster SHALL carry the columns No., Team, Fencer, Nat., Club,
HRID, Rank and Paid, and SHALL list one row per fighter on a team's roster, in the
tab's order of teams and each team's roster order. A team's number, its name and
its paid cell SHALL stand on its first row only; the rows of its other fighters
leave those three cells empty. A team with no fighter on its roster SHALL be one
row stating its number, name and paid, with the fighter cells empty.

No. SHALL number teams as the tab numbers them, not fighters. Paid SHALL read the
team's paid, yes or no, as the tab's team row does. The fighter's cells SHALL state
what the tab states for that fighter.

The roster SHALL NOT print the fencer who entered a team, nor the team's member
count against the discipline's bounds. Those are the console's; the printout is
posted.

The rule the capacity line places SHALL fall under the last fighter of the last
team above the line, and a thin rule SHALL separate each team from the next.

#### Scenario: A team's cells on its first row
- **WHEN** the organizer prints a team discipline whose first team, Wolves, names four fighters and has paid
- **THEN** the first row reads 1, Wolves, its first fighter's cells and Ano, and the next three rows state only their fighters

#### Scenario: Teams are numbered, fighters are not
- **WHEN** a team discipline lists three teams of four
- **THEN** the roster has twelve rows and its No. column reads 1, 2 and 3, once each

#### Scenario: The console's facts are not printed
- **WHEN** the organizer prints a team entered by Petr Novák naming four of three to five
- **THEN** neither Petr Novák as the entering fencer nor the count 4 against 3–5 appears on the roster

#### Scenario: An empty team still prints
- **WHEN** a seated team has no fighter on its roster yet
- **THEN** the roster lists one row for it with its number, name and paid, and empty fighter cells

#### Scenario: The capacity rule falls between teams
- **WHEN** a team discipline with capacity for two teams lists two seated teams and one waitlisted team, each naming three fighters
- **THEN** the heavier rule falls under the sixth row, the last fighter of the second team

#### Scenario: An English team roster
- **WHEN** the organizer ticks English and prints a team discipline
- **THEN** its headers read No., Team, Fencer, Nat., Club, HRID, Rank, Paid
