## ADDED Requirements

### Requirement: Account creation with HR binding
The system SHALL let a fencer create a portable account and bind it to a HEMA Ratings profile during creation: search the fighters index by name, present candidate profiles (name, nationality, club), and record the confirmed hr_id. Profile fields SHALL be prefilled from the confirmed profile, with the HR canonical name as the display name.

#### Scenario: Fencer confirms an HR profile
- **WHEN** a fencer creates an account and selects one of the candidate HR profiles
- **THEN** the account stores the hr_id and the HR canonical name, nationality, and club
- **AND** the fencer may adjust email and club before saving

#### Scenario: Fencer has no HR profile
- **WHEN** a fencer declares they have no HEMA Ratings profile
- **THEN** the account is created with an empty hr_id
- **AND** the account can be bound to an HR profile later without losing history

### Requirement: One account per HR identity
The system SHALL prevent two accounts from binding the same hr_id.

#### Scenario: hr_id already bound
- **WHEN** account creation attempts to bind an hr_id already bound to an existing account
- **THEN** the binding is rejected and the fencer is directed to account recovery

### Requirement: Portable profile across tournaments
Fencer accounts SHALL be global, not tournament-scoped, and reusable to register for any tournament in the deployment. Profile changes SHALL be audited.

#### Scenario: Returning fencer registers for a new tournament
- **WHEN** an existing fencer opens registration for another tournament
- **THEN** the registration is prefilled from the account profile without re-entering identity data
