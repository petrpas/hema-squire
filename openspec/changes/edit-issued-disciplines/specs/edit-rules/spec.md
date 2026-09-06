## ADDED Requirements

### Requirement: A rule may act on a registration rather than on a projected row
Most rules restate what a row says: they are replayed over the projected table,
and removing one returns the field to its source-derived value.

A discipline amendment SHALL be a rule of a second kind, one whose subject is
the registration behind the row rather than the row's projection. Applying it
SHALL replace that registration's discipline entries and recompute its stored
total; a rule that wrote only the projected row would leave the table saying one
thing while the registration billed another, which is the defect the kind exists
to avoid.

The kind SHALL carry the disciplines it names, validated against the
tournament's own offered individual disciplines when the rule is created, so a
replay states the decision that was taken rather than depending on what the
tournament offers today.

A discipline edit SHALL NOT be recorded as a field edit where a registration
stands behind the row. A field edit writes the projection, and accepting one
there would produce the mismatch silently.

#### Scenario: The rule reaches the registration
- **WHEN** the organizer changes a row's disciplines and the row has a registration
- **THEN** the registration's entries and total change, and the table states the same disciplines

#### Scenario: A field edit is refused where it would only move the table
- **WHEN** a disciplines field edit is submitted for a row that has a registration
- **THEN** it is refused rather than applied to the projection alone

### Requirement: Withdrawing a discipline amendment prices it back
Removing a discipline amendment from the manual-edits log SHALL return the
registration to the disciplines and the total it held before that rule was
applied, on the same terms the amendment itself was applied on: priced at the
registration's own registration moment, placed according to the registration's
origin, and silent unless the withdrawal leaves the fencer owing more.

The withdrawal SHALL be visible in the log as the amendment was, so that a
correction and its undoing read as two decisions rather than as one that
vanished.

Where a registration has been amended more than once, removing one rule SHALL
leave the state the remaining rules produce, exactly as removing any other rule
does (**Rule lifecycle**).

#### Scenario: Undoing a correction restores the price
- **WHEN** the organizer withdraws a discipline amendment that had added a discipline
- **THEN** the registration holds its previous disciplines and its previous total

#### Scenario: Undoing the dearer of two corrections
- **WHEN** two amendments have been applied and the organizer withdraws the first
- **THEN** the registration holds what the second alone produces

#### Scenario: An undo that costs the fencer is announced
- **WHEN** withdrawing an amendment leaves the fencer owing more than they have paid
- **THEN** the fencer receives the surcharge notice
