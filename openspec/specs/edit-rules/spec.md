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
