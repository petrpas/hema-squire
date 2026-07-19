## MODIFIED Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present seven phase tabs: Setup, Load, Parsing, Matching on HR, Deduplication, Payments, Export. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Each of the six processing tabs SHALL show the full fencer list in the state after that operation, the base columns (No, Name, Nat., Club) plus phase-specific columns, the operation's parameter panel (general rules), and the log of manual edits belonging to that phase.

#### Scenario: Switching phases
- **WHEN** the organizer switches from Matching on HR to Payments
- **THEN** the table re-renders with payment columns and the Payments parameter panel and edits log, over the same fencer list

#### Scenario: Setup tab
- **WHEN** the organizer opens the Setup tab
- **THEN** the tournament configuration forms and completeness checklist are shown in place of the fencer table