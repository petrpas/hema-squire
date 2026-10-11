## MODIFIED Requirements

### Requirement: Reversible row deletion
Deleting a row SHALL be a manual, reversible operation: the row is excluded from active views and exports but remains restorable. Both deletion and restoration SHALL persist as rules.

**A row standing for a live registration SHALL NOT be deleted.** Deletion settles what the table holds, and a live registration is not a record to tidy away but a person holding a seat. Taking only the row away left that seat held and its clocks and payments running, unseen. Such a row SHALL offer **Zrušit registraci** in deletion's place (`registration`, An organizer may cancel a registration), and a deletion asked of it SHALL be refused with a reason naming the registration. A row whose registration has expired, an imported or hand-entered row not yet issued, and a row of import noise remain deletable and restorable as before. A row deleted while holding a live registration before this rule stood SHALL stay deleted and restorable; restored, it offers cancellation like any other.

A deleted row SHALL be listed on the phase whose deletion removed it and on every phase before that one in the fixed phase order, marked as deleted; the phases after it SHALL NOT list the row at all. The deletion is a decision taken at one step, and the steps that follow stand after it.

**Rows SHALL be removed and restored on Import and on the fencer list alone.** Those two are where the roster is settled; every phase after them reads it. A delete offered at the end of a row about money reads as an action on the money, and one at the end of a row about an HR profile reads as unbinding the profile — neither is what it does, and both are reachable one tab to the left where the row is plainly a row. A phase that offers no removal SHALL offer no restoration either, and SHALL attribute no deletion to itself.

Within those two phases the offer to restore a row SHALL be made wherever the row is listed, so that a row can always be brought back from the phase that removed it. Removing the deletion from that phase's manual-edits log SHALL restore the row equally.

A phase that lists no fencer table neither removes rows nor lists removed ones, and no deletion SHALL be attributed to it. A deleted row SHALL NOT be raised as a deduplication candidate, and a candidate group SHALL lose a member a deletion took out of the table.

A row a merge absorbed SHALL NOT be listed on any phase but Import, whatever phase the merge was decided on: a merge states that two rows are one fencer, which is true of every phase, and it is undone by withdrawing the merge rather than by restoring the row.

Whether a row is listed SHALL NOT change what the sheet holds: a hidden row remains in the projection, in the audit, and in the manual-edits log that names it.

#### Scenario: Delete and restore
- **WHEN** the organizer deletes a withdrawn fencer's row and later restores it
- **THEN** the row disappears from views and exports, then returns with its full history intact

#### Scenario: Gone from the phases that follow
- **WHEN** the organizer deletes a row on Fencers and moves through Matching on HR, Payments and Export
- **THEN** none of those tables lists the row

#### Scenario: A deleted row is no longer a duplicate of anything
- **WHEN** the organizer deletes one of two rows a deduplication candidate group named, and opens Deduplication
- **THEN** the group no longer stands as a candidate

#### Scenario: Still there where it was deleted
- **WHEN** the organizer returns to Fencers after deleting a row there
- **THEN** the row is listed, struck through, and offers to be restored

#### Scenario: The later phases offer nothing on a row
- **WHEN** the organizer opens Matching on HR, Payments or Export
- **THEN** no row offers to be deleted or restored, and a row deleted on Fencers is simply absent

#### Scenario: Restoring returns it to every phase
- **WHEN** the organizer restores a row deleted on Fencers
- **THEN** every phase lists it again, unmarked

#### Scenario: The edits log still names a hidden row
- **WHEN** an entry of the Fencers log names a row deleted on Import
- **THEN** the entry still names that row by its fixed number and the fencer's name, though no table on Fencers lists it

#### Scenario: An absorbed row is not listed again
- **WHEN** deduplication merges an imported row into an in-app registration and the organizer opens Fencers
- **THEN** the absorbed row is not listed there, and the Import view still shows it marked as absorbed

#### Scenario: A live registration is cancelled, not deleted
- **WHEN** the organizer opens the actions of a fencer-list row standing for a reserved registration
- **THEN** Zrušit registraci is offered and deletion is not

#### Scenario: The server refuses the deletion
- **WHEN** a deletion is asked of a live registration's row by any route
- **THEN** it is refused with a reason naming the registration, and no rule is written

#### Scenario: An expired registration's row may still be tidied
- **WHEN** the organizer deletes the row of a reservation that has expired
- **THEN** the row is deleted and remains restorable
