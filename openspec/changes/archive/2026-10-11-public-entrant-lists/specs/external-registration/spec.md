## MODIFIED Requirements

### Requirement: A participant list Squire does not maintain says so
WHERE the roster shown publicly is one Squire does not maintain — the organizer keeps the registrations and the entrants reached Squire by import — the Entrants tab (`public-entrants`) SHALL state, above its rosters, the moment the roster last reached Squire.

The statement SHALL be a fact about when, and SHALL NOT be a judgement about currency: it SHALL NOT claim the list is up to date and SHALL NOT warn that it may be stale. Both are assessments Squire cannot make, and the second would be wrong the moment the organizer imports again.

What such a list shows about payment, and that it shows no queue and draws no capacity line, is fixed by `public-entrants`.

#### Scenario: The list dates itself
- **WHEN** a visitor opens the Entrants tab of an organizer-kept tournament whose roster was last imported four days ago
- **THEN** the tab states, above its rosters, that they stand as of that moment

#### Scenario: No judgement is offered
- **WHEN** the roster was last imported three months ago
- **THEN** the list states that moment and does not warn that it may be out of date

#### Scenario: A fresh import moves the moment
- **WHEN** the organizer imports an updated roster
- **THEN** the stated moment becomes the new one

#### Scenario: A live list states no moment
- **WHEN** a visitor opens the Entrants tab of a tournament whose registrations Squire keeps
- **THEN** no as-of moment is stated
