# etl-console Specification

## Purpose
Provide the organizer console: a phase-tabbed fencer table with per-row status, HR matching review, deterministic reruns, operation parameters, and reversible row deletion.

## Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present the tournament's fencer table under six phase tabs: Load, Parsing, Matching on HR, Deduplication, Payments, Export. Each phase tab SHALL show the full fencer list in the state after that operation, the base columns (No, Name, Nat., Club) plus phase-specific columns, the operation's parameter panel (general rules), and the log of manual edits belonging to that phase.

#### Scenario: Switching phases
- **WHEN** the organizer switches from Matching on HR to Payments
- **THEN** the table re-renders with payment columns and the Payments parameter panel and edits log, over the same fencer list

### Requirement: Per-row phase status
Processing status SHALL be tracked per row, not globally. Rows originating from in-app registration SHALL enter with Load, Parsing, and Matching satisfied (born structured and HR-bound); imported rows SHALL traverse all phases.

#### Scenario: Mixed table
- **WHEN** the table contains native registrations and freshly imported rows
- **THEN** native rows show as matched while imported rows still await matching, in the same view

### Requirement: HR matching review
The Matching phase SHALL show HR columns (HRID, HR_Name, HR_Nat, HR_Club) and a per-row match verdict: confirmed (✓), uncertain (?), or no match (✗). The organizer SHALL resolve ? and ✗ rows by accepting a candidate, searching and selecting a profile, or marking the fencer as having no HR profile. Each resolution SHALL persist as a rule.

#### Scenario: Resolving an uncertain match
- **WHEN** the organizer confirms the suggested profile on a row marked ?
- **THEN** the row becomes ✓, the hr_id is bound, and the decision survives future reruns

### Requirement: Rerun
The organizer SHALL be able to rerun processing at any time. A rerun SHALL recompute the table deterministically from source records, the persisted rule set, and current operation parameters. Previously materialized LLM decisions SHALL NOT be re-invoked; only rows without decisions may trigger LLM processing.

#### Scenario: Rerun after new import
- **WHEN** the organizer imports additional rows and reruns
- **THEN** existing rows keep their decisions and edits, and only the new rows are processed

### Requirement: Operation parameters
Each operation SHALL expose its parameters in the phase's general-rules panel (for example a matching similarity threshold). Parameter changes SHALL be audited and take effect on the next rerun.

#### Scenario: Threshold change
- **WHEN** the organizer lowers the matching similarity threshold and reruns
- **THEN** undecided rows are re-evaluated under the new threshold while resolved rows keep their rules

### Requirement: Reversible row deletion
Deleting a row SHALL be a manual, reversible operation: the row is excluded from active views and exports but remains restorable. Both deletion and restoration SHALL persist as rules.

#### Scenario: Delete and restore
- **WHEN** the organizer deletes a withdrawn fencer's row and later restores it
- **THEN** the row disappears from views and exports, then returns with its full history intact
