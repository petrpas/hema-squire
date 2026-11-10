## MODIFIED Requirements

### Requirement: Meta-journal of rule lifecycle events
The system SHALL retain an append-only journal of rule creation and deletion events (actor, timestamp, rule content). The journal SHALL NOT participate in replay: data-side, a deleted rule remains as if it had never existed.

Append-only SHALL mean that an entry is never rewritten to change what happened. The sole exception SHALL be redaction required by `account-deletion`: a personal address or an erased name in an entry's content SHALL be removable, while the entry, its actor and its timestamp stay.

#### Scenario: Accountability for a deleted rule
- **WHEN** the organizer asks who deleted a rule and when
- **THEN** the journal answers it, while the replayed table state shows no trace of the deleted rule

#### Scenario: Redacted address
- **WHEN** an account whose address appears in a journal entry is deleted
- **THEN** the entry remains and no longer contains the address
