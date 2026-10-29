## MODIFIED Requirements

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

## ADDED Requirements

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
