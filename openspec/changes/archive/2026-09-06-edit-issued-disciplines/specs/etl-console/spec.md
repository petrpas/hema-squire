## ADDED Requirements

### Requirement: The disciplines cell is not closed by the row having a registration
The disciplines cell SHALL be offered on the fencer list for every row that
phase lists. Whether a registration stands behind the row SHALL decide what the
edit *does* — a correction to the row, or an amendment of the registration
(`discipline-amendment`) — and SHALL NOT decide whether the cell opens.

The cell was previously offered only for a row with no registration behind it,
on the ground that an edit reaching an issued registration would move the table
without the money. Issuing became a step of payment intake, so after any import
every row has a registration and the cell opened for nothing. A condition that
names a state the product no longer produces is not a safeguard; it is a
feature withdrawn without saying so.

The cell SHALL remain closed on every phase but the fencer list. The phases
after it read the roster rather than settle it, and Import has no registration
to amend.

#### Scenario: Offered on a roster that has been issued
- **WHEN** the organizer opens the fencer list after an import has issued registrations for every row
- **THEN** the disciplines cell opens for editing on every row

#### Scenario: Offered on a row that has not been issued
- **WHEN** the organizer opens the fencer list of a roster no intake has issued yet
- **THEN** the disciplines cell opens for editing, and the edit is carried into the registration when the row is issued

#### Scenario: Still closed on the phases that read the roster
- **WHEN** the organizer opens Matching on HR, Payments or Export
- **THEN** no disciplines cell opens for editing
