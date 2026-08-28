## ADDED Requirements

### Requirement: Readable manual-edits log
Every entry in the manual-edits log SHALL be readable without knowledge of the
system's internals. An entry SHALL identify its row as the table does — by the
row's number in the current table and the fencer's name — and never by the row's
internal id. A field SHALL be named by its column label. A change that has no
column of its own SHALL be phrased as a sentence rather than a field assignment:
a deletion reads as a deletion, a restoration is absent (it cancels), and a
merge reads as a merge into the named surviving row. Values SHALL be rendered as
the table renders them, with an empty value shown as a dash.

#### Scenario: Deleted row
- **WHEN** the organizer deletes the row of a withdrawn fencer
- **THEN** the log entry names the row by its number and the fencer's name and states that the row is deleted, in place of a `_deleted` field assignment

#### Scenario: Field edit
- **WHEN** the organizer corrects a fencer's club
- **THEN** the log entry names the row and reads as the club's column label with the old and new value

#### Scenario: Merged row
- **WHEN** the organizer confirms a duplicate merge
- **THEN** the absorbed row's entry states that it was merged into the surviving row, named by its number and fencer name

#### Scenario: Both languages
- **WHEN** the console is read in Czech
- **THEN** every part of an entry — field labels, the deletion and merge sentences, and rendered values — is Czech
