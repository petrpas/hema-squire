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
