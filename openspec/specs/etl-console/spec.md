# etl-console Specification

## Purpose
Provide the organizer console: a phase-tabbed fencer table with per-row status, HR matching review, deterministic reruns, operation parameters, and reversible row deletion.

## Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Matching on HR, Deduplication, Payments, Export, Teams, Queue. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Teams and Queue SHALL likewise replace the fencer table with their own views, as fixed by `team-disciplines` and `seating-queue`.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it SHALL show one and the same set of fencers** — every fencer the tournament knows, from in-app registration and from import together — as that set stands at the moment of viewing, minus the rows a removal earlier in the phase order has already taken out of it (Reversible row deletion). A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), the log of manual edits belonging to that phase, and the removals it stands after. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which fencers are listed.

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

#### Scenario: A phase after a deletion lists fewer rows
- **WHEN** the organizer deletes one of those fifteen rows on Fencers and then opens Payments
- **THEN** fourteen rows are listed there, and Fencers still lists fifteen

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
Processing status SHALL be tracked per row, not globally. A row originating from in-app registration SHALL enter structured and HR-bound — it belongs to the fencer list from the moment it is created and SHALL never appear in the Import view — so Matching is satisfied for it at birth. An imported row SHALL enter unstructured and unmatched and SHALL traverse matching and deduplication. A manually entered row SHALL enter structured, its fields having been chosen from the tournament's own structure, but unmatched unless the organizer supplied a HEMA Ratings id, and SHALL traverse matching and deduplication as an imported row does.

The three populations SHALL coexist in one table without being separated: a phase view SHALL NOT hide rows for which its operation is already satisfied, and SHALL NOT group or mark rows by which population they came from beyond what the Import view's own scope already implies.

#### Scenario: Mixed table
- **WHEN** the table contains native registrations and freshly imported rows
- **THEN** native rows show as matched while imported rows still await matching, in the same view

#### Scenario: Registration never appears in Import
- **WHEN** a fencer registers in the application while an imported batch is present
- **THEN** their row joins the fencer list and the Import view is unchanged

#### Scenario: Manual row awaits matching
- **WHEN** a fencer is entered by hand without a HEMA Ratings id
- **THEN** their row appears on the fencer list awaiting matching, beside imported rows in the same state

### Requirement: HR matching review
The Matching phase SHALL present each row as a ledger line per **The ledger
idiom**: the registered name, nationality and club as the claim; the HR columns
(HRID, HR_Name, HR_Nat, HR_Club) as the evidence; and a per-row match verdict.
The verdict SHALL be one of confirmed, found, proposed, no match, or unmatched,
and SHALL distinguish those owing the organizer work from those that do not.

The evidence register SHALL state the profile's nationality as its two-letter
ISO country code, whatever vocabulary the source spells it in, so that it can be
read
against a claim written in codes without the reader taking a difference in
spelling for a difference in country. Where no country can be identified the
source's own words SHALL stand — a spelling the system cannot read is still the
evidence it has.

The organizer SHALL ratify a proposed match in one action on the row. From any
row, whatever its verdict, the organizer SHALL be able to search the fighters
index and select a different profile, or mark the fencer as having no HR
profile. Entering a HEMA Ratings id directly into the row SHALL be a verdict,
carrying the same weight and the same consequences as a selection made by
search. Each resolution SHALL persist as a rule.

A resolution SHALL read in the manual-edits log as **one entry**. Binding an id,
the verdict that binding reaches, the canonical name it promotes, the registered
name that promotion displaces, and the evidence register it moves are one
decision by one organizer; as separate entries they would report a single click
several times over. The entry SHALL state what the organizer decided — the id
where the resolution moved it, and the verdict where it did not.

#### Scenario: Resolving an uncertain match
- **WHEN** the organizer confirms the suggested profile on a row marked proposed
- **THEN** the row becomes confirmed, the hr_id is bound, and the decision survives future reruns

#### Scenario: One vocabulary down the evidence column
- **WHEN** the fighters index records a fencer's country as an English name
- **THEN** the row states it as a two-letter ISO code, and every row states it the same way whatever the verdict and whenever the verdict was reached

#### Scenario: Comparing claim against evidence
- **WHEN** the organizer reviews a row whose registered name, club or nationality differs from the matched profile's
- **THEN** both sets of values are visible on the row at once, without opening anything

#### Scenario: One decision, one entry
- **WHEN** the organizer confirms a proposed match and the canonical name is promoted over the registered one
- **THEN** the log carries a single entry for that row, naming the verdict reached, and the promotion is visible on the row rather than as further entries

#### Scenario: A typed id is a verdict
- **WHEN** the organizer types a HEMA Ratings id into a row's HRID cell
- **THEN** the row's verdict becomes confirmed and the id's consequences follow, as though the profile had been selected by search

#### Scenario: Settled rows are still revisable
- **WHEN** the organizer opens the search on a row already reading found or confirmed
- **THEN** an alternative profile may be selected, and the new verdict supersedes the old one

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

A deleted row SHALL be listed on the phase whose deletion removed it and on every phase before that one in the fixed phase order, marked as deleted; the phases after it SHALL NOT list the row at all. The deletion is a decision taken at one step, and the steps that follow stand after it.

The offer to restore a row SHALL be made wherever the row is listed and nowhere else, so that a row can always be brought back from the phase that removed it. Removing the deletion from that phase's manual-edits log SHALL restore the row equally.

A row a merge absorbed SHALL NOT be listed on any phase but Import, whatever phase the merge was decided on: a merge states that two rows are one fencer, which is true of every phase, and it is undone by withdrawing the merge rather than by restoring the row.

Whether a row is listed SHALL NOT change what the sheet holds: a hidden row remains in the projection, in the audit, and in the manual-edits log that names it.

#### Scenario: Delete and restore
- **WHEN** the organizer deletes a withdrawn fencer's row and later restores it
- **THEN** the row disappears from views and exports, then returns with its full history intact

#### Scenario: Gone from the phases that follow
- **WHEN** the organizer deletes a row on Fencers and moves through Matching on HR, Deduplication, Payments and Export
- **THEN** none of those tables lists the row

#### Scenario: Still there where it was deleted
- **WHEN** the organizer returns to Fencers after deleting a row there
- **THEN** the row is listed, struck through, and offers to be restored

#### Scenario: A late deletion leaves the earlier phases alone
- **WHEN** the organizer deletes a row on Payments and then opens Fencers
- **THEN** the row is listed there, struck through, and can be restored from there

#### Scenario: Restoring returns it to every phase
- **WHEN** the organizer restores a row deleted on Fencers
- **THEN** every phase lists it again, unmarked

#### Scenario: The edits log still names a hidden row
- **WHEN** an entry of the Fencers log names a row deleted on Import
- **THEN** the entry still names that row by its fixed number and the fencer's name, though no table on Fencers lists it

#### Scenario: An absorbed row is not listed again
- **WHEN** deduplication merges an imported row into an in-app registration and the organizer opens Fencers
- **THEN** the absorbed row is not listed there, and the Import view still shows it marked as absorbed

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

### Requirement: Fixed fencer number
Every row of the fencer list SHALL carry a number that identifies the fencer within the tournament. The number SHALL be allocated once, when the row first enters the tournament — by registration, by import, or by manual entry — and SHALL NOT change afterwards for any reason: not when the table is sorted, not when an earlier row is deleted or restored, not when a duplicate is merged away, and not when a further import arrives.

A number SHALL NOT be reissued. The number of a row deleted or merged away SHALL remain retired rather than passing to another fencer; a restored row SHALL come back with the number it had.

Clearing the tournament's imported content SHALL be the one exception: the numbers held by the cleared rows SHALL be released, since the tournament is asserting that those rows never existed. No number still held by a row that survives the clear SHALL be reissued.

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

#### Scenario: Manual entry takes the next number
- **WHEN** the organizer enters a fencer by hand into a table whose highest number is forty
- **THEN** that row is numbered forty-one, whatever registration moment it states

#### Scenario: Clearing releases the cleared numbers
- **WHEN** a tournament numbered one to thirty, of which eleven to thirty came from a file, is cleared
- **THEN** the surviving rows keep numbers one to ten and the next row entered is numbered eleven

### Requirement: Order of the fencer list
The fencer list SHALL be ordered by registration moment, earliest first, across all populations together — an imported row, a manually entered row and an in-app registration SHALL interleave by their moments rather than being grouped by origin.

A row whose registration moment is unknown SHALL be placed after every row that states one, and such rows SHALL keep the order in which they were numbered — which for an imported batch is the order of its file. No substitute moment SHALL be invented for them.

#### Scenario: Populations interleave
- **WHEN** an imported row states a registration moment falling between two in-app registrations
- **THEN** it is listed between them

#### Scenario: Rows without a moment sort last
- **WHEN** an imported batch states no registration times
- **THEN** its rows follow every row that has a moment, in the order they appeared in the file

#### Scenario: Backdated manual entry interleaves
- **WHEN** the organizer enters a fencer by hand with a registration moment falling between two existing rows
- **THEN** it is listed between them rather than at the end

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

### Requirement: Manual entry of a fencer
The organizer MAY add a fencer to the fencer list by hand, without a file and without the fencer registering. The action SHALL be offered on the Fencers tab and nowhere else, and SHALL open a dialog rather than an editable blank row — a row is entered whole or not at all.

A manually entered row SHALL be a source record of the tournament in its own right, a third population beside in-app registrations and imported rows. It SHALL take a fixed number when it is entered, SHALL sort by the registration moment it states, SHALL carry its note, and SHALL travel through matching, deduplication and export exactly as an imported row does. It SHALL be editable and deletable by the same means as any other row.

A manually entered row SHALL NOT create an account for the fencer, SHALL NOT be given a variable symbol or a payment instruction, and SHALL NOT cause any mail to be sent. It states who is competing; it does not enrol them in the application.

A manually entered row SHALL NOT appear on the Import view, in any state. The Import view records what a file contained, and a manual entry came from no file.

#### Scenario: Fencer entered at the door
- **WHEN** the organizer enters a fencer by hand on the Fencers tab
- **THEN** one new row joins the fencer list, carrying a fixed number of its own, in the chronological place its registration moment gives it

#### Scenario: Manual entry absent from Import
- **WHEN** the organizer enters a fencer by hand while an imported batch is present
- **THEN** the Import view is unchanged and lists only the file's rows

#### Scenario: Manual entry is not offered on Import
- **WHEN** the organizer opens the Import tab
- **THEN** no manual entry action is offered there

#### Scenario: Manual row deduplicates like any other
- **WHEN** a manually entered fencer shares an hr_id with an imported row
- **THEN** the pair is queued for the organizer's review as a duplicate pair

#### Scenario: Manual row is editable afterwards
- **WHEN** the organizer corrects the club of a manually entered fencer in the table
- **THEN** the correction is recorded in the fencer list's manual-edits log, as it would be for any other row

#### Scenario: No account is created
- **WHEN** a fencer is entered by hand
- **THEN** no account exists for them, no confirmation mail is sent, and no payment instruction is issued

### Requirement: Manual entry fields follow the tournament's structure
The manual entry dialog SHALL offer the tournament's own structure rather than a generic fencer form. Disciplines SHALL be offered as the tournament's own offered individual disciplines, by their names; items to borrow SHALL be offered as the items the tournament lends, by their names; the afterparty SHALL be offered only where the tournament holds one. A choice the tournament does not offer SHALL NOT be presented.

Team disciplines SHALL NOT be offered in the dialog. A team is entered through the tournament's team handling, not by naming a team discipline on a fencer's row.

The dialog SHALL additionally take the fencer's name, nationality, club, HEMA Ratings id, e-mail, a registration moment, and a note. The registration moment SHALL default to the present moment in the tournament's own time zone and SHALL be changeable, so that a form received last week can be entered with the moment it was received.

#### Scenario: Only the offered disciplines appear
- **WHEN** a tournament offers three individual disciplines and one team discipline, and the organizer opens the dialog
- **THEN** the three individual disciplines are offered and the team discipline is not

#### Scenario: Rentals named as the tournament names them
- **WHEN** a tournament lends a mask and a longsword under those names
- **THEN** those are the items the dialog offers to borrow, and no others

#### Scenario: No afterparty, no question
- **WHEN** a tournament holds no afterparty
- **THEN** the dialog asks nothing about one

#### Scenario: Backdated entry
- **WHEN** the organizer changes the registration moment to a date three days ago and submits
- **THEN** the row is listed among the rows registered that day, not among today's

### Requirement: Strict validation of a manual entry
A manual entry SHALL be accepted whole or refused whole. The system SHALL NOT repair, guess at, or silently drop any value the organizer supplied.

A name SHALL be required and SHALL NOT be blank. At least one discipline SHALL be required. A discipline SHALL be one the tournament offers as individual; an item to borrow SHALL be one the tournament lends; a HEMA Ratings id SHALL be a whole number; an e-mail SHALL have the shape of an e-mail address; a registration moment SHALL be a readable moment. Nationality, club, e-mail, HEMA Ratings id and note SHALL be optional and, when left empty, SHALL be recorded as absent rather than as an empty value.

A refusal SHALL name the field it refuses and why, SHALL keep everything else the organizer has typed, and SHALL add no row. A refusal SHALL be shown against the field itself, not only as a summary.

An entry duplicating a fencer already on the list SHALL NOT be refused for that reason: duplicates are the deduplication phase's business, and refusing here would prevent the organizer from recording what actually happened.

#### Scenario: Blank name refused
- **WHEN** the organizer submits with no name
- **THEN** the entry is refused, the name field is marked, and no row is added

#### Scenario: No discipline refused
- **WHEN** the organizer submits without choosing a discipline
- **THEN** the entry is refused and says a discipline is required

#### Scenario: Non-numeric HEMA Ratings id refused
- **WHEN** the organizer types a profile URL into the HEMA Ratings id field
- **THEN** the entry is refused against that field and the rest of the form stands as typed

#### Scenario: Duplicate is allowed through
- **WHEN** the organizer enters a fencer whose name and hr_id match a row already on the list
- **THEN** the row is added, and the pair is left for deduplication to raise

#### Scenario: Empty optional field
- **WHEN** the organizer leaves the club empty
- **THEN** the row is added with no club, and the table shows a dash there

### Requirement: Where the two source actions live
The Import tab's operation panel SHALL carry both actions that concern a file: uploading one and clearing what has been imported. The Fencers tab's panel SHALL carry the manual entry action. Neither tab SHALL carry the other's action, each panel holding only the operation its own phase performs.

#### Scenario: Clear belongs to Import
- **WHEN** the organizer opens the Import tab
- **THEN** the upload and the clear action are both offered in its panel

#### Scenario: Fencers offers entry, not clearing
- **WHEN** the organizer opens the Fencers tab
- **THEN** manual entry is offered and no clear action is

### Requirement: The ledger idiom
Every console phase in which a machine proposes and an organizer ratifies SHALL
present its decision unit as a ledger line carrying three registers together, in
one place, without navigation: the **claim** (what the fencer told us), the
**evidence** (what the consulted source holds), and the **verdict** (what the
system concluded). The decision unit is whatever the decision is about — a row
in Matching, a pair of rows in Deduplication, a pairing of a row and a
transaction in Payments — and the ledger line is rendered wherever that unit
lives; this requirement fixes the registers, not the surface.

No operation SHALL write the claim register. The fencer's own words are rewritten
only by an organizer's field edit; a machine's finding belongs in the evidence
register, never in place of the claim.

Consequences SHALL follow the verdict, not the proposal. Canonical naming, row
absorption, payment binding and every other effect of a decision SHALL fire when
the organizer ratifies, never when the machine proposes. A proposal changes
nothing but the verdict register.

Ratifying the machine's proposal SHALL cost one action on the ledger line
itself. Overriding it SHALL be reachable from the same place. Both SHALL persist
as rules and SHALL therefore be removable, so that a mistaken ratification costs
one undo and leaves a trail.

A distinction the organizer cannot see, the system SHALL NOT draw: where a
verdict distinguishes degrees of machine confidence, the reason for the degree
SHALL be derivable from the difference between the claim and evidence registers
already on screen. A confidence the machine merely asserts is not a ground for
drawing the distinction.

A phase holding a queue of undecided units SHALL state how many remain.

#### Scenario: Proposal does not displace the claim
- **WHEN** a machine proposes a value for a field the fencer supplied
- **THEN** the fencer's value stays in the claim register, the proposed value appears in the evidence register, and both are visible at once

#### Scenario: One action ratifies
- **WHEN** the organizer accepts the proposal on a ledger line
- **THEN** the verdict is recorded in one action, its consequences fire, and the action can be undone

#### Scenario: Unexplainable confidence is not drawn
- **WHEN** a machine reports a confidence that nothing in the claim or evidence registers accounts for
- **THEN** the verdict does not distinguish that unit from any other proposal

#### Scenario: The queue is countable
- **WHEN** units await a verdict in a phase
- **THEN** the phase states how many
