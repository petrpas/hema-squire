## MODIFIED Requirements

### Requirement: Per-account UI language preference
Each account SHALL store a preferred UI language, chosen at signup from the implemented localizations (derived from the bundled locale resources, not a hardcoded list) and editable on the Profile page. The application SHALL render in the account's language after login and immediately after signup. The registration window's language selector SHALL default to English on first render; changing the selection SHALL switch the window's own language at once. Accounts without an explicit preference SHALL default to English.

#### Scenario: Signup defaults to English
- **WHEN** a fencer opens the registration window without changing the language selector
- **THEN** the window renders in English and the account is created with English as its preferred language

#### Scenario: English chosen at signup
- **WHEN** a fencer selects English in the registration window and signs up
- **THEN** the application renders in English immediately and again on every later login

#### Scenario: Language changed on the Profile page
- **WHEN** a fencer changes the preferred language on the Profile page
- **THEN** the UI switches to the new language and the preference persists for future logins

#### Scenario: Selector follows implemented localizations
- **WHEN** a new locale resource file is added to the application
- **THEN** the registration window and Profile page language selectors offer it without code changes

## ADDED Requirements

### Requirement: Sign-in screen renders in English
The sign-in (login) screen SHALL always render in English, independent of the browser's detected locale, any previously stored account or session language, or the signup form's language selection. It has no language selector of its own.

#### Scenario: Sign-in ignores a previously stored Czech preference
- **WHEN** a visitor whose last session had the UI in Czech (or any other locale) returns to the sign-in screen while logged out
- **THEN** the sign-in screen renders in English

#### Scenario: Sign-in unaffected by an in-progress signup language change
- **WHEN** a visitor switches the signup form's language selector to a non-English locale and then navigates back to sign-in
- **THEN** the sign-in screen still renders in English
