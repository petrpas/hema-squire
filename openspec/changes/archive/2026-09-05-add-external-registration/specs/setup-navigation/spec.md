## ADDED Requirements

### Requirement: Setup offers no section for a registration Squire does not run
WHEN a tournament's registrations are kept by the organizer (`registration-ownership`), Setup SHALL NOT offer the sections that govern a registration Squire runs and no one operates on such a tournament — in particular the reminder day, which schedules notice about an obligation Squire neither sets nor chases.

The line SHALL be drawn at **who acts on a setting**, not at who might read it. A setting the organizer still acts on SHALL remain offered even where Squire does nothing with it: prices price the export, the totals and what the organizer charges; the seating deadline is about seats; the registration-opens and registration-closes dates still state when the organizer's own registration runs, and SHALL remain editable although they no longer gate anything, as fixed by `tournament-admin`.

A hidden section SHALL follow the treatment `setup-navigation` already fixes for a section the tournament's mode does not offer: its stored values SHALL be retained unchanged, and it SHALL become available again if the tournament's registrations return to Squire's keeping.

The external registration address SHALL be offered on such a tournament and SHALL be marked as a mandatory item, since it is what publication now depends on.

#### Scenario: The reminder day is not offered
- **WHEN** the organizer opens Setup on a tournament whose registrations they keep
- **THEN** no reminder day is offered

#### Scenario: The timeline dates remain
- **WHEN** the same organizer opens the timeline
- **THEN** the registration-opens and registration-closes dates are offered and editable, stating when their own registration runs

#### Scenario: Hidden values survive the switch back
- **WHEN** a tournament carrying a reminder day is switched to organizer-kept and later back to Squire-kept
- **THEN** the reminder day holds the value it held before, with nothing to re-enter

#### Scenario: The external address is offered and marked
- **WHEN** the organizer opens Setup on an organizer-kept tournament with no external registration address
- **THEN** the address is offered and reported among the mandatory items still to supply
