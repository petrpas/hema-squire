## ADDED Requirements

### Requirement: The rentals cell is open on the fencer list
The rentals cell SHALL be offered on the fencer list for every row that phase
lists, and SHALL be edited as the item names separated by commas, the way the
disciplines cell is edited. Whether a registration stands behind the row SHALL
decide what the edit *does* — a correction to the row, or an amendment of the
registration (`discipline-amendment`) — and SHALL NOT decide whether the cell
opens.

What a row borrows is priced, so an uncorrectable rentals cell is a wrong total
with no remedy in the console. It SHALL remain closed on every phase but the
fencer list, which is the phase that reads what a fencer asked for.

#### Scenario: Offered on a roster that has been issued
- **WHEN** the organizer opens the fencer list after an import has issued registrations for every row
- **THEN** the rentals cell opens for editing on every row

#### Scenario: Edited as the text it is shown as
- **WHEN** the organizer opens a rentals cell holding two items
- **THEN** the draft is those item names separated by a comma, and saving it states both

#### Scenario: Still closed on the phases that read the roster
- **WHEN** the organizer opens Matching on HR, Payments or Export
- **THEN** no rentals cell opens for editing

### Requirement: Note and problem markers on both views
A row's note and its parse problems SHALL NOT occupy table columns of their own. Each SHALL be shown as a marker in a narrow column, and the marker SHALL be shown only on a row that carries such content — a row with no note SHALL show nothing in the note column, not a dash and not an empty marker.

Activating a marker SHALL disclose the full text in place, as static bordered text that closes on dismissal. The disclosed text SHALL be read-only: a note is the fencer's words or the parser's, and a problem is the parser's report, neither of which the organizer rewrites.

The note marker SHALL be offered on the Import view and on the fencer list alike, since both populations carry notes.

The problem marker SHALL be offered on both as well. It began as a property of an imported row, but a row now states problems that outlive parsing — a borrowed item the tournament lends nothing by, which nothing is billing for — and the fencer list is where that item is read and corrected. A problem stated only on the view the organizer is not looking at is a problem stated nowhere.

#### Scenario: Row without a note
- **WHEN** a row carries no note
- **THEN** its note column is empty, showing no marker and no placeholder

#### Scenario: Reading a note
- **WHEN** the organizer activates the note marker on a row
- **THEN** the note's full text is shown, and it cannot be edited there

#### Scenario: A problem that outlives parsing is on the fencer list
- **WHEN** a row borrows an item the tournament lends nothing by
- **THEN** the fencer list shows a problem marker on that row naming the item nothing prices

#### Scenario: A row with nothing wrong shows no problem marker
- **WHEN** a row on the fencer list carries no parse problem and borrows only items the tournament lends
- **THEN** its problem column is empty

#### Scenario: A registration's note is reachable
- **WHEN** an in-app registration carries a note from the fencer
- **THEN** its marker appears on the fencer list and discloses that note

## REMOVED Requirements

### Requirement: Note and problem markers
**Reason**: The problem marker stopped being a property of an imported row alone. A row now carries problems that outlive parsing — a borrowed item the tournament lends nothing by — and the requirement's rule that the fencer list offers no problem column would hide exactly those.
**Migration**: Replaced in full by **Note and problem markers on both views**, which keeps every rule about the two markers and offers the problem marker on the fencer list as well.
