## MODIFIED Requirements

### Requirement: Fixed fencer number
Every row of the fencer list SHALL carry a number that identifies the fencer within the tournament. The number SHALL be allocated once, when the row first enters the tournament — by registration, by import, or by manual entry — and SHALL NOT change afterwards for any reason: not when the table is sorted, not when an earlier row is deleted or restored, not when a duplicate is merged away, and not when a further import arrives.

A number SHALL NOT be reissued. The number of a row deleted or merged away SHALL remain retired rather than passing to another fencer; a restored row SHALL come back with the number it had.

Clearing the tournament's imported content SHALL be the one exception: the numbers held by the cleared rows SHALL be released, since the tournament is asserting that those rows never existed. No number still held by a row that survives the clear SHALL be reissued.

The number SHALL be allocated in the order rows enter the tournament, which is not necessarily the order the table displays. Where an imported row states a registration moment earlier than that of rows already numbered, the table SHALL sort it into its chronological place and its number SHALL stand out of sequence there. The number counts nobody's position in the list; it names a fencer.

Every view SHALL number its rows by this number, the Import view included. No view SHALL number rows by their line in an uploaded file: a line number describes a file, and the Import view describes what the tournament imported across every file it was given. Import's numbers SHALL therefore be those of the tournament, gaps and all, where rows of other populations were numbered between them.

#### Scenario: Deletion does not renumber
- **WHEN** the organizer deletes the third row of a fifteen-row table
- **THEN** the remaining rows keep the numbers they had, and no number moves up

#### Scenario: Merge retires a number
- **WHEN** two rows are merged and the absorbed row disappears
- **THEN** the surviving row keeps its own number and the absorbed row's number is used by no one

#### Scenario: Backdated import numbers out of sequence
- **WHEN** an import brings a fencer whose registration moment precedes existing rows
- **THEN** that row is displayed among the earliest rows while carrying a number higher than theirs

#### Scenario: Import shows the tournament's numbers
- **WHEN** the organizer opens the Import view of a tournament whose imported rows are numbered three, four, seven and eight, in-app registrations holding the rest
- **THEN** those four rows are shown numbered three, four, seven and eight, and no numbering starts again at one

#### Scenario: A second upload continues the numbering
- **WHEN** a second file brings four rows to a tournament numbered one to thirty
- **THEN** they are numbered thirty-one to thirty-four, and the rows of the first file keep the numbers they had

#### Scenario: Manual entry takes the next number
- **WHEN** the organizer enters a fencer by hand into a table whose highest number is forty
- **THEN** that row is numbered forty-one, whatever registration moment it states

#### Scenario: Clearing releases the cleared numbers
- **WHEN** a tournament numbered one to thirty, of which eleven to thirty came from a file, is cleared
- **THEN** the surviving rows keep numbers one to ten and the next row entered is numbered eleven

## REMOVED Requirements

### Requirement: Import view of one batch
**Reason**: The view was defined as one upload's contents, which stopped describing what it shows. Uploads now accumulate, and a row that arrived in an earlier file is as much an imported row as one that arrived in the latest — it is on the fencer list either way, and hiding it from Import made the view a record of a file rather than of what the tournament imported.
**Migration**: Replaced by **Import view of everything imported** below, which keeps every clause about absorbed and deleted rows staying listed, and about Import owning the import controls. No behaviour is lost; the view's population widens from one batch to all of them.

## ADDED Requirements

### Requirement: Import view of everything imported
The Import view SHALL show every row the tournament has imported, from every upload, in the order the rows arrived. Each SHALL be shown as it was read, parsed, and hand-corrected. A row that a later operation has absorbed or deleted SHALL remain listed there, marked as such, rather than disappearing — the view is a record of what the tournament's files contained and how they were understood, not a list of who is competing.

A row SHALL be listed there for as long as it is imported. A later upload that does not carry it SHALL NOT remove it from the view, and neither the upload a row arrived in nor the order the uploads happened in SHALL group or separate rows there.

The Import view SHALL carry the import operation's controls; the fencer list SHALL NOT.

#### Scenario: Absorbed row stays visible
- **WHEN** deduplication merges an imported row into an in-app registration
- **THEN** the row remains in the Import view marked as absorbed, and is gone from the fencer list

#### Scenario: Rows of every upload listed together
- **WHEN** the organizer has uploaded three files and opens the Import view
- **THEN** the rows of all three are listed together in arrival order, with nothing marking where one upload ended and the next began

#### Scenario: An issued row is still an imported row
- **WHEN** an imported row has been issued a registration
- **THEN** it is still listed in the Import view, with its number and its parse problems

#### Scenario: Import controls belong to Import
- **WHEN** the organizer opens the Fencers tab
- **THEN** no file upload is offered there
