# edit-rules Specification

## Purpose
Persist every manual data action as a replayable rule, with auditability, deterministic replay, and a meta-journal of rule lifecycle events.
## Requirements
### Requirement: Every manual action creates a rule
Every manual data action over a row — field edit, row deletion or restoration, match resolution, deduplication decision, manual payment link — SHALL create a persistent rule that is re-applied on every rerun of the process.

#### Scenario: Diacritics correction survives reruns
- **WHEN** the organizer corrects "Novak" to "Novák" and later reruns the process
- **THEN** the corrected name is reproduced by replaying the rule

### Requirement: Rule lifecycle
Rules SHALL be listable per phase, editable, and removable by the organizer. Removing a rule SHALL recompute the state as if the rule had never existed.

#### Scenario: Removing an edit
- **WHEN** the organizer deletes the "Novak → Novák" rule
- **THEN** on recomputation the name reverts to its source-derived value

### Requirement: Audit of applied changes
The edits log SHALL state the net difference between the current table and the
source data: one entry per row field whose replayed value differs from its
source-derived value, showing that field's source value, its current value, and
the actor and timestamp of the newest rule that contributed to it. A field whose
rules return it to its source value SHALL produce no entry, however many rules
were involved. An entry SHALL belong to the phase of its newest contributing
rule, and removing an entry SHALL remove every rule behind it, so the field
returns to its source value in a single action. The full per-rule history remains
answerable from the rule journal.

#### Scenario: Inspecting a change
- **WHEN** the organizer opens the edits log on a phase
- **THEN** each entry shows which row and field changed, from which value to which, and who last changed it, when

#### Scenario: Cancelling operations leave no entry
- **WHEN** the organizer deletes a row and then restores it
- **THEN** the edits log shows no entry for that row, while the journal still records both operations

#### Scenario: Repeated operations do not stack
- **WHEN** the organizer deletes a row, restores it, and deletes it again
- **THEN** the edits log shows a single entry stating the row is deleted, attributed to the last of the three operations

#### Scenario: Removing an entry undoes every rule behind it
- **WHEN** a name has been edited twice and the organizer removes the log's entry for that name
- **THEN** both edits are removed and the name reverts to its source-derived value

#### Scenario: An entry sits in the phase of its newest rule
- **WHEN** a field edited during Load is edited again during Matching
- **THEN** the entry appears in the Matching phase's log and not in Load's

### Requirement: Deterministic replay
Given identical source records, rule set, and operation parameters, replay SHALL produce an identical table state.

#### Scenario: Reproducible state
- **WHEN** the same inputs are replayed on another day or another machine
- **THEN** the resulting table is byte-identical in content

### Requirement: Meta-journal of rule lifecycle events
The system SHALL retain an append-only journal of rule creation and deletion events (actor, timestamp, rule content). The journal SHALL NOT participate in replay: data-side, a deleted rule remains as if it had never existed.

#### Scenario: Accountability for a deleted rule
- **WHEN** the organizer asks who deleted a rule and when
- **THEN** the journal answers it, while the replayed table state shows no trace of the deleted rule

### Requirement: Rule ordering
Rules SHALL apply in creation order. Where multiple rules target the same field of the same row, the most recently created rule SHALL determine the value.

#### Scenario: Two edits of one cell
- **WHEN** a name is edited twice by two different rules
- **THEN** the later rule's value is shown, and removing it exposes the earlier rule's value

### Requirement: A removed row states where it was removed
Replay SHALL state, on every row it marks removed, the phase of the rule that
removed it — the deletion, or the merge that absorbed it. Where several rules
have removed and returned a row in turn, the stated phase SHALL be that of the
latest removal standing, and a row a restoration has returned SHALL state no
removing phase at all.

The removing phase SHALL be a replay product, derived afresh from the rule set
on every replay and stored nowhere: identical inputs state the same phase, and
withdrawing the removing rule withdraws it.

A row whose removing phase is not one the console offers SHALL be treated as
removed nowhere in particular rather than as removed everywhere, so that a
phase no longer in the order cannot make a row unreachable.

#### Scenario: A deletion states its phase
- **WHEN** a row is deleted by a rule belonging to the Payments phase
- **THEN** the replayed row is marked removed and states Payments as where it was removed

#### Scenario: A restoration clears it
- **WHEN** that row is then restored
- **THEN** the replayed row is neither marked removed nor states a removing phase

#### Scenario: The latest removal wins
- **WHEN** a row deleted on Import is restored and deleted again on Deduplication
- **THEN** the replayed row states Deduplication, not Import

#### Scenario: A merge states its phase
- **WHEN** a merge decided on Deduplication absorbs a row
- **THEN** the absorbed row states Deduplication as where it was removed, alongside the row it was merged into

#### Scenario: Withdrawing the rule withdraws the phase
- **WHEN** the rule that deleted a row is removed from the rule set
- **THEN** the next replay produces a row that is neither removed nor states a removing phase, without any stored value to clean up

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

### Requirement: A rule may replace the person a row is about
A substitution SHALL be a rule of a third kind, whose subject is **who the row is about** rather than a projected field or a registration's billing.

The kind SHALL carry the whole of the substitute's identity — name, HEMA Ratings id where one was chosen, nationality, club, the seat's address — together with the identity it replaced, so that a replay states the decision that was taken and a withdrawal has somewhere to return the seat to. It SHALL NOT be recorded as a set of field edits: several edits can be withdrawn one at a time, which would leave a row wearing half of one person and half of another.

Where a registration stands behind the row, applying the rule SHALL move the registration to the substitute's fencer record and SHALL set the seat's contact address; the projection follows from the registration, as it does for an amendment. Where no registration stands behind the row — an imported or hand-entered row not yet issued one — applying the rule SHALL write the identity onto the projected row.

Applying the rule SHALL NOT recompute the registration's total, SHALL NOT touch its entries or its items, and SHALL NOT write to the payment journal. It changes who holds the seat, not what the seat is.

An identity field edit SHALL remain what it is: correcting a misspelt name is not a substitution, and SHALL NOT be recorded as one.

#### Scenario: The rule reaches the registration
- **WHEN** a substitution is applied to a row that has a registration
- **THEN** the registration belongs to the substitute's fencer record, its total and entries are unchanged, and the table states the substitute's name

#### Scenario: The rule writes the projection where there is no registration
- **WHEN** a substitution is applied to an imported row that has been issued no registration
- **THEN** the projected row states the substitute's name, profile, nationality and club

#### Scenario: Withdrawal returns the whole identity at once
- **WHEN** a substitution rule is withdrawn
- **THEN** the row states the replaced fencer's name, profile, nationality, club and address together, with nothing of the substitute left on it

#### Scenario: A correction is not a substitution
- **WHEN** the organizer corrects a misspelt name in the table
- **THEN** a field edit is recorded, no substitution is, and no mail is sent

### Requirement: The substitution reads as a sentence in the log
The manual-edits log SHALL render a substitution as one line naming the row, the fencer replaced and the fencer who replaced them, in that order, in the reading language. It SHALL NOT render the identity payload field by field.

#### Scenario: One readable line
- **WHEN** the organizer reads the fencer list's manual-edits log after a substitution
- **THEN** one entry names the row's number, the replaced fencer and the substitute
