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

### Requirement: Sign-in screen renders in English
The sign-in (login) screen SHALL always render in English, independent of the browser's detected locale, any previously stored account or session language, or the signup form's language selection. It has no language selector of its own.

#### Scenario: Sign-in ignores a previously stored Czech preference
- **WHEN** a visitor whose last session had the UI in Czech (or any other locale) returns to the sign-in screen while logged out
- **THEN** the sign-in screen renders in English

#### Scenario: Sign-in unaffected by an in-progress signup language change
- **WHEN** a visitor switches the signup form's language selector to a non-English locale and then navigates back to sign-in
- **THEN** the sign-in screen still renders in English

### Requirement: Money rendered from amount and currency
Monetary values SHALL be rendered by a single formatting function per surface — one in the frontend, one for emails and generated documents — taking the amount and a currency code and returning the localized string, with the unit drawn from a currency-symbol table. Locale resources SHALL NOT contain a currency unit baked into message text or field labels; labels that need to name a currency SHALL take it as an interpolated parameter. Adding a currency SHALL require extending the symbol table only, with no change to locale resources.

#### Scenario: Total rendered in the tournament's currency
- **WHEN** a total of 1750 is rendered for a CZK tournament and the same amount for a EUR tournament
- **THEN** each renders with its own unit from the symbol table using one shared message key

#### Scenario: Field labels take the currency as a parameter
- **WHEN** a price field label is rendered for a tournament
- **THEN** the label names that tournament's currency through interpolation rather than through a currency-specific message key

#### Scenario: No currency literals in locale resources
- **WHEN** the locale resources and email templates are inspected
- **THEN** no currency unit or code appears as literal text in any message value

#### Scenario: Email amounts follow the communication language
- **WHEN** a confirmation email is generated for a tournament whose communication language is Czech
- **THEN** the amount is formatted for Czech with the tournament's currency unit, from the shared email formatter
