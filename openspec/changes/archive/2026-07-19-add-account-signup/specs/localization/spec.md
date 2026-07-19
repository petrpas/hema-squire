## ADDED Requirements

### Requirement: Per-account UI language preference
Each account SHALL store a preferred UI language, chosen at signup from the implemented localizations (derived from the bundled locale resources, not a hardcoded list) and editable on the Profile page. The application SHALL render in the account's language after login and immediately after signup. Changing the language selection inside the registration window SHALL switch the window's own language at once. Accounts without an explicit preference SHALL default to Czech.

#### Scenario: English chosen at signup
- **WHEN** a fencer selects English in the registration window and signs up
- **THEN** the application renders in English immediately and again on every later login

#### Scenario: Language changed on the Profile page
- **WHEN** a fencer changes the preferred language on the Profile page
- **THEN** the UI switches to the new language and the preference persists for future logins

#### Scenario: Selector follows implemented localizations
- **WHEN** a new locale resource file is added to the application
- **THEN** the registration window and Profile page language selectors offer it without code changes
