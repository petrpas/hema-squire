## ADDED Requirements

### Requirement: Location presentation on cards and the information line
The tournament location SHALL be presented as an inline markdown field (`organizer-prose`) everywhere a fencer reads it. On the tournament information screen it SHALL render on the `date · place · qualification` line, a location link appearing there as a link. On a Fencer Home card it SHALL render on the bold date-and-place line as label text only, because the card is itself a link. In both places the rendered location SHALL stay on the line it belongs to — it SHALL NOT introduce a block, a line break, or a heading — SHALL wrap rather than overflow on a narrow screen, and SHALL leave no stray middle dot when the location is absent.

#### Scenario: Linked place on the information screen
- **WHEN** a tournament whose location is `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)` is opened
- **THEN** the identity line reads date · ZŠ Bílá · qualification, with `ZŠ Bílá` a link opening in a new tab, and no markup characters visible

#### Scenario: Same place on a home card
- **WHEN** the same tournament is listed on Fencer Home
- **THEN** the bold date-and-place line reads date · ZŠ Bílá as text, and selecting anywhere on the card still opens the tournament

#### Scenario: Absent location leaves no separator
- **WHEN** a listed tournament has no location
- **THEN** the date stands alone on its line with no middle dot before or after it, on the card and on the information screen alike
