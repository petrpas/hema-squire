## MODIFIED Requirements

### Requirement: Account creation with HR binding
The system SHALL offer a self-service registration window, reachable from the login screen, with the fields: email, password, name, and preferred UI language (selected from the implemented localizations). The window SHALL include an optional HEMA Ratings step: it SHALL reuse the form's own name field as the search query (there SHALL NOT be a second name input inside the step), search the fighters index by name, and present candidate profiles (name, nationality, club). Before a candidate is bound, the system SHALL present an explicit ownership confirmation that shows the candidate's details (name, nationality, club, HR id) and a link to that fighter's hemaratings.com profile page opening in a new browser tab, and asks the fencer to confirm the account is theirs; binding SHALL occur only on that confirmation. On confirmation the HR canonical name SHALL become the account display name and be visible in the form before submitting, and a confirmed profile SHALL be clearable before submit. When a profile is confirmed, the form SHALL show a confirmation line carrying the canonical name and the HR id (for example `HEMA Ratings profile confirmed: Petr Lukeš (8956)`). The step SHALL be skippable; an account created without it can be bound later from the Profile page. On successful signup the account SHALL be active immediately (no email verification) and the fencer SHALL be logged in and land on Fencer Home. A duplicate email SHALL be rejected with a clear message.

#### Scenario: Fencer signs up without HEMA Ratings
- **WHEN** a fencer submits the registration window with email, password, name, and a language, skipping the HR step
- **THEN** the account is created with the typed name and chosen language, and the fencer is logged in and lands on Fencer Home

#### Scenario: Name field drives the HR search
- **WHEN** a fencer with a name typed in the form opens the HR step
- **THEN** the step searches by that name without asking for the name again

#### Scenario: Explicit ownership confirmation before binding
- **WHEN** a fencer selects a candidate profile in the HR step
- **THEN** an ownership confirmation is shown with the candidate's name, nationality, club, HR id, and a hemaratings.com profile link opening in a new tab, and the profile is bound only after the fencer confirms it is theirs

#### Scenario: Fencer confirms an HR profile
- **WHEN** a fencer uses the HR step and confirms one of the candidate profiles before submitting
- **THEN** the account stores the hr_id and the HR canonical name, nationality, and club
- **AND** the form showed the canonical name as the account name before submission
- **AND** the confirmation line displayed the canonical name together with the HR id

#### Scenario: Duplicate email rejected
- **WHEN** a fencer submits the registration window with an email that already has an account
- **THEN** the signup is rejected with a message that the email is already registered

#### Scenario: Fencer has no HR profile
- **WHEN** a fencer declares they have no HEMA Ratings profile
- **THEN** the account is created with an empty hr_id
- **AND** the account can be bound to an HR profile later without losing history
