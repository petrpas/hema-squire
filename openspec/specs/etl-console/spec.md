# etl-console Specification

## Purpose
Provide the organizer console: a phase-tabbed fencer table with per-row status, HR matching review, deterministic reruns, operation parameters, and reversible row deletion.

## Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Load, Parsing, Matching on HR, Deduplication, Payments, Export, Teams, Queue. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Teams and Queue SHALL likewise replace the fencer table with their own views, as fixed by `team-disciplines` and `seating-queue`. Each of the processing tabs SHALL show the full fencer list in the state after that operation, the base columns (No, Name, Nat., Club) plus phase-specific columns, the operation's parameter panel (general rules), and the log of manual edits belonging to that phase.

**Which phases are offered SHALL follow the tournament's features**, as fixed by `tournament-modes`. The Payments phase SHALL be offered only while the payments feature is on, and the Teams phase only while the team disciplines feature is on. The remaining phases SHALL always be offered, since they are what every tournament is made of. Whichever phases are offered SHALL keep the fixed order above; the mode removes phases, it never reorders them.

A phase the mode does not offer SHALL NOT be reachable by its URL either. Addressing it SHALL open the console on the phase it opens on by default rather than on an empty view, so that a bookmark saved before a feature was turned off still lands somewhere useful.

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

#### Scenario: Payments phase absent without the feature
- **WHEN** the organizer opens the console of a tournament whose payments feature is off
- **THEN** no Payments phase is offered, and the other phases its mode allows behave as usual

#### Scenario: Teams phase absent without the feature
- **WHEN** the organizer opens the console of a tournament whose team disciplines feature is off
- **THEN** no Teams phase is offered

#### Scenario: Stale bookmark to a hidden phase
- **WHEN** an organizer opens a saved URL naming the Payments phase of a tournament whose payments feature has since been turned off
- **THEN** the console opens on its default phase rather than on an empty Payments view

#### Scenario: Phase reappears with its feature
- **WHEN** the organizer turns the payments feature back on
- **THEN** the Payments phase is offered again in its fixed place between Deduplication and Export

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
An operation whose behaviour the organizer tunes SHALL expose its own parameters in the phase that runs it — the matching similarity threshold in the matching phase, the amount-matching tolerance in the payments phase. Parameter changes SHALL be audited and take effect on the next rerun.

A phase panel SHALL carry only parameters of the operation that phase runs. **Configuration of the tournament itself SHALL NOT be offered in any phase panel**: what the tournament costs, when it happens, and how fencers pay are decisions taken in Setup before publication, and offering them in a phase panel puts a second editor on a field Setup is responsible for. A phase that has no parameters of its own SHALL show no parameter panel rather than an empty one.

#### Scenario: Threshold change
- **WHEN** the organizer lowers the matching similarity threshold and reruns
- **THEN** undecided rows are re-evaluated under the new threshold while resolved rows keep their rules

#### Scenario: Tolerance belongs to the payments phase
- **WHEN** the organizer opens the payments phase during reconciliation
- **THEN** the amount-matching tolerance is offered there and takes effect on the next rerun

#### Scenario: No tournament configuration in a phase panel
- **WHEN** the organizer looks for the payment mode, the deposit, a tournament date, or a price in any console phase panel
- **THEN** none is offered, and Setup is the only place each can be edited

#### Scenario: A phase with no parameters shows no panel
- **WHEN** the organizer opens a phase whose operation has no tunable parameters
- **THEN** no parameter panel is shown for it

### Requirement: Reversible row deletion
Deleting a row SHALL be a manual, reversible operation: the row is excluded from active views and exports but remains restorable. Both deletion and restoration SHALL persist as rules.

#### Scenario: Delete and restore
- **WHEN** the organizer deletes a withdrawn fencer's row and later restores it
- **THEN** the row disappears from views and exports, then returns with its full history intact

### Requirement: Registration moment in the fencer table
The console's fencer table SHALL state each row's registration moment as a day
and a clock time together, never as a day alone. The clock SHALL be shown on
the 24-hour scale to the minute; seconds SHALL NOT be shown.

The moment SHALL be read in the tournament's own zone — the same zone every
other date and time on that tournament's timeline is read in — so that two
organizers in different places read one registration as the same instant. A
registration moment that carries no zone of its own, as an imported row's does,
SHALL be shown as the wall clock it states, unshifted; it SHALL NOT be
reinterpreted as an instant in the reader's zone or the tournament's.

A row with no registration moment SHALL keep the em dash the table uses for an
absent value. The column SHALL be set in tabular numerals so the moments align
down the column.

#### Scenario: Registration moment carries a zone
- **WHEN** a registration recorded at 15:32 in the tournament's zone is shown in the fencer table
- **THEN** its cell states that day and `15:32`, whatever zone the organizer's browser sits in

#### Scenario: Two registrations on one day
- **WHEN** two fencers registered on the same day, one in the morning and one in the evening
- **THEN** their cells differ by their clock times, and the order the table is sorted in is visible in the column

#### Scenario: Imported row states a bare local time
- **WHEN** an imported row's registration time arrives as a date and time without a zone or offset
- **THEN** its cell states that same date and time, shifted by no zone conversion

#### Scenario: Row without a registration moment
- **WHEN** a row carries no registration moment
- **THEN** its cell shows the em dash, not a fallback date or an empty cell

### Requirement: Readable manual-edits log
Every entry in the manual-edits log SHALL be readable without knowledge of the
system's internals. An entry SHALL identify its row as the table does — by the
row's number in the current table and the fencer's name — and never by the row's
internal id. A field SHALL be named by its column label. A change that has no
column of its own SHALL be phrased as a sentence rather than a field assignment:
a deletion reads as a deletion, a restoration is absent (it cancels), and a
merge reads as a merge into the named surviving row. Values SHALL be rendered as
the table renders them, with an empty value shown as a dash.

#### Scenario: Deleted row
- **WHEN** the organizer deletes the row of a withdrawn fencer
- **THEN** the log entry names the row by its number and the fencer's name and states that the row is deleted, in place of a `_deleted` field assignment

#### Scenario: Field edit
- **WHEN** the organizer corrects a fencer's club
- **THEN** the log entry names the row and reads as the club's column label with the old and new value

#### Scenario: Merged row
- **WHEN** the organizer confirms a duplicate merge
- **THEN** the absorbed row's entry states that it was merged into the surviving row, named by its number and fencer name

#### Scenario: Both languages
- **WHEN** the console is read in Czech
- **THEN** every part of an entry — field labels, the deletion and merge sentences, and rendered values — is Czech
