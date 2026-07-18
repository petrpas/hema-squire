## ADDED Requirements

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
Each change applied to the data SHALL be auditable for the lifetime of its causing rule: actor, timestamp, and before/after values.

#### Scenario: Inspecting a change
- **WHEN** the organizer opens the edits log on a phase
- **THEN** each entry shows who changed what, when, and from which value to which

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
