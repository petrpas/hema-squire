## ADDED Requirements

### Requirement: The Profile page has a Privacy tab
The Profile page SHALL be split into two tabs, `Profile` and `Privacy`, the first selected by default. The Privacy tab SHALL have an address of its own, so that the privacy notice and a message can lead to it. It SHALL hold everything about the account's personal data in one place:

- who is responsible and the contact for requests, with a link to the full privacy notice (`privacy`);
- the download of the account's own data (`privacy`, An account holder can download their own data);
- for an account that has accepted the organizer data terms or owes them, which version it accepted and when, or that acceptance is due, with the terms to read;
- account deletion, opening a dialog that states the impact and asks for the password. While a deletion is pending the tab SHALL state the date it takes effect and SHALL offer withdrawal.

The Profile tab SHALL hold the account, role and HEMA Ratings sections and none of the above.

#### Scenario: Pending deletion
- **WHEN** an account with a pending deletion opens the Privacy tab
- **THEN** the date is stated and withdrawal is offered

#### Scenario: Reached by address
- **WHEN** someone follows a link to the Profile page's Privacy tab
- **THEN** the Privacy tab is selected and shows the download and deletion

#### Scenario: The Profile tab stays about the account
- **WHEN** an account opens the Profile page
- **THEN** the Profile tab is selected and neither the download nor deletion is on it
