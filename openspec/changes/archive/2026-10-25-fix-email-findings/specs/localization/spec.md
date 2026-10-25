## MODIFIED Requirements

### Requirement: Fully localized from the start
All user-facing text — UI, emails, generated documents, and validation messages — SHALL be externalized in locale resources. English SHALL be the default UI locale and the UI's fallback, and both English and Czech SHALL be complete in the UI at launch; additional languages SHALL be addable without code changes; missing keys SHALL fall back to the default locale. Backend-generated text — emails and documents — SHALL fall back to Czech, the locale it is written complete in.

Validation messages are the one surface where silent fallback is not acceptable: a user is being told to fix something, in a language they may not read. Every validation code SHALL therefore have a message in every bundled locale, verified by a parity test that fails on a missing key rather than letting the default locale stand in. Validation messages SHALL interpolate their limits as parameters rather than writing them into the text, so a changed bound never requires a locale edit.

**Email text is held to the same parity.** A tournament's communication language is a promise about every message it sends. A key missing from one locale is a message, or a line inside one, that arrives in a language the fencer may not read, and nothing in the running system reports it. Every `email.*` key SHALL therefore exist in every bundled backend locale, verified by the same kind of parity test. The Czech fallback remains for a locale added later without its email text, and SHALL NOT stand in for a bundled one.

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

#### Scenario: An English tournament's confirmation
- **WHEN** a fencer registers on a tournament whose communication language is English
- **THEN** the confirmation's subject, body, summary markers, greeting and signature are all English
