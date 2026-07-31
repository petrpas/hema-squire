## MODIFIED Requirements

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published (setup-complete), non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Subtitle and logo carried when set
- **WHEN** a listed tournament has a subtitle and a logo
- **THEN** its list entry carries the subtitle and a reference to its logo, and entries without them omit those fields

#### Scenario: Unpublished excluded
- **WHEN** a tournament's mandatory setup is incomplete or it is cancelled
- **THEN** it is absent from the fencer-facing list
