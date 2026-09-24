## MODIFIED Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Matching on HR, Deduplication, Payments, Queue, Export, Teams. Queue stands before Export because it changes who holds a seat, and Export is what leaves the tournament once nothing further changes it. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Deduplication, Teams, Queue and Export SHALL likewise replace the fencer table with their own views, as fixed by **Deduplication candidate review**, `team-disciplines`, `seating-queue` and `export-tables`. The Export tab SHALL present a band of tables derived from the tournament — the fencer list, one per individual discipline, one per extra-item category it offers — rather than one table of its own, and SHALL therefore declare no phase columns. Its fencer table is one tab of that band and remains the fencer table in every respect this requirement fixes.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it that shows a fencer table SHALL show one and the same set of fencers** — every fencer the tournament knows, from in-app registration and from import together — as that set stands at the moment of viewing, minus the rows a removal earlier in the phase order has already taken out of it (Reversible row deletion). A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), the log of manual edits belonging to that phase, and the removals it stands after. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which fencers are listed.

A phase whose operation concerns a small and usually empty subset of the fencers SHALL NOT be given the fencer table for that reason: where the work is a handful of rows out of fifty, listing the fifty states the work in the one place it is hardest to see. Deduplication is such a phase and shows its candidates instead.

Which phases are offered SHALL follow the tournament's settings. The Teams phase SHALL be offered only while the team disciplines feature is on (`tournament-features`). **The Import phase SHALL be offered only on a manual tournament** (`table-import`): an automatic tournament's entrants register in the application or are entered by hand, and neither arrives by file. **The Queue phase SHALL be offered only on an automatic tournament** (`tournament-mode`): a manual tournament never places anyone in a queue, so the phase would hold a capacity mark with nothing to act on. **The Payments phase SHALL be offered on every tournament**, whoever handles its payments: where Squire handles them it holds what it holds today, and where it does not it is boned out to the settled mark alone (`payments`). It is the place a reader looks for who has paid, and that answer SHALL NOT move to another phase depending on a setting the reader may not know about. The remaining phases SHALL always be offered, since they are what every tournament is made of. Whichever phases are offered SHALL keep the fixed order above; a setting removes phases, it never reorders them.

A phase's **columns** SHALL remain a property of that phase. Where a phase's contents follow a tournament's settings, it SHALL be the phase that branches, not its column table — so that no column has to be understood as sometimes present.

A phase the mode does not offer SHALL NOT be reachable by its URL either. Addressing it SHALL open the console on the phase it opens on by default rather than on an empty view, so that a bookmark saved before a feature was turned off still lands somewhere useful.

#### Scenario: Switching phases
- **WHEN** the organizer switches from Matching on HR to Payments
- **THEN** the table re-renders with payment columns and the Payments parameter panel and edits log, over the same fencer list, and the URL names the Payments phase

#### Scenario: Import shows imported rows alone
- **WHEN** a manual tournament has ten registrations entered by other roads and a five-row imported batch, and the organizer opens Import
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

#### Scenario: Deduplication lists candidates, not fencers
- **WHEN** the organizer opens Deduplication on a tournament of fifty fencers among whom the operation raised two candidate groups
- **THEN** the two groups are shown and the fencer table is not, and the fifty fencers remain listed on Fencers

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
- **WHEN** the organizer opens the console of a tournament whose payments setting is off
- **THEN** no Payments phase is offered, and the other phases its mode allows behave as usual

#### Scenario: Teams phase absent without the feature
- **WHEN** the organizer opens the console of a tournament whose team disciplines feature is off
- **THEN** no Teams phase is offered

#### Scenario: Stale bookmark to a hidden phase
- **WHEN** an organizer opens a saved URL naming the Teams phase of a tournament whose team disciplines feature has since been turned off
- **THEN** the console opens on its default phase rather than on an empty Teams view

#### Scenario: Phase reappears with its feature
- **WHEN** the organizer of a tournament that handled its own payments switches it to Squire handling them
- **THEN** the Payments phase, which was present all along, gains the queues, the intake and the transactions in its fixed place between Deduplication and Export — what returns with the setting is the phase's contents, not the phase

#### Scenario: No Import on an automatic tournament
- **WHEN** the organizer opens the console of an automatic tournament, or a saved URL naming its Import phase
- **THEN** no Import phase is offered, and the URL opens the console on its default phase

#### Scenario: Queue before Export
- **WHEN** the organizer reads the phase tabs of an automatic tournament
- **THEN** Queue stands between Payments and Export

#### Scenario: No Queue on a manual tournament
- **WHEN** the organizer opens the console of a manual tournament, or a saved URL naming its Queue phase
- **THEN** no Queue phase is offered, and the URL opens the console on its default phase

#### Scenario: Export is a band of tables
- **WHEN** the organizer opens Export
- **THEN** a band of tables derived from the tournament is shown in place of the single fencer table, and the fencer list is one of its tabs

### Requirement: Manual entry of a fencer
The organizer MAY add a fencer to the fencer list by hand, without a file and without the fencer registering. The action SHALL be offered on the Fencers tab and nowhere else, and SHALL open a dialog rather than an editable blank row — a row is entered whole or not at all.

**What an entry becomes depends on the tournament's mode.** On an **automatic** tournament it SHALL become a registration at once, as `registration` fixes under **A registration entered by hand**: placed against capacity, carrying a variable symbol, and sent nothing. On a **manual** tournament it SHALL be a source record, as follows in the rest of this requirement.

On a manual tournament a manually entered row SHALL be a source record of the tournament in its own right, a third population beside in-app registrations and imported rows. It SHALL take a fixed number when it is entered, SHALL sort by the registration moment it states, SHALL carry its note, and SHALL travel through matching, deduplication and export exactly as an imported row does. It SHALL be editable and deletable by the same means as any other row.

A manual entry SHALL NOT create an account for the fencer, and SHALL NOT cause any mail to be sent, in either mode. **On a manual tournament it SHALL NOT be given a variable symbol or a payment instruction when it is entered.** It states who is competing; entering it does not enrol them in the application.

On a manual tournament a row SHALL become billable when registrations are issued for the fencer list, which happens as a step of payment intake rather than by any action the organizer takes on this phase (`imported-registrations`). Issuing SHALL apply to manually entered rows and imported rows alike — both state who is competing, and neither is enrolled by arriving. Being issued a registration SHALL NOT cause mail to be sent either, and SHALL NOT create an account.

The Fencers phase SHALL NOT offer an action that issues registrations. An organizer reconciling a payment SHALL NOT have to know that issuing exists, and SHALL NOT be sent to another phase to make the roster billable first.

A manually entered row SHALL NOT appear on the Import view, in any state. The Import view records what a file contained, and a manual entry came from no file.

The entry SHALL be offered whenever the tournament is published, including after registration closes and after seating settles: the fencer at the door on the tournament's day is the case it exists for.

#### Scenario: Entered at the door of an automatic tournament
- **WHEN** the organizer of an automatic tournament enters a fencer by hand for a discipline with a free place, before seating settles
- **THEN** a registration is created at once, seated, carrying a variable symbol, and no mail is sent

#### Scenario: Entered after seating settled
- **WHEN** the organizer of an automatic tournament enters a fencer by hand after seating settled
- **THEN** the registration is placed in the queue, from where the organizer may promote it

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

#### Scenario: Entry alone issues no variable symbol
- **WHEN** a fencer is entered by hand on a manual tournament whose payments feature is on
- **THEN** the row carries no variable symbol until the next payment intake issues registrations for the list

#### Scenario: Manual rows are issued alongside imported ones
- **WHEN** a statement is imported against a manual tournament's list holding both imported and manually entered rows
- **THEN** both populations are issued registrations, and neither is sent mail

#### Scenario: The Fencers phase offers no issuing action
- **WHEN** the organizer opens the Fencers tab on a tournament whose rows have no registrations
- **THEN** no action to issue registrations is offered there
