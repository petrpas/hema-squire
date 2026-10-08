## ADDED Requirements

### Requirement: A discipline roster prints to PDF and PNG
A discipline tab of the Export phase SHALL offer two actions, **PDF** and **PNG**,
each downloading the tab's roster typeset as a document of that format. No other
tab SHALL offer them.

The file SHALL be named `<tournament slug>-<discipline slug>` with the format's
extension, and SHALL be offered as a download.

#### Scenario: A discipline offers both
- **WHEN** the organizer opens the Sabre Open tab
- **THEN** its rail card offers PDF and PNG

#### Scenario: Other tabs do not
- **WHEN** the organizer opens the Fencers, Merch or Summary tab
- **THEN** its rail card offers neither PDF nor PNG

#### Scenario: The file is named for what it holds
- **WHEN** the organizer downloads the PNG of Sabre Open on tournament `na-duel-2026` whose discipline slug is `SA`
- **THEN** the file is `na-duel-2026-SA.png`

### Requirement: The printout is the tab as it stands
The roster SHALL list the rows the tab lists, in the order it lists them, with the
filter it applies: the active-only switch and the seeding order as they are set
when the action is pressed. Its position column SHALL number the rows as the tab
numbers them.

Where the tab draws its capacity line, the roster SHALL draw a rule under the last
row above it; where the tab draws no line, the rule SHALL fall under the last row.

#### Scenario: The seeding order prints
- **WHEN** the organizer ticks the seeding order on Sabre Open and downloads its PDF
- **THEN** the PDF lists the fencers in seeding order, numbered as on screen

#### Scenario: Active only prints only the active
- **WHEN** Sabre Open lists 24 fencers, 20 of them paid, and the organizer switches it to active only and downloads its PNG
- **THEN** the PNG lists the 20, numbered 1 to 20

#### Scenario: The capacity rule
- **WHEN** Sabre Open has capacity 24, 24 seated fencers and 3 queued
- **THEN** the roster has a rule under its 24th row and lists the 3 queued below it

### Requirement: The roster's columns, title and language
The roster SHALL carry the columns No., Fencer, Nat., Club, HRID, Rank and Paid,
stating what the tab states for each row; Paid SHALL read yes or no as the tab's
paid column does. Its title SHALL read the tournament's name and the discipline's
name joined by a dash.

The headers and the yes/no SHALL be in the console's language, or in English where
the English tick is on. The tournament's and the discipline's names, and every
fencer's name and club, SHALL be printed as they are written.

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
and under the last row. The output SHALL NOT depend on fonts installed on the host.

The text the roster prints SHALL be data to the template and never part of its
source: a name or club containing Typst syntax SHALL print as the characters it is.

The PNG SHALL be one image, however long the roster.

#### Scenario: Typst syntax prints as text
- **WHEN** a fencer's club is entered as `#import "x"`
- **THEN** the roster prints `#import "x"` in the club column and renders normally

#### Scenario: A long roster is one image
- **WHEN** a discipline lists 60 fencers and the organizer downloads its PNG
- **THEN** one PNG holds all 60 rows

#### Scenario: The same on every host
- **WHEN** the roster is rendered on a host with no GFS Neohellenic installed
- **THEN** it is set in GFS Neohellenic
