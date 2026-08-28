## MODIFIED Requirements

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
