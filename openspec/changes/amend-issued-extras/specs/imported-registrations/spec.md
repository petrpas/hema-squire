## ADDED Requirements

### Requirement: An item nothing prices is stated as a problem of the row
A row that borrows an item the tournament lends nothing by SHALL state that item
as a problem of the row, in the marker the fencer list and the Import view both
carry (`etl-console`), as well as in the rentals cell itself.

The cell states it to whoever is reading that column; the problem marker states
it to whoever is reading the row. Both are needed: the organizer who has to act
on it is usually looking for what is wrong with the roster, not auditing the
rentals column item by item, and a total short by one unbilled item is otherwise
invisible.

The row SHALL still be issued, and the item SHALL still be billed nothing: what
the fencer asked for is a record, and refusing it would replace an unpriced item
with a lost one.

#### Scenario: The problem names the item
- **WHEN** a row borrows an item the tournament offers under no name
- **THEN** the row carries a problem naming that item, alongside any parse problem it already had

#### Scenario: Correcting the name clears the problem
- **WHEN** the organizer corrects that item's name to one the tournament lends
- **THEN** the problem is gone from the row and the item is priced
