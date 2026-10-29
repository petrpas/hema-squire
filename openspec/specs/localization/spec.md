# localization Specification

## Purpose
Externalize all user-facing text in locale resources, with English the default UI locale, Czech complete at launch, and a distinction between tournament communication language and UI language.
## Requirements
### Requirement: Fully localized from the start
All user-facing text — UI, emails, generated documents, and validation messages — SHALL be externalized in locale resources. English SHALL be the default UI locale and the UI's fallback, and both English and Czech SHALL be complete in the UI at launch; additional languages SHALL be addable without code changes; missing keys SHALL fall back to the default locale. Backend-generated text — emails and documents — SHALL fall back to Czech, the locale it is written complete in.

Validation messages are the one surface where silent fallback is not acceptable: a user is being told to fix something, in a language they may not read. Every validation code SHALL therefore have a message in every bundled locale, verified by a parity test that fails on a missing key rather than letting the default locale stand in. Validation messages SHALL interpolate their limits as parameters rather than writing them into the text, so a changed bound never requires a locale edit.

**Email text is held to the same parity.** A message's language is a promise to the person reading it. A key missing from one locale is a message, or a line inside one, that arrives in a language the fencer may not read, and nothing in the running system reports it. Every `email.*` key SHALL therefore exist in every bundled backend locale, verified by the same kind of parity test. The Czech fallback remains for a locale added later without its email text, and SHALL NOT stand in for a bundled one.

#### Scenario: Adding English later
- **WHEN** an English locale is added
- **THEN** the application offers English fully from locale resources, with Czech fallback for untranslated keys

#### Scenario: A validation message missing from a bundled locale
- **WHEN** a validation code has a message in one bundled locale but not another
- **THEN** the locale parity test fails, naming the missing key and locale, rather than the message falling back

#### Scenario: A limit stated in a message
- **WHEN** a validation message states a maximum length or a permitted range
- **THEN** the figure arrives as an interpolated parameter and no locale file contains it as literal text

#### Scenario: An email key missing from a bundled locale
- **WHEN** an `email.*` key exists in the Czech backend locale but not in the English one
- **THEN** the locale parity test fails, naming the missing key and locale

#### Scenario: An English reader's confirmation
- **WHEN** a fencer whose language is English registers on a tournament whose communication language is Czech
- **THEN** the confirmation's subject, body, summary markers, greeting and signature are all English

### Requirement: Communication language vs UI language
A message about a tournament SHALL be written in **its recipient's language** — the language stored on the fencer record it is addressed to — when that language is a bundled backend locale, and in the tournament's communication language otherwise. Every piece of Squire's text inside one message, including any line composed before the send and handed to it, SHALL be in that one language. A send addressed to more than one person SHALL resolve the language for each recipient separately. Text the organizer authored — the tournament's name, its description, discipline names — SHALL be stated as written, in whatever language it was written in. The console and fencer-facing UI language SHALL follow the user's preference. Mail about an account rather than a tournament (signup verification, password reset, password changed) SHALL use the account's language, as before.

The tournament's communication language SHALL be an editable setting of the tournament. A new tournament SHALL take the UI language of the organizer who creates it, and the creation dialog SHALL NOT offer it. Changing it SHALL govern mail sent from then on and SHALL NOT rewrite mail already sent or the language already stored on any fencer record.

#### Scenario: Czech tournament, foreign organizer
- **WHEN** a tournament is configured with Czech communication and an organizer prefers another UI language
- **THEN** the organizer's console renders in their preferred language, and fencers without a bundled language of their own receive Czech mail

#### Scenario: The recipient's language wins
- **WHEN** a Czech tournament mails a fencer whose account language is English
- **THEN** the message is in English, with the tournament's name and discipline names as the organizer wrote them

#### Scenario: An unbundled recipient language falls back
- **WHEN** a fencer record carries a language no bundled backend locale provides
- **THEN** the message is in the tournament's communication language

#### Scenario: Two recipients, two languages
- **WHEN** a substitution is mailed to the fencer replaced, whose language is Czech, and the one replacing them, whose language is English
- **THEN** each receives the message in their own language

#### Scenario: A composed line follows the message
- **WHEN** a team promotion notice is sent to an English-reading entering fencer of a Czech tournament
- **THEN** the line naming the team and its discipline is in English like the rest of the message

#### Scenario: New tournament takes the creator's language
- **WHEN** an organizer whose UI language is English creates a tournament
- **THEN** its communication language is English, and the creation dialog asked nothing about it

#### Scenario: Changing the language later
- **WHEN** the organizer changes a tournament's communication language from Czech to English after mail has been sent
- **THEN** mail sent afterwards falls back to English, and no sent message and no stored fencer language is changed

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

### Requirement: A visitor without an account reads English
The application SHALL render in English for every visitor who is not signed in — public tournament pages, the picker, and anything else reachable without an account — from the first paint, without a swap after one. Signing out SHALL return the UI to English, so a preference belonging to a session that has ended does not outlive it. Browser-detected locale SHALL NOT select the anonymous language.

#### Scenario: Public page opened without an account
- **WHEN** a visitor with no account opens a public tournament page
- **THEN** the page renders in English on its first paint

#### Scenario: Signing out drops the account's language
- **WHEN** a fencer whose account prefers Czech signs out
- **THEN** the UI returns to English rather than staying in Czech

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

### Requirement: A fencer record created without a language takes the tournament's
A fencer record created on a tournament's behalf without a language of its own — a substitute entered by the organizer, a row imported from a table that states no language or one no bundled locale provides — SHALL be given the tournament's communication language at the moment it is created. A record created from a person's own choice (account signup, the guest form) SHALL keep that choice, and an imported row stating a bundled language SHALL keep it.

#### Scenario: Substitute on a Czech tournament
- **WHEN** the organizer substitutes a new person into a registration on a tournament whose communication language is Czech
- **THEN** the fencer record created for them carries Czech, and the substitution message to them is in Czech

#### Scenario: Import without a language column
- **WHEN** a table with no language column is imported into an English tournament
- **THEN** every fencer record it creates carries English

#### Scenario: Import stating a language
- **WHEN** an imported row states Czech on an English tournament
- **THEN** the fencer record it creates carries Czech

