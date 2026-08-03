## ADDED Requirements

### Requirement: Discipline dialog reopens on the discipline's own values
WHEN the discipline dialog is reopened on an existing discipline, it SHALL show that discipline's stored name and stored slug as they are, and SHALL NOT replace either with a value derived from its classification. Derivation governs a discipline being added, not one being reopened: on a reopened discipline it SHALL resume only for a field the organizer has since cleared or for a field that changes because the organizer alters the kind or the classification in this dialog session.

Confirming a reopened dialog without touching its name or slug SHALL therefore leave both exactly as they were stored, and the tab SHALL count no unsaved change on their account.

#### Scenario: Reopened dialog states the stored values
- **WHEN** the organizer reopens the dialog on a discipline whose name and slug they had overridden as "Top bracket" and `LS-A`
- **THEN** the dialog shows "Top bracket" and `LS-A`, not the name and slug its classification would generate

#### Scenario: Reopening and confirming changes nothing
- **WHEN** the organizer reopens a discipline's dialog and confirms it without editing a field
- **THEN** the row's name and slug are unchanged and the tab reports no further unsaved changes than before

#### Scenario: Classification change still moves the derived fields
- **WHEN** the organizer reopens a discipline that carries generated identity and changes its weapon
- **THEN** the name and the slug follow the new weapon, exactly as they do while adding a discipline

#### Scenario: An overridden field is not recaptured by derivation
- **WHEN** the organizer reopens a discipline whose slug they had overridden and changes its gender
- **THEN** the name follows the new classification and the overridden slug is left as stored
