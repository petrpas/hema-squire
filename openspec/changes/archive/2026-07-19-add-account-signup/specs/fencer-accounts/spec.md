## MODIFIED Requirements

### Requirement: Account creation with HR binding
The system SHALL offer a self-service registration window, reachable from the login screen, with the fields: email, password, name, and preferred UI language (selected from the implemented localizations). The window SHALL include an optional HEMA Ratings step: search the fighters index by name, present candidate profiles (name, nationality, club), and record the confirmed hr_id at signup — the HR canonical name SHALL become the account display name and be visible in the form before submitting, and a confirmed profile SHALL be clearable before submit. The step SHALL be skippable; an account created without it can be bound later from the Profile page. On successful signup the account SHALL be active immediately (no email verification) and the fencer SHALL be logged in and land on Fencer Home. A duplicate email SHALL be rejected with a clear message.

#### Scenario: Fencer signs up without HEMA Ratings
- **WHEN** a fencer submits the registration window with email, password, name, and a language, skipping the HR step
- **THEN** the account is created with the typed name and chosen language, and the fencer is logged in and lands on Fencer Home

#### Scenario: Fencer confirms an HR profile
- **WHEN** a fencer uses the HR step and confirms one of the candidate profiles before submitting
- **THEN** the account stores the hr_id and the HR canonical name, nationality, and club
- **AND** the form showed the canonical name as the account name before submission

#### Scenario: Duplicate email rejected
- **WHEN** a fencer submits the registration window with an email that already has an account
- **THEN** the signup is rejected with a message that the email is already registered

#### Scenario: Fencer has no HR profile
- **WHEN** a fencer declares they have no HEMA Ratings profile
- **THEN** the account is created with an empty hr_id
- **AND** the account can be bound to an HR profile later without losing history
