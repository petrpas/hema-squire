# localization Specification

## Purpose
Externalize all user-facing text in locale resources, with Czech complete at launch and a distinction between tournament communication language and UI language.

## Requirements

### Requirement: Fully localized from the start
All user-facing text — UI, emails, generated documents — SHALL be externalized in locale resources. Czech SHALL be complete at launch; additional languages SHALL be addable without code changes; missing keys SHALL fall back to the default locale.

#### Scenario: Adding English later
- **WHEN** an English locale is added
- **THEN** the application offers English fully from locale resources, with Czech fallback for untranslated keys

### Requirement: Communication language vs UI language
Emails to fencers SHALL use the tournament's communication language. The console and fencer-facing UI language SHALL follow the user's preference.

#### Scenario: Czech tournament, foreign organizer
- **WHEN** a tournament is configured with Czech communication and an organizer prefers another UI language
- **THEN** fencers receive Czech emails while the organizer's console renders in their preferred language once available

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
