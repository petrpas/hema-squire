## MODIFIED Requirements

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
