## MODIFIED Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Matching on HR, Deduplication, Payments, Export, Teams, Queue. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Teams and Queue SHALL likewise replace the fencer table with their own views, as fixed by `team-disciplines` and `seating-queue`.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it SHALL show one and the same set of rows** — every fencer the tournament knows, from in-app registration and from import together — as that set stands at the moment of viewing. A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), and the log of manual edits belonging to that phase. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which rows are listed.

Which phases are offered SHALL follow the tournament's features, as fixed by `tournament-modes`. The Payments phase SHALL be offered only while the payments feature is on, and the Teams phase only while the team disciplines feature is on. The remaining phases SHALL always be offered, since they are what every tournament is made of. Whichever phases are offered SHALL keep the fixed order above; the mode removes phases, it never reorders them.

A phase the mode does not offer SHALL NOT be reachable by its URL either. Addressing it SHALL open the console on the phase it opens on by default rather than on an empty view, so that a bookmark saved before a feature was turned off still lands somewhere useful.

#### Scenario: Switching phases
- **WHEN** the organizer switches from Matching on HR to Payments
- **THEN** the table re-renders with payment columns and the Payments parameter panel and edits log, over the same fencer list, and the URL names the Payments phase

#### Scenario: Import shows imported rows alone
- **WHEN** a tournament has ten in-app registrations and a five-row imported batch, and the organizer opens Import
- **THEN** the five imported rows are listed and none of the ten registrations is

#### Scenario: Fencers shows both populations
- **WHEN** the same organizer opens Fencers
- **THEN** all fifteen rows are listed together

#### Scenario: Duplicates stand until deduplication
- **WHEN** one fencer is present once as an in-app registration and twice in the imported batch, and deduplication has not yet run
- **THEN** that fencer occupies three rows in the Fencers table

#### Scenario: Setup tab
- **WHEN** the organizer opens the Setup tab
- **THEN** the tournament configuration forms and completeness checklist are shown in place of the fencer table

#### Scenario: Returning to Setup
- **WHEN** the organizer is on any processing tab and clicks the Setup tab
- **THEN** the Setup phase opens; the tab's full visual extent accepts the click

#### Scenario: Back returns to the previous phase
- **WHEN** the organizer moves from Import to Fencers and presses Back
- **THEN** the Import phase is shown again

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
without a phase segment SHALL open the Fencers phase. The console SHALL resolve the tournament
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
- **THEN** the Fencers phase is shown

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
Processing status SHALL be tracked per row, not globally. A row originating from in-app registration SHALL enter structured and HR-bound — it belongs to the fencer list from the moment it is created and SHALL never appear in the Import view — so Matching is satisfied for it at birth. An imported row SHALL enter unstructured and unmatched and SHALL traverse matching and deduplication.

The two populations SHALL coexist in one table without being separated: a phase view SHALL NOT hide rows for which its operation is already satisfied.

#### Scenario: Mixed table
- **WHEN** the table contains native registrations and freshly imported rows
- **THEN** native rows show as matched while imported rows still await matching, in the same view

#### Scenario: Registration never appears in Import
- **WHEN** a fencer registers in the application while an imported batch is present
- **THEN** their row joins the fencer list and the Import view is unchanged

### Requirement: Readable manual-edits log
Every entry in the manual-edits log SHALL be readable without knowledge of the
system's internals. An entry SHALL identify its row the way the table names that
row — by the row's number and the fencer's name — and never by the row's
internal id. The number SHALL be the row's fixed number, so that an entry keeps
naming the same fencer however the table is later sorted, deleted from, or
merged. A field SHALL be named by its column label. A change that has no
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

#### Scenario: Entry survives a deletion elsewhere
- **WHEN** an entry names fencer number 12 and the organizer then deletes an earlier row
- **THEN** the entry still names fencer number 12 and the same fencer

#### Scenario: Both languages
- **WHEN** the console is read in Czech
- **THEN** every part of an entry — field labels, the deletion and merge sentences, and rendered values — is Czech

## ADDED Requirements

### Requirement: Fixed fencer number
Every row of the fencer list SHALL carry a number that identifies the fencer within the tournament. The number SHALL be allocated once, when the row first enters the tournament, and SHALL NOT change afterwards for any reason: not when the table is sorted, not when an earlier row is deleted or restored, not when a duplicate is merged away, and not when a further import arrives.

A number SHALL NOT be reissued. The number of a row deleted or merged away SHALL remain retired rather than passing to another fencer; a restored row SHALL come back with the number it had.

The number SHALL be allocated in the order rows enter the tournament, which is not necessarily the order the table displays. Where an imported row states a registration moment earlier than that of rows already numbered, the table SHALL sort it into its chronological place and its number SHALL stand out of sequence there. The number counts nobody's position in the list; it names a fencer.

The Import view SHALL NOT use this number. Its rows SHALL be numbered by their line in the uploaded file, a number meaningful only within that batch.

#### Scenario: Deletion does not renumber
- **WHEN** the organizer deletes the third row of a fifteen-row table
- **THEN** the remaining rows keep the numbers they had, and no number moves up

#### Scenario: Merge retires a number
- **WHEN** two rows are merged and the absorbed row disappears
- **THEN** the surviving row keeps its own number and the absorbed row's number is used by no one

#### Scenario: Backdated import numbers out of sequence
- **WHEN** an import brings a fencer whose registration moment precedes existing rows
- **THEN** that row is displayed among the earliest rows while carrying a number higher than theirs

#### Scenario: Import numbers its own lines
- **WHEN** the organizer opens the Import view
- **THEN** each row is numbered by its line in the uploaded file, and those numbers start again at one for the next upload

### Requirement: Order of the fencer list
The fencer list SHALL be ordered by registration moment, earliest first, across both populations together — an imported row and an in-app registration SHALL interleave by their moments rather than being grouped by origin.

A row whose registration moment is unknown SHALL be placed after every row that states one, and such rows SHALL keep the order of the file they arrived in. No substitute moment SHALL be invented for them.

#### Scenario: Populations interleave
- **WHEN** an imported row states a registration moment falling between two in-app registrations
- **THEN** it is listed between them

#### Scenario: Rows without a moment sort last
- **WHEN** an imported batch states no registration times
- **THEN** its rows follow every row that has a moment, in the order they appeared in the file

### Requirement: Note and problem markers
A row's note and its parse problems SHALL NOT occupy table columns of their own. Each SHALL be shown as a marker in a narrow column, and the marker SHALL be shown only on a row that carries such content — a row with no note SHALL show nothing in the note column, not a dash and not an empty marker.

Activating a marker SHALL disclose the full text in place, as static bordered text that closes on dismissal. The disclosed text SHALL be read-only: a note is the fencer's words or the parser's, and a problem is the parser's report, neither of which the organizer rewrites.

The note marker SHALL be offered on the Import view and on the fencer list alike, since both populations carry notes. The problem marker SHALL be offered on the Import view alone, parse problems being a property of an imported row and never of an in-app registration.

#### Scenario: Row without a note
- **WHEN** a row carries no note
- **THEN** its note column is empty, showing no marker and no placeholder

#### Scenario: Reading a note
- **WHEN** the organizer activates the note marker on a row
- **THEN** the note's full text is shown, and it cannot be edited there

#### Scenario: Problems absent from the fencer list
- **WHEN** the organizer looks for parse problems on the Fencers tab
- **THEN** no problem column is offered there, and the Import view is where they are read

#### Scenario: A registration's note is reachable
- **WHEN** an in-app registration carries a note from the fencer
- **THEN** its marker appears on the fencer list and discloses that note

### Requirement: Import view of one batch
The Import view SHALL show the latest imported batch whole: every row of the file as it was read, parsed, and hand-corrected. A row that a later operation has absorbed or deleted SHALL remain listed there, marked as such, rather than disappearing — the view is a record of what a file contained and how it was understood, not a list of who is competing.

The Import view SHALL carry the import operation's controls; the fencer list SHALL NOT.

#### Scenario: Absorbed row stays visible
- **WHEN** deduplication merges an imported row into an in-app registration
- **THEN** the row remains in the Import view marked as absorbed, and is gone from the fencer list

#### Scenario: Import controls belong to Import
- **WHEN** the organizer opens the Fencers tab
- **THEN** no file upload is offered there

### Requirement: Two manual-edits logs with two meanings
A correction made on the Import view and a decision made on the fencer list SHALL be recorded in separate logs. The Import log SHALL hold corrections to how a file was read — errata against a batch. The fencer list's log and those of the phases after it SHALL hold the organizer's decisions about fencers.

Re-uploading a corrected file SHALL preserve the Import log's corrections for rows the file did not change, and SHALL NOT disturb the decisions recorded on the fencer list.

#### Scenario: Correction logged against the batch
- **WHEN** the organizer fixes a mangled name on the Import view
- **THEN** the entry appears in the Import log and not in the fencer list's log

#### Scenario: Decision logged against the fencer
- **WHEN** the organizer changes a fencer's club on the fencer list, the fencer having moved between clubs since registering
- **THEN** the entry appears in the fencer list's log and not in the Import log
