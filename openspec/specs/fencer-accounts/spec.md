# fencer-accounts Specification

## Purpose
Give fencers portable, globally scoped accounts bound to HEMA Ratings identities, reusable across tournaments.

## Requirements

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

### Requirement: Non-exclusive HR profile claims
The system SHALL allow multiple accounts to claim the same HEMA Ratings profile — a claim to an already-claimed profile SHALL NOT be rejected at signup or Profile binding. Wherever HR candidate profiles are presented for claiming, profiles already claimed by another account SHALL be marked with a non-blocking notice so the fencer can recognize they may already have an account. The admin accounts list SHALL flag accounts whose hr_id is shared with at least one other account; resolution remains the existing administrative unbinding.

#### Scenario: Claiming an already-claimed profile succeeds
- **WHEN** a fencer confirms an HR profile that another account has already claimed, at signup or on the Profile page
- **THEN** the claim succeeds exactly as for an unclaimed profile

#### Scenario: Fencer warned about an existing claim
- **WHEN** HR candidate profiles are listed and one of them is already claimed by another account
- **THEN** that candidate carries a visible notice that it is already claimed, and the fencer may still confirm it

#### Scenario: Admin sees duplicate claims
- **WHEN** an Admin opens the accounts list while two accounts share the same hr_id
- **THEN** both accounts are flagged as sharing their HR profile, and the Admin can resolve the duplicate by unbinding the wrong account

### Requirement: Portable profile across tournaments
Fencer accounts SHALL be global, not tournament-scoped, and reusable to register for any tournament in the deployment. Profile changes SHALL be audited.

#### Scenario: Returning fencer registers for a new tournament
- **WHEN** an existing fencer opens registration for another tournament
- **THEN** the registration is prefilled from the account profile without re-entering identity data

### Requirement: Administrative HR unbinding
An Admin SHALL be able to unbind a wrongly linked HEMA Ratings profile from an account: the hr_id is cleared while profile fields keep their current values, and the change is recorded in the profile audit trail. The account can then be bound to the correct profile through the existing binding flow. Fencer-initiated rebinding SHALL remain rejected — the binding stays write-once from the fencer's side.

#### Scenario: Admin unbinds a wrong profile
- **WHEN** an Admin clears the hr_id of an account linked to the wrong HEMA Ratings profile
- **THEN** the hr_id is empty, the unbinding is audited, and the fencer can bind the correct profile

#### Scenario: Fencer still cannot rebind
- **WHEN** a fencer whose account already has an hr_id attempts to bind a different profile
- **THEN** the request is rejected as before
