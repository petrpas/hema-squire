## ADDED Requirements

### Requirement: Deduplication candidate review
The Deduplication phase SHALL present the tournament's candidate duplicate
groups in place of the fencer table, and SHALL list nothing else: a fencer no
candidate names is not this phase's business, and listing them all states the
work in the one place it is hardest to see.

Each candidate group SHALL be presented as a table of its own, one row per member
record, stating that record's fixed number, its identity per **HR identity in the
phases after matching**, its email, its registration moment, its disciplines, its
weapon rentals, its afterparty and its note. Beneath the members, separated by a
rule, the group SHALL state its **conclusion**: the merged record the system
recommends, in the same columns as the members, so that what a merge would keep
and what it would drop are read down one column. The group SHALL name what raised
it — the HEMA Ratings id its records share, or the classifier's band — and SHALL
carry the merge note prepared for it.

The conclusion SHALL be editable before it is confirmed. An editable cell SHALL
offer the members' own values for that field as choices and SHALL accept a value
typed in. A field holding a list SHALL be edited by including or excluding each
value the members carry between them. The merge note SHALL be editable as prose.
Confirming SHALL record the conclusion as the organizer left it, never the
recommendation it started from. The HEMA Ratings id SHALL NOT be editable in the
conclusion: binding a profile is Matching's verdict and is reached there.

Every group SHALL carry one of three verdicts and SHALL state which: awaiting a
decision, merged, or kept separate. A group SHALL read as merged while a merge
rule for it stands and SHALL NOT read as merged otherwise, so that withdrawing
the merge from the manual-edits log returns the group to those awaiting a
decision rather than leaving it settled and unmerged. A group merged by the
operation itself SHALL be listed with the rest, stating that the machine decided
it.

From any group, whatever its verdict, the organizer SHALL be able to reach the
opposite verdict in one action, and to reopen the conclusion, edit it, and
confirm it again. Confirming a merge SHALL replace whatever merge stood for that
group rather than adding a second one.

The phase SHALL state how many groups await a decision. Where none does — the
ordinary case — it SHALL say so in one sentence and offer the operation's run,
rather than presenting an empty table. The phase's rail SHALL keep the run
control and the phase's manual-edits log, as every processing phase does.

Groups the operation discarded as too weak to raise SHALL NOT be listed: they
exist to keep false positives off the screen, and listing them would return them
to it.

A merge SHALL read in the manual-edits log as **one entry**, as a match
resolution does. The values the merge decided, the merge note it recorded and the
absorption it performed are one decision by one organizer; as separate entries
they report a single click once for every field that happened to differ, and a
field that merged one empty value onto another reports a change that changed
nothing. The entry SHALL state the absorption — which row went into which — and
the values SHALL be applied without appending to the log. Undoing that entry
SHALL reverse the whole merge, values included.

#### Scenario: Only candidates are listed
- **WHEN** the operation has raised two candidate groups among fifty fencers and the organizer opens Deduplication
- **THEN** two group tables are shown, and the forty-six fencers no group names appear nowhere on the phase

#### Scenario: A group states its members and its conclusion together
- **WHEN** the organizer opens a group of two records, one carrying a club and the other a later note
- **THEN** both records are listed as rows, and beneath them the conclusion states the merged record in the same columns, with the merge note

#### Scenario: Choosing a member's value
- **WHEN** the organizer opens the conclusion's name cell of a group whose records read `Jan Novák` and `Novák Jan`
- **THEN** both spellings are offered as choices, and choosing one puts it in the conclusion

#### Scenario: Typing a value the members do not carry
- **WHEN** the organizer types a name into the conclusion's name cell that neither record spelled
- **THEN** the typed value stands in the conclusion, and confirming records it

#### Scenario: A list field is edited by inclusion
- **WHEN** one record entered longsword and the other longsword and rapier
- **THEN** the conclusion offers both disciplines, each removable, and confirms with those left in

#### Scenario: An edited conclusion is what takes effect
- **WHEN** the organizer edits the recommended club and confirms the merge
- **THEN** the surviving record carries the edited club, not the recommended one

#### Scenario: The id is not rebound here
- **WHEN** the organizer clicks the HEMA Ratings id cell of a conclusion
- **THEN** no edit opens

#### Scenario: An automatic merge is visible
- **WHEN** the operation merged a group of its own accord
- **THEN** the group is listed as merged, stating that the machine decided it

#### Scenario: An automatic merge is one action from being undone
- **WHEN** the organizer disagrees with such a merge and asks for the records to be kept separate
- **THEN** the merge is withdrawn, the records stand apart again, and the group reads as kept separate by the organizer

#### Scenario: Withdrawing a merge in the log reopens the group
- **WHEN** the organizer removes a merge from the phase's manual-edits log
- **THEN** the group returns to those awaiting a decision and is counted again

#### Scenario: A settled group can be decided again
- **WHEN** the organizer opens a group kept separate earlier and merges it
- **THEN** the merge takes effect and the group reads as merged, without a second merge standing beside the first

#### Scenario: A merge reads as one entry
- **WHEN** the organizer confirms a merge that changed a club, wrote a merge note and absorbed a row
- **THEN** the phase's log carries a single entry for that decision, naming the absorption, and no entry for any field the merge decided

#### Scenario: A field that changed nothing says nothing
- **WHEN** a merged field replaces one empty value with another
- **THEN** no entry reports it

#### Scenario: Undoing the entry undoes the whole merge
- **WHEN** the organizer removes that entry from the log
- **THEN** the absorbed row returns, the merged values are gone from the survivor, and the group awaits a decision again

#### Scenario: Nothing to decide
- **WHEN** no candidate group stands
- **THEN** the phase says so in one sentence and offers the run, showing no table

## MODIFIED Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Matching on HR, Deduplication, Payments, Export, Teams, Queue. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Deduplication, Teams and Queue SHALL likewise replace the fencer table with their own views, as fixed by **Deduplication candidate review**, `team-disciplines` and `seating-queue`.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it that shows a fencer table SHALL show one and the same set of fencers** — every fencer the tournament knows, from in-app registration and from import together — as that set stands at the moment of viewing, minus the rows a removal earlier in the phase order has already taken out of it (Reversible row deletion). A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), the log of manual edits belonging to that phase, and the removals it stands after. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which fencers are listed.

A phase whose operation concerns a small and usually empty subset of the fencers SHALL NOT be given the fencer table for that reason: where the work is a handful of rows out of fifty, listing the fifty states the work in the one place it is hardest to see. Deduplication is such a phase and shows its candidates instead.

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

### Requirement: Per-row phase status
Processing status SHALL be tracked per row, not globally. A row originating from in-app registration SHALL enter structured and HR-bound — it belongs to the fencer list from the moment it is created and SHALL never appear in the Import view — so Matching is satisfied for it at birth. An imported row SHALL enter unstructured and unmatched and SHALL traverse matching and deduplication. A manually entered row SHALL enter structured, its fields having been chosen from the tournament's own structure, but unmatched unless the organizer supplied a HEMA Ratings id, and SHALL traverse matching and deduplication as an imported row does.

The three populations SHALL coexist in one table without being separated: a phase showing the fencer table SHALL NOT hide rows for which its operation is already satisfied, and SHALL NOT group or mark rows by which population they came from beyond what the Import view's own scope already implies. A phase that shows no fencer table is not selecting among the fencers by their status; it is not listing them at all, and this requirement says nothing about it.

#### Scenario: Mixed table
- **WHEN** the table contains native registrations and freshly imported rows
- **THEN** native rows show as matched while imported rows still await matching, in the same view

#### Scenario: Registration never appears in Import
- **WHEN** a fencer registers in the application while an imported batch is present
- **THEN** their row joins the fencer list and the Import view is unchanged

#### Scenario: A phase without a fencer table selects nothing
- **WHEN** the organizer opens Deduplication, where only candidate groups are shown
- **THEN** no row is hidden for having satisfied the operation, because no fencer table is presented from which to hide it

#### Scenario: Manual row awaits matching
- **WHEN** a fencer is entered by hand without a HEMA Ratings id
- **THEN** their row appears on the fencer list awaiting matching, beside imported rows in the same state

### Requirement: HR identity in the phases after matching
On every phase after Matching — Deduplication, Payments and Export — the three
identity columns (name, nationality, club) of every row those phases display
SHALL state the values of the HEMA Ratings profile the row is bound to, not the
values the fencer registered under or an import file spelled. On Payments and
Export those rows are the fencer table's; on Deduplication they are the member
rows and the conclusion row of each candidate group. The profile's nationality SHALL be stated as the
two-letter ISO country code, the same reading the Matching evidence register
uses, so that one identity column speaks one vocabulary down its whole length.

Where a row is bound to no profile — never matched, or resolved as having none —
those columns SHALL state the registered name, nationality and club, rendered in
italic. The italic SHALL be the whole of the marking: no dash, no badge, no
second column. A row without a profile therefore stays identifiable and stays
comparable against its neighbours, while a reader can see at a glance which lines
of the table the profile stands behind.

The identity columns SHALL be read-only on those phases, whether HR-backed or
italic. An HR-backed value belongs to the profile and is changed by rebinding the
id on Matching; a registered value is corrected where it is claimed, on the
fencer list or on Import. Identity cells SHALL remain editable on Import, on the
fencer list and on Matching, as they are today.

The conclusion row of a deduplication candidate group is the one exception, and
only where no profile stands behind the group: choosing which registered
spelling the merged record keeps is the merge's own decision and is taken
nowhere else. Where the group's records are bound to a profile, its identity
cells state the profile's values and stay read-only like every other cell of
these phases.

Matching itself SHALL keep the claim-beside-evidence layout fixed by **HR
matching review** unchanged: the registered values and the HR register are shown
side by side there, because comparing them is what the phase is for.

#### Scenario: A matched row is identified by its profile
- **WHEN** the organizer opens Deduplication on a candidate group whose records are bound to a profile reading `Lukas Mueller`, `Germany`, `Berlin Schwert`, registered as `Lukáš Müller`, `DE`, `Berlin`
- **THEN** the group's member rows and its conclusion read `Lukas Mueller`, `DE`, `Berlin Schwert`, upright

#### Scenario: An unmatched row keeps its own words
- **WHEN** the organizer opens Deduplication on a candidate group no profile is bound to
- **THEN** its member rows state the name, nationality and club each record registered under, in italic, and not an em dash

#### Scenario: One vocabulary down the identity column
- **WHEN** two matched rows sit side by side and the index spells one country in English and the other as a code
- **THEN** both nationality cells read the two-letter ISO code

#### Scenario: The same reading on every later phase
- **WHEN** the organizer moves from Deduplication to Payments and on to Export
- **THEN** each phase identifies the row the same way, HR-backed values upright and registered values in italic

#### Scenario: Identity is not rewritten after matching
- **WHEN** the organizer clicks a name, nationality or club cell of the fencer table on Payments or Export, or of a member row on Deduplication
- **THEN** no edit opens, and no field-edit rule can be created from those cells on those phases

#### Scenario: A bound group's identity is not the merge's to decide
- **WHEN** the organizer opens the conclusion of a candidate group whose records are bound to a profile and clicks its name cell
- **THEN** no edit opens, and the cell states the profile's name

#### Scenario: An unbound group's identity is the merge's to decide
- **WHEN** the organizer opens the conclusion of a candidate group no profile is bound to and clicks its name cell
- **THEN** the cell opens, offering each member's registered spelling and accepting one typed in

#### Scenario: Corrections still have their place
- **WHEN** the organizer clicks the same fencer's name cell on the fencer list
- **THEN** the cell opens for editing as before, and the correction persists as a rule

#### Scenario: Matching still compares claim against evidence
- **WHEN** the organizer opens Matching on a row whose registered club differs from the matched profile's
- **THEN** both the registered values and the HR register are visible on the row at once, unchanged by this requirement

#### Scenario: Resolving a match changes how later phases read the row
- **WHEN** the organizer binds a profile to a row that had none and then opens Payments
- **THEN** the row's identity columns state the profile's values, upright, where they had been the registered ones in italic

### Requirement: Reversible row deletion
Deleting a row SHALL be a manual, reversible operation: the row is excluded from active views and exports but remains restorable. Both deletion and restoration SHALL persist as rules.

A deleted row SHALL be listed on the phase whose deletion removed it and on every phase before that one in the fixed phase order, marked as deleted; the phases after it SHALL NOT list the row at all. The deletion is a decision taken at one step, and the steps that follow stand after it.

The offer to restore a row SHALL be made wherever the row is listed and nowhere else, so that a row can always be brought back from the phase that removed it. Removing the deletion from that phase's manual-edits log SHALL restore the row equally.

A phase that lists no fencer table neither removes rows nor lists removed ones, and no deletion SHALL be attributed to it. A deleted row SHALL NOT be raised as a deduplication candidate, and a candidate group SHALL lose a member a deletion took out of the table.

A row a merge absorbed SHALL NOT be listed on any phase but Import, whatever phase the merge was decided on: a merge states that two rows are one fencer, which is true of every phase, and it is undone by withdrawing the merge rather than by restoring the row.

Whether a row is listed SHALL NOT change what the sheet holds: a hidden row remains in the projection, in the audit, and in the manual-edits log that names it.

#### Scenario: Delete and restore
- **WHEN** the organizer deletes a withdrawn fencer's row and later restores it
- **THEN** the row disappears from views and exports, then returns with its full history intact

#### Scenario: Gone from the phases that follow
- **WHEN** the organizer deletes a row on Fencers and moves through Matching on HR, Payments and Export
- **THEN** none of those tables lists the row

#### Scenario: A deleted row is no longer a duplicate of anything
- **WHEN** the organizer deletes one of two rows a deduplication candidate group named, and opens Deduplication
- **THEN** the group no longer stands as a candidate

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

### Requirement: The ledger idiom
Every console phase in which a machine proposes and an organizer ratifies SHALL
present its decision unit as a ledger line carrying three registers together, in
one place, without navigation: the **claim** (what the fencer told us), the
**evidence** (what the consulted source holds), and the **verdict** (what the
system concluded). The decision unit is whatever the decision is about — a row
in Matching, a candidate group of rows in Deduplication, a pairing of a row and
a transaction in Payments — and the ledger line is rendered wherever that unit
lives; this requirement fixes the registers, not the surface. Where the unit is a
group, the verdict register SHALL state the record the decision would produce, in
the same terms as the claim register, so that the two are read against each
other rather than described to the organizer.

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
one undo and leaves a trail. Where the verdict register states a record rather
than a single value, correcting that record before ratifying SHALL be possible on
the ledger line itself, and what is ratified SHALL be the record as corrected.

Where a capability spec grants a machine a verdict of its own — a finding so
strong that waiting for a human costs more than it protects — that verdict is
not exempt from this requirement, only from the ratification. It SHALL be listed
among the phase's decision units, stated as the machine's rather than the
organizer's, and the opposite verdict SHALL cost one action, as ratifying costs
one. A consequence a machine applied and did not show is what this permission
must not become.

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

#### Scenario: A machine's own verdict is stated, not hidden
- **WHEN** an operation applies a verdict of its own without asking the organizer
- **THEN** the unit is listed with the phase's other decision units, stating that the machine decided it, and one action reaches the opposite verdict

#### Scenario: The record is corrected before it is ratified
- **WHEN** the verdict register proposes a record and the organizer changes one of its values before accepting
- **THEN** the record as changed is what the verdict records, and the machine's proposal is not what takes effect

#### Scenario: The queue is countable
- **WHEN** units await a verdict in a phase
- **THEN** the phase states how many
