## ADDED Requirements

### Requirement: Nationality is stated as a flag
On every roster of the public entrants view, the Nat. cell SHALL state a nationality from
which a country can be read as that country's national flag, alone, in place of any code
or name. A nationality is read as a country the way the familiar-entrants match reads one
(`public-browsing`), as an ISO 3166 alpha-2 code whatever vocabulary it was written in:
either ISO code, the English name, the official name, or one of the aliases Squire keeps, so "CZ", "CZE" and "Czech Republic" all draw the
Czech flag and "England" draws the flag of the United Kingdom. The flag SHALL carry the
country's name in the page's language as its accessible name and as the title shown on
hover. A nationality from which no country can be read SHALL be stated as written, as
text. An empty nationality SHALL leave the cell empty.

This SHALL hold for an individual's row, a side event's row, a team member's row and a
team's row where it states the nationality all its members share. A team whose members'
nationalities differ SHALL leave the cell empty, as now.

The flag SHALL be drawn small enough to sit within the row's line height, at the flag's
own proportions with no cropping, framed by a hairline so that a flag mostly white
still reads against the paper. It SHALL be a file Squire serves itself; no flag SHALL be
fetched from a third party, and no emoji SHALL draw one.

The flag of Russia SHALL be drawn in greyscale, not in its colors; it is otherwise drawn
and named as every other flag.

The flag SHALL NOT reach any other screen or output: the organizer console, the Export
tables, the data export and the printed roster (`roster-print`) SHALL keep stating the
nationality as they do.

#### Scenario: A Czech fencer
- **WHEN** a visitor reading Czech opens a roster holding a fencer whose nationality is "CZ"
- **THEN** the Nat. cell shows the Czech flag and no code, and its accessible name is "Česko"

#### Scenario: Spellings of one country draw one flag
- **WHEN** a roster holds three fencers whose nationalities read "PL", "Poland" and "POL"
- **THEN** all three Nat. cells show the Polish flag

#### Scenario: The Russian flag in greyscale
- **WHEN** a roster holds a fencer whose nationality reads "Russia"
- **THEN** the Nat. cell shows the Russian flag in greyscale, named as Russia, while the other flags on the roster keep their colors

#### Scenario: A spelling no country is read from
- **WHEN** a fencer's nationality reads "Bohemia"
- **THEN** the Nat. cell states "Bohemia" as text and shows no flag

#### Scenario: A team sharing a country
- **WHEN** every member of a team records nationality "SK"
- **THEN** the team's row shows the Slovak flag, and each member's row, when opened, shows it too

#### Scenario: The console keeps codes
- **WHEN** the organizer opens the Export tab of the discipline whose public roster shows flags
- **THEN** its Nat. column states the codes, and no flag is drawn
