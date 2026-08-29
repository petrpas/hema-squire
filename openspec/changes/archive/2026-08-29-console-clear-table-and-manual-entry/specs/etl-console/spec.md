## ADDED Requirements

### Requirement: Manual entry of a fencer
The organizer MAY add a fencer to the fencer list by hand, without a file and without the fencer registering. The action SHALL be offered on the Fencers tab and nowhere else, and SHALL open a dialog rather than an editable blank row — a row is entered whole or not at all.

A manually entered row SHALL be a source record of the tournament in its own right, a third population beside in-app registrations and imported rows. It SHALL take a fixed number when it is entered, SHALL sort by the registration moment it states, SHALL carry its note, and SHALL travel through matching, deduplication and export exactly as an imported row does. It SHALL be editable and deletable by the same means as any other row.

A manually entered row SHALL NOT create an account for the fencer, SHALL NOT be given a variable symbol or a payment instruction, and SHALL NOT cause any mail to be sent. It states who is competing; it does not enrol them in the application.

A manually entered row SHALL NOT appear on the Import view, in any state. The Import view records what a file contained, and a manual entry came from no file.

#### Scenario: Fencer entered at the door
- **WHEN** the organizer enters a fencer by hand on the Fencers tab
- **THEN** one new row joins the fencer list, carrying a fixed number of its own, in the chronological place its registration moment gives it

#### Scenario: Manual entry absent from Import
- **WHEN** the organizer enters a fencer by hand while an imported batch is present
- **THEN** the Import view is unchanged and lists only the file's rows

#### Scenario: Manual entry is not offered on Import
- **WHEN** the organizer opens the Import tab
- **THEN** no manual entry action is offered there

#### Scenario: Manual row deduplicates like any other
- **WHEN** a manually entered fencer shares an hr_id with an imported row
- **THEN** the pair is queued for the organizer's review as a duplicate pair

#### Scenario: Manual row is editable afterwards
- **WHEN** the organizer corrects the club of a manually entered fencer in the table
- **THEN** the correction is recorded in the fencer list's manual-edits log, as it would be for any other row

#### Scenario: No account is created
- **WHEN** a fencer is entered by hand
- **THEN** no account exists for them, no confirmation mail is sent, and no payment instruction is issued

### Requirement: Manual entry fields follow the tournament's structure
The manual entry dialog SHALL offer the tournament's own structure rather than a generic fencer form. Disciplines SHALL be offered as the tournament's own offered individual disciplines, by their names; items to borrow SHALL be offered as the items the tournament lends, by their names; the afterparty SHALL be offered only where the tournament holds one. A choice the tournament does not offer SHALL NOT be presented.

Team disciplines SHALL NOT be offered in the dialog. A team is entered through the tournament's team handling, not by naming a team discipline on a fencer's row.

The dialog SHALL additionally take the fencer's name, nationality, club, HEMA Ratings id, e-mail, a registration moment, and a note. The registration moment SHALL default to the present moment in the tournament's own time zone and SHALL be changeable, so that a form received last week can be entered with the moment it was received.

#### Scenario: Only the offered disciplines appear
- **WHEN** a tournament offers three individual disciplines and one team discipline, and the organizer opens the dialog
- **THEN** the three individual disciplines are offered and the team discipline is not

#### Scenario: Rentals named as the tournament names them
- **WHEN** a tournament lends a mask and a longsword under those names
- **THEN** those are the items the dialog offers to borrow, and no others

#### Scenario: No afterparty, no question
- **WHEN** a tournament holds no afterparty
- **THEN** the dialog asks nothing about one

#### Scenario: Backdated entry
- **WHEN** the organizer changes the registration moment to a date three days ago and submits
- **THEN** the row is listed among the rows registered that day, not among today's

### Requirement: Strict validation of a manual entry
A manual entry SHALL be accepted whole or refused whole. The system SHALL NOT repair, guess at, or silently drop any value the organizer supplied.

A name SHALL be required and SHALL NOT be blank. At least one discipline SHALL be required. A discipline SHALL be one the tournament offers as individual; an item to borrow SHALL be one the tournament lends; a HEMA Ratings id SHALL be a whole number; an e-mail SHALL have the shape of an e-mail address; a registration moment SHALL be a readable moment. Nationality, club, e-mail, HEMA Ratings id and note SHALL be optional and, when left empty, SHALL be recorded as absent rather than as an empty value.

A refusal SHALL name the field it refuses and why, SHALL keep everything else the organizer has typed, and SHALL add no row. A refusal SHALL be shown against the field itself, not only as a summary.

An entry duplicating a fencer already on the list SHALL NOT be refused for that reason: duplicates are the deduplication phase's business, and refusing here would prevent the organizer from recording what actually happened.

#### Scenario: Blank name refused
- **WHEN** the organizer submits with no name
- **THEN** the entry is refused, the name field is marked, and no row is added

#### Scenario: No discipline refused
- **WHEN** the organizer submits without choosing a discipline
- **THEN** the entry is refused and says a discipline is required

#### Scenario: Non-numeric HEMA Ratings id refused
- **WHEN** the organizer types a profile URL into the HEMA Ratings id field
- **THEN** the entry is refused against that field and the rest of the form stands as typed

#### Scenario: Duplicate is allowed through
- **WHEN** the organizer enters a fencer whose name and hr_id match a row already on the list
- **THEN** the row is added, and the pair is left for deduplication to raise

#### Scenario: Empty optional field
- **WHEN** the organizer leaves the club empty
- **THEN** the row is added with no club, and the table shows a dash there

### Requirement: Where the two source actions live
The Import tab's operation panel SHALL carry both actions that concern a file: uploading one and clearing what has been imported. The Fencers tab's panel SHALL carry the manual entry action. Neither tab SHALL carry the other's action, each panel holding only the operation its own phase performs.

#### Scenario: Clear belongs to Import
- **WHEN** the organizer opens the Import tab
- **THEN** the upload and the clear action are both offered in its panel

#### Scenario: Fencers offers entry, not clearing
- **WHEN** the organizer opens the Fencers tab
- **THEN** manual entry is offered and no clear action is

## MODIFIED Requirements

### Requirement: Per-row phase status
Processing status SHALL be tracked per row, not globally. A row originating from in-app registration SHALL enter structured and HR-bound — it belongs to the fencer list from the moment it is created and SHALL never appear in the Import view — so Matching is satisfied for it at birth. An imported row SHALL enter unstructured and unmatched and SHALL traverse matching and deduplication. A manually entered row SHALL enter structured, its fields having been chosen from the tournament's own structure, but unmatched unless the organizer supplied a HEMA Ratings id, and SHALL traverse matching and deduplication as an imported row does.

The three populations SHALL coexist in one table without being separated: a phase view SHALL NOT hide rows for which its operation is already satisfied, and SHALL NOT group or mark rows by which population they came from beyond what the Import view's own scope already implies.

#### Scenario: Mixed table
- **WHEN** the table contains native registrations and freshly imported rows
- **THEN** native rows show as matched while imported rows still await matching, in the same view

#### Scenario: Registration never appears in Import
- **WHEN** a fencer registers in the application while an imported batch is present
- **THEN** their row joins the fencer list and the Import view is unchanged

#### Scenario: Manual row awaits matching
- **WHEN** a fencer is entered by hand without a HEMA Ratings id
- **THEN** their row appears on the fencer list awaiting matching, beside imported rows in the same state

### Requirement: Fixed fencer number
Every row of the fencer list SHALL carry a number that identifies the fencer within the tournament. The number SHALL be allocated once, when the row first enters the tournament — by registration, by import, or by manual entry — and SHALL NOT change afterwards for any reason: not when the table is sorted, not when an earlier row is deleted or restored, not when a duplicate is merged away, and not when a further import arrives.

A number SHALL NOT be reissued. The number of a row deleted or merged away SHALL remain retired rather than passing to another fencer; a restored row SHALL come back with the number it had.

Clearing the tournament's imported content SHALL be the one exception: the numbers held by the cleared rows SHALL be released, since the tournament is asserting that those rows never existed. No number still held by a row that survives the clear SHALL be reissued.

The number SHALL be allocated in the order rows enter the tournament, which is not necessarily the order the table displays. Where an imported row states a registration moment earlier than that of rows already numbered, the table SHALL sort it into its chronological place and its number SHALL stand out of sequence there. The number counts nobody's position in the list; it names a fencer.

The Import view SHALL NOT use this number. Its rows SHALL be numbered by their line in the uploaded file, a number meaningful only within that batch.

#### Scenario: Deletion does not renumber
- **WHEN** the organizer deletes the third row of a fifteen-row table
- **THEN** the remaining rows keep the numbers they had, and no number moves up

#### Scenario: Merge retires a number
- **WHEN** two rows are merged and the absorbed row disappears
- **THEN** the surviving row keeps its own number and the absorbed row's number is used by no one

#### Scenario: Backdated import numbers out of sequence
- **WHEN** an import brings a fencer whose registration moment precedes existing rows
- **THEN** that row is displayed among the earliest rows while carrying a number higher than theirs

#### Scenario: Import numbers its own lines
- **WHEN** the organizer opens the Import view
- **THEN** each row is numbered by its line in the uploaded file, and those numbers start again at one for the next upload

#### Scenario: Manual entry takes the next number
- **WHEN** the organizer enters a fencer by hand into a table whose highest number is forty
- **THEN** that row is numbered forty-one, whatever registration moment it states

#### Scenario: Clearing releases the cleared numbers
- **WHEN** a tournament numbered one to thirty, of which eleven to thirty came from a file, is cleared
- **THEN** the surviving rows keep numbers one to ten and the next row entered is numbered eleven

### Requirement: Order of the fencer list
The fencer list SHALL be ordered by registration moment, earliest first, across all populations together — an imported row, a manually entered row and an in-app registration SHALL interleave by their moments rather than being grouped by origin.

A row whose registration moment is unknown SHALL be placed after every row that states one, and such rows SHALL keep the order in which they were numbered — which for an imported batch is the order of its file. No substitute moment SHALL be invented for them.

#### Scenario: Populations interleave
- **WHEN** an imported row states a registration moment falling between two in-app registrations
- **THEN** it is listed between them

#### Scenario: Rows without a moment sort last
- **WHEN** an imported batch states no registration times
- **THEN** its rows follow every row that has a moment, in the order they appeared in the file

#### Scenario: Backdated manual entry interleaves
- **WHEN** the organizer enters a fencer by hand with a registration moment falling between two existing rows
- **THEN** it is listed between them rather than at the end
