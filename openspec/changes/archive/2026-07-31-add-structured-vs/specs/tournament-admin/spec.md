## ADDED Requirements

### Requirement: Variable symbol series
Each tournament SHALL carry a VS year and a VS series, which together form the prefix of every variable symbol it issues. The VS year SHALL be taken from the tournament's date when the series is assigned, so that an event held in January belongs to that January's year even when it is created and sells out during the preceding year. The VS series SHALL be an integer from 1 to 99 and SHALL be unique among the tournaments sharing a VS year.

The series SHALL be assigned automatically when the tournament is created, as the lowest value not already taken for its year. The organizer SHALL be able to change it in the Setup phase, and SHALL be shown the resulting variable-symbol prefix so they can see what payers will quote. Both the series and its year SHALL become read-only once the tournament has its first registration; from that point a change to the tournament's date SHALL NOT reassign either, and no already-issued variable symbol SHALL be renumbered. A tournament whose date later moves into another year therefore keeps its original prefix, which is correct because nothing routes on the prefix.

Assigning a series SHALL fail with a clear message naming the exhausted year when every value from 1 to 99 is already taken for that year, rather than assigning a duplicate or an out-of-range value.

#### Scenario: Series assigned on creation
- **WHEN** an organizer creates the first tournament dated in 2026
- **THEN** it is assigned VS year 2026 and series 1, and its Setup shows the variable-symbol prefix 2601

#### Scenario: Lowest free series taken
- **WHEN** a new tournament is created for a year in which series 1 and 3 are taken
- **THEN** it is assigned series 2

#### Scenario: Series taken from the tournament date, not the creation date
- **WHEN** an organizer creates a tournament in November 2026 for a date in January 2027
- **THEN** its VS year is 2027 and its series is the lowest free value among 2027 tournaments

#### Scenario: Series editable before the first registration
- **WHEN** the organizer changes the series in Setup on a tournament that has no registrations, to a value free in its year
- **THEN** the change is accepted and subsequent variable symbols use the new prefix

#### Scenario: Series collision rejected
- **WHEN** the organizer sets a series already used by another tournament in the same year
- **THEN** the change is rejected with a message naming the conflict

#### Scenario: Series frozen after the first registration
- **WHEN** the organizer attempts to change the series on a tournament that already has a registration
- **THEN** the change is rejected and the existing prefix is retained

#### Scenario: Date change after registrations does not renumber
- **WHEN** a tournament with registrations has its date moved from December 2026 into January 2027
- **THEN** its VS year and series are unchanged, every issued variable symbol keeps its value, and newly issued symbols continue on the same prefix

#### Scenario: Year exhausted
- **WHEN** a tournament is created for a year that already holds 99 tournaments
- **THEN** creation is refused with a message naming the exhausted year
