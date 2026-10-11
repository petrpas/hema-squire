## ADDED Requirements

### Requirement: Tournament short code
A tournament MAY carry a short code of one to three visible characters, set by its organizer in the tournament settings under the label "Zkratka" with a help hint stating it is shown where the tournament has no logo. It is optional and not part of mandatory setup.

The field SHALL be prefilled with the monogram derived from the tournament's display name, and SHALL be stored only when the organizer enters a value that differs from it; a stored value SHALL be trimmed. Clearing the field SHALL remove the stored value and return the tournament to the derived monogram, which follows later renames. A value longer than three characters, or empty after trimming while being stored, SHALL be rejected with a field error that states the limit.

#### Scenario: Untouched field stores nothing
- **WHEN** an organizer saves settings without changing the prefilled short code
- **THEN** no short code is stored, and renaming the tournament later changes what its plate reads

#### Scenario: Organizer sets a code
- **WHEN** the organizer enters `PDM` and saves
- **THEN** the short code `PDM` is stored

#### Scenario: Too long
- **WHEN** the organizer enters `PRAHA`
- **THEN** the field shows an error stating the three-character limit and nothing is saved

#### Scenario: Clearing restores derivation
- **WHEN** the organizer clears a stored short code and saves
- **THEN** no short code is stored and the plate shows the derived monogram again
