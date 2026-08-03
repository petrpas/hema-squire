## MODIFIED Requirements

### Requirement: Fully localized from the start
All user-facing text — UI, emails, generated documents, and validation messages — SHALL be externalized in locale resources. Czech SHALL be complete at launch; additional languages SHALL be addable without code changes; missing keys SHALL fall back to the default locale.

Validation messages are the one surface where silent fallback is not acceptable: a user is being told to fix something, in a language they may not read. Every validation code SHALL therefore have a message in every bundled locale, verified by a parity test that fails on a missing key rather than letting the default locale stand in. Validation messages SHALL interpolate their limits as parameters rather than writing them into the text, so a changed bound never requires a locale edit.

#### Scenario: Adding English later
- **WHEN** an English locale is added
- **THEN** the application offers English fully from locale resources, with Czech fallback for untranslated keys

#### Scenario: A validation message missing from a bundled locale
- **WHEN** a validation code has a message in one bundled locale but not another
- **THEN** the locale parity test fails, naming the missing key and locale, rather than the message falling back

#### Scenario: A limit stated in a message
- **WHEN** a validation message states a maximum length or a permitted range
- **THEN** the figure arrives as an interpolated parameter and no locale file contains it as literal text
