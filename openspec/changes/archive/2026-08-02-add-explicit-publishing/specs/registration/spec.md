## MODIFIED Requirements

### Requirement: Registration availability
The system SHALL accept a registration only when the tournament has been published and the current date is within the registration window: on or after the registration-opens date when set, and on or before the registration-closes date when set (otherwise up to the tournament date). When registration is unavailable, the rejection SHALL carry a distinct reason — not yet published, not yet open, or closed — so clients can present it (with the opening date where applicable). The gate SHALL NOT re-check mandatory setup completeness: publication already guarantees it, and a published tournament cannot be edited into incompleteness.

#### Scenario: Not published
- **WHEN** a fencer attempts to register for a tournament that has not been published
- **THEN** the registration is rejected with the not-yet-published reason, whether or not its mandatory setup is complete

#### Scenario: After close
- **WHEN** a fencer attempts to register after the registration-closes date
- **THEN** the registration is rejected with the closed reason

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published, non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set, and its local currency — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Subtitle and logo carried when set
- **WHEN** a listed tournament has a subtitle and a logo
- **THEN** its list entry carries the subtitle and a reference to its logo, and entries without them omit those fields

#### Scenario: Currency carried
- **WHEN** a fencer requests the list
- **THEN** each entry carries the tournament's local currency so amounts render without a hardcoded unit

#### Scenario: Unpublished excluded
- **WHEN** a tournament has not been published, or it is cancelled
- **THEN** it is absent from the fencer-facing list

#### Scenario: Setup-complete draft still excluded
- **WHEN** a tournament's mandatory setup is complete but nobody has published it
- **THEN** it is absent from the fencer-facing list
