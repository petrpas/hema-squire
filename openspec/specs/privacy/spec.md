# privacy Specification

## Purpose
Define how Squire states and handles personal data: the public privacy page, the notice at each point of collection, the organizer data terms a tournament owner accepts, an account holder's download of their own data, and the route for requests from people without an account.

## Requirements
### Requirement: A public privacy page states how personal data is handled
The system SHALL offer a public page, readable without an account and reachable from every screen, in every bundled language. It SHALL state the controller and a contact, each purpose with its legal basis, the categories of data, the recipients and processors, transfers outside the EU, the retention period of each category, the rights of the data subject including complaint to the supervisory authority, and the page's effective date.

It SHALL state which processing the operator controls and which the tournament's organizer controls. It SHALL state that after account deletion a name, HEMA Ratings ID, club and nationality stay on the rosters of held tournaments, why, and how to object. It SHALL NOT describe data that stays linked to a name as anonymised.

#### Scenario: A visitor reads the page
- **WHEN** a visitor without an account follows the privacy link from any screen
- **THEN** the page opens in the visitor's language and names the controller and a contact

#### Scenario: Retained rosters are disclosed
- **WHEN** a reader looks up what happens after account deletion
- **THEN** the page states that the name and HR ID stay on held rosters and how to object

### Requirement: Collection is accompanied by a notice
Every form collecting personal data SHALL show a short notice linking to the privacy page, including signup, guest registration and registration. The notice SHALL inform and SHALL NOT be a consent tick, since the processing does not rest on consent.

#### Scenario: Guest registers
- **WHEN** a visitor opens the guest registration form
- **THEN** the notice and its link are shown and nothing has to be ticked

### Requirement: A tournament owner accepts the organizer data terms
The owner of a tournament SHALL accept the current organizer data terms before using its console. The terms SHALL state that the organizer is controller for entries, payments and matching, that the operator acts as its processor, the listed sub-processors, the retention periods, and that exports are the organizer's responsibility. The system SHALL record the accepted version and the moment. A new version SHALL require acceptance again.

#### Scenario: Existing owner opens a console
- **WHEN** an owner who has not accepted the current version opens a console
- **THEN** the terms are shown in a dialog and the console is usable only after acceptance

#### Scenario: Team member is not asked
- **WHEN** a console team member who owns no tournament opens the console
- **THEN** no terms are shown

### Requirement: An account holder can download their own data
The Profile page SHALL offer a download of the account's own personal data in JSON: profile, profile audit trail, and its registrations with disciplines, extras and credited payments. The download SHALL NOT contain another person's data or any credential.

#### Scenario: Download
- **WHEN** a signed-in account asks for its data
- **THEN** a JSON file with its profile and registrations is downloaded

#### Scenario: Another person's data stays out
- **WHEN** the account's payment was made by another person
- **THEN** the payer's name and account number are absent from the file

### Requirement: Requests from people without an account have a route
The privacy page SHALL state a contact that receives mail, for access, erasure and objection requests from anyone, including a guest and a person entered by an organizer. The contact SHALL be tested for delivery before the page is published.

#### Scenario: Guest asks for erasure
- **WHEN** a guest writes to the stated contact
- **THEN** the message reaches the operator
