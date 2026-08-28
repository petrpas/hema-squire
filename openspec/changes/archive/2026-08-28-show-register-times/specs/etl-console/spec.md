## ADDED Requirements

### Requirement: Registration moment in the fencer table
The console's fencer table SHALL state each row's registration moment as a day
and a clock time together, never as a day alone. The clock SHALL be shown on
the 24-hour scale to the minute; seconds SHALL NOT be shown.

The moment SHALL be read in the tournament's own zone — the same zone every
other date and time on that tournament's timeline is read in — so that two
organizers in different places read one registration as the same instant. A
registration moment that carries no zone of its own, as an imported row's does,
SHALL be shown as the wall clock it states, unshifted; it SHALL NOT be
reinterpreted as an instant in the reader's zone or the tournament's.

A row with no registration moment SHALL keep the em dash the table uses for an
absent value. The column SHALL be set in tabular numerals so the moments align
down the column.

#### Scenario: Registration moment carries a zone
- **WHEN** a registration recorded at 15:32 in the tournament's zone is shown in the fencer table
- **THEN** its cell states that day and `15:32`, whatever zone the organizer's browser sits in

#### Scenario: Two registrations on one day
- **WHEN** two fencers registered on the same day, one in the morning and one in the evening
- **THEN** their cells differ by their clock times, and the order the table is sorted in is visible in the column

#### Scenario: Imported row states a bare local time
- **WHEN** an imported row's registration time arrives as a date and time without a zone or offset
- **THEN** its cell states that same date and time, shifted by no zone conversion

#### Scenario: Row without a registration moment
- **WHEN** a row carries no registration moment
- **THEN** its cell shows the em dash, not a fallback date or an empty cell
