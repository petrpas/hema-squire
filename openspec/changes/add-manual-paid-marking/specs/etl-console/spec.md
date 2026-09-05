## MODIFIED Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Matching on HR, Deduplication, Payments, Export, Teams, Queue. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Deduplication, Teams and Queue SHALL likewise replace the fencer table with their own views, as fixed by **Deduplication candidate review**, `team-disciplines` and `seating-queue`.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it that shows a fencer table SHALL show one and the same set of fencers** — every fencer the tournament knows, from in-app registration and from import together — as that set stands at the moment of viewing, minus the rows a removal earlier in the phase order has already taken out of it (Reversible row deletion). A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), the log of manual edits belonging to that phase, and the removals it stands after. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which fencers are listed.

A phase whose operation concerns a small and usually empty subset of the fencers SHALL NOT be given the fencer table for that reason: where the work is a handful of rows out of fifty, listing the fifty states the work in the one place it is hardest to see. Deduplication is such a phase and shows its candidates instead.

Which phases are offered SHALL follow the tournament's settings. The Teams phase SHALL be offered only while the team disciplines feature is on (`tournament-features`). **The Payments phase SHALL be offered on every tournament**, whoever handles its payments: where Squire handles them it holds what it holds today, and where it does not it is boned out to the settled mark alone (`payments`). It is the place a reader looks for who has paid, and that answer SHALL NOT move to another phase depending on a setting the reader may not know about. The remaining phases SHALL always be offered, since they are what every tournament is made of. Whichever phases are offered SHALL keep the fixed order above; a setting removes phases, it never reorders them.

A phase's **columns** SHALL remain a property of that phase. Where a phase's contents follow a tournament's settings, it SHALL be the phase that branches, not its column table — so that no column has to be understood as sometimes present.

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
- **WHEN** an organizer opens a saved URL naming the Teams phase of a tournament whose team disciplines feature has since been turned off
- **THEN** the console opens on its default phase rather than on an empty Teams view

#### Scenario: The phase fills out again
- **WHEN** the organizer of a tournament that handled its own payments switches it to Squire handling them
- **THEN** the Payments phase, already present, gains the queues, the intake and the transactions in its fixed place between Deduplication and Export

## ADDED Requirements

### Requirement: The Payments phase is boned out where Squire collects nothing
WHERE Squire does not handle a tournament's payments, the Payments phase SHALL hold exactly one thing: whether each registration has been marked settled, and the control that marks and unmarks it (`payments`).

It SHALL hold nothing else. No queue of unmatched or flagged transactions, no intake card, no matching tolerance, no transaction list, no variable symbol, no payment window — none of them has a meaning when no money passes through Squire, and a phase offering a control that answers a refusal is worse than one that does not offer it.

Where Squire does handle the payments the phase SHALL be exactly what it is today, and SHALL NOT carry the settled mark: the state there follows from credited transactions and has one writer.

The phase SHALL state what the mark means where it could mislead: that it records the organizer's word that the money was received, and that Squire has received nothing itself.

**The mark SHALL be a write to the registration, not a rule.** Every other manual edit in the console persists as a rule replayed over the projection, which changes what the table and the export show and reaches nothing else. This mark changes what the registration *is* — the public participant list and the registration's own state depend on it — so it SHALL be written through. The departure SHALL be deliberate and confined to this one action.

#### Scenario: The boned-out phase
- **WHEN** the organizer opens the Payments phase on a tournament that handles its own payments
- **THEN** each row states whether it is marked settled and the mark can be set and unset, and no queue, intake, tolerance or transaction list is offered

#### Scenario: The full phase is unchanged
- **WHEN** the organizer opens the Payments phase on a tournament whose payments Squire handles
- **THEN** it holds what it holds today, and no settled mark is offered

#### Scenario: The mark reaches the registration
- **WHEN** a registration is marked settled and the tournament's public participant list is read
- **THEN** that entrant is shown as confirmed, which no rule over the projection could have achieved
