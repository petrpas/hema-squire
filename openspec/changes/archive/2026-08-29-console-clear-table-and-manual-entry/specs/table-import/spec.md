## ADDED Requirements

### Requirement: Clearing the tournament's imported content
The organizer MAY clear everything the tournament has imported. Clearing SHALL remove every uploaded batch, every source row those batches carried, every decision taken about those rows — parses, match proposals, merge proposals, dedup classifications — and every manual correction recorded against them. The removal SHALL be a deletion of the data, not a marking of it: nothing cleared SHALL remain visible, restorable, or countable anywhere in the console afterwards, and the tournament SHALL read as one that never imported anything.

Clearing SHALL leave every row that did not come from a file untouched. In-app registrations and manually entered rows SHALL keep their content, their notes, their fixed numbers, and the decisions and edits recorded about them.

Where a correction or a merge decision names both an imported row and a row of another population, clearing SHALL remove that decision too — it was taken about a row that no longer exists — while leaving the other row itself in place.

Clearing SHALL NOT be offered as an undo of a single upload: it removes all imported content at once, including batches superseded by later uploads, so that clearing never leaves an older file's rows behind to become the table again.

#### Scenario: Wrong file removed altogether
- **WHEN** the organizer uploads the wrong table and then clears
- **THEN** the Import view is empty, no imported row appears on the fencer list, and the Import log is empty

#### Scenario: Registrations survive a clear
- **WHEN** a tournament with twelve in-app registrations and an imported batch is cleared
- **THEN** the twelve registrations remain on the fencer list with their numbers and their edit history unchanged

#### Scenario: Superseded batches go too
- **WHEN** the organizer has uploaded three successive files and clears
- **THEN** no rows of any of the three remain, and the Import view does not fall back to an earlier upload

#### Scenario: Re-import after a clear starts clean
- **WHEN** the organizer clears and then uploads the correct file
- **THEN** every row of the new file is parsed afresh, with no decision or correction carried over from the cleared content

#### Scenario: Merge decision naming a cleared row
- **WHEN** an imported row had been merged into an in-app registration and the tournament is cleared
- **THEN** the merge is gone along with the imported row, and the registration stands on its own, unmerged

### Requirement: Clearing is warned about and irreversible
Clearing SHALL be confirmed before it happens. The confirmation SHALL state what is about to be removed — how many rows, from how many uploaded files — and SHALL state plainly that the removal cannot be undone. It SHALL be distinguishable from the reversible row deletion the table already offers, which removes a row from view while keeping it restorable.

Dismissing the confirmation SHALL leave everything as it was. Confirming SHALL be final: no undo action, no restore, and no entry in any log SHALL bring the cleared content back.

#### Scenario: Confirmation states the cost
- **WHEN** the organizer activates the clear action on a tournament holding forty imported rows from two files
- **THEN** the confirmation names the forty rows and the two files, and says the removal cannot be undone

#### Scenario: Dismissed confirmation changes nothing
- **WHEN** the organizer dismisses the confirmation
- **THEN** the imported rows, decisions and corrections all remain exactly as before

#### Scenario: No undo after confirming
- **WHEN** the organizer confirms the clear and then looks for a way back
- **THEN** none is offered, and the manual-edits log holds no entry that restores the cleared content

#### Scenario: Nothing to clear
- **WHEN** the organizer opens Import on a tournament that has imported nothing
- **THEN** the clear action is not offered
