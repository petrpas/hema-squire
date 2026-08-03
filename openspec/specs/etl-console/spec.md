# etl-console Specification

## Purpose
Provide the organizer console: a phase-tabbed fencer table with per-row status, HR matching review, deterministic reruns, operation parameters, and reversible row deletion.

## Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present seven phase tabs: Setup, Load, Parsing, Matching on HR, Deduplication, Payments, Export. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Each of the six processing tabs SHALL show the full fencer list in the state after that operation, the base columns (No, Name, Nat., Club) plus phase-specific columns, the operation's parameter panel (general rules), and the log of manual edits belonging to that phase.

#### Scenario: Switching phases
- **WHEN** the organizer switches from Matching on HR to Payments
- **THEN** the table re-renders with payment columns and the Payments parameter panel and edits log, over the same fencer list, and the URL names the Payments phase

#### Scenario: Setup tab
- **WHEN** the organizer opens the Setup tab
- **THEN** the tournament configuration forms and completeness checklist are shown in place of the fencer table

#### Scenario: Returning to Setup
- **WHEN** the organizer is on any processing tab and clicks the Setup tab
- **THEN** the Setup phase opens; the tab's full visual extent accepts the click

#### Scenario: Back returns to the previous phase
- **WHEN** the organizer moves from Load to Parsing and presses Back
- **THEN** the Load phase is shown again

### Requirement: Console addressed by tournament and phase
The console SHALL be addressed by the URL `/organizer/:slug/console/:phase`, where `:slug`
identifies the tournament and `:phase` names the open phase tab; `/organizer/:slug/console`
without a phase segment SHALL open the Load phase. The console SHALL resolve the tournament
from `:slug` through the API on its own, so that it opens from a URL alone, with no
tournament object handed to it by the picker or by any other screen. While it resolves the
tournament it SHALL show the design system's static loading text, never a spinner or an
animated progress indicator.

A slug naming no tournament, or one the account may not open, SHALL render the not-found
screen (`routing`) rather than an empty console. A phase segment outside the console's known
phases SHALL do the same rather than silently opening a default phase.

Creating a tournament from the picker SHALL land the creator on that tournament's Setup
phase URL, which is how `tournament-admin`'s create-from-picker requirement is now satisfied.

#### Scenario: Console opened by URL alone
- **WHEN** an organizer opens `/organizer/spring-open-2026/console/dedup` in a fresh tab, having never visited the picker in that session
- **THEN** the console loads that tournament itself and opens on the Deduplication phase

#### Scenario: Phase omitted from the URL
- **WHEN** an organizer opens `/organizer/spring-open-2026/console`
- **THEN** the Load phase is shown

#### Scenario: Console survives a refresh
- **WHEN** the organizer refreshes the browser while the Payments phase is open
- **THEN** the same tournament's Payments phase is shown again

#### Scenario: Unknown tournament
- **WHEN** an organizer opens `/organizer/no-such-thing/console`
- **THEN** the not-found screen is shown

#### Scenario: Creation lands on Setup
- **WHEN** an organizer creates a tournament from the picker
- **THEN** they arrive at `/organizer/<new-slug>/console/setup` with the Setup phase open

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
