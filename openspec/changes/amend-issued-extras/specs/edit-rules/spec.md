## MODIFIED Requirements

### Requirement: A rule may act on a registration rather than on a projected row
Most rules restate what a row says: they are replayed over the projected table,
and removing one returns the field to its source-derived value.

A registration amendment SHALL be a rule of a second kind, one whose subject is
the registration behind the row rather than the row's projection. Applying it
SHALL replace what the amended field names on that registration and recompute
its stored total; a rule that wrote only the projected row would leave the table
saying one thing while the registration billed another, which is the defect the
kind exists to avoid.

The kind SHALL carry **which field it amends** and the whole of that field's new
value. The fields it may amend are those that decide what a registration is
billed: its disciplines, and the items it borrows. One kind rather than one per
field, because what differs between them is a validator and a column, and a
second parallel path would be one more place for the pricing, the notice and
the withdrawal to drift apart.

The value SHALL be validated when the rule is created — disciplines against the
tournament's own offered individual disciplines, borrowed items against nothing,
an item the tournament does not lend being stated on the row rather than refused
(`imported-registrations`) — so a replay states the decision that was taken
rather than depending on what the tournament offers today.

An edit to an amendable field SHALL NOT be recorded as a field edit where a
registration stands behind the row. A field edit writes the projection, and
accepting one there would produce the mismatch silently.

#### Scenario: The rule reaches the registration
- **WHEN** the organizer changes a row's disciplines and the row has a registration
- **THEN** the registration's entries and total change, and the table states the same disciplines

#### Scenario: A rentals edit reaches the registration
- **WHEN** the organizer changes what a row borrows and the row has a registration
- **THEN** the registration's rental selections and total change, and the table states the same items

#### Scenario: A field edit is refused where it would only move the table
- **WHEN** a disciplines field edit is submitted for a row that has a registration
- **THEN** it is refused rather than applied to the projection alone

#### Scenario: A rentals field edit is refused the same way
- **WHEN** a rentals field edit is submitted for a row that has a registration
- **THEN** it is refused rather than applied to the projection alone

### Requirement: Withdrawing a discipline amendment prices it back
Removing a registration amendment from the manual-edits log SHALL return the
amended field to what the registration was issued with, and the registration to
the total that state produces, on the same terms the amendment itself was
applied on: priced at the registration's own registration moment, placed
according to the registration's origin, and silent unless the withdrawal leaves
the fencer owing more.

The withdrawal SHALL be visible in the log as the amendment was, so that a
correction and its undoing read as two decisions rather than as one that
vanished.

Where a registration has been amended more than once, removing one rule SHALL
leave the state the remaining rules produce, exactly as removing any other rule
does (**Rule lifecycle**). This SHALL hold field by field: withdrawing an
amendment of one field SHALL NOT disturb what an amendment of another field
still standing decided.

#### Scenario: Undoing a correction restores the price
- **WHEN** the organizer withdraws a discipline amendment that had added a discipline
- **THEN** the registration holds its previous disciplines and its previous total

#### Scenario: Undoing the dearer of two corrections
- **WHEN** two amendments have been applied and the organizer withdraws the first
- **THEN** the registration holds what the second alone produces

#### Scenario: Undoing one field leaves another field's amendment standing
- **WHEN** a row's disciplines and rentals have both been amended and the disciplines amendment is withdrawn
- **THEN** the registration holds its issued disciplines and its amended rentals, and its total accounts for both

#### Scenario: An undo that costs the fencer is announced
- **WHEN** withdrawing an amendment leaves the fencer owing more than they have paid
- **THEN** the fencer receives the surcharge notice
