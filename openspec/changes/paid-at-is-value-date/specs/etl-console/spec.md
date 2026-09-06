## ADDED Requirements

### Requirement: Dates in the Payments phase table are read in the tournament's zone
The Payments phase's fencer table states two moments — when a reservation
expires and when its registration was paid. Both SHALL be read in the
tournament's own zone, the same zone the registration moment in the fencer table
is already read in, so that two organizers in different places read one
registration the same way.

The paid date SHALL be shown as a day alone. What it states is the day the money
arrived (`payments`), which a statement gives without a clock, and printing an
hour the bank never stated would invent precision. The expiry SHALL keep the form
it has.

A registration with no paid date SHALL keep the em dash the table uses for an
absent value.

#### Scenario: A reader in another zone
- **WHEN** a registration paid on the 3rd in the tournament's zone is read by an organizer whose browser sits west of it
- **THEN** the cell states the 3rd

#### Scenario: An expiry late in the local evening
- **WHEN** a reservation expires at 23:00 in the tournament's zone and is read by an organizer whose browser sits east of it
- **THEN** the cell states the day the expiry falls on where the tournament is held, not the following day

#### Scenario: An unpaid registration
- **WHEN** a reservation has not been paid
- **THEN** its paid cell shows the em dash, not a fallback date
