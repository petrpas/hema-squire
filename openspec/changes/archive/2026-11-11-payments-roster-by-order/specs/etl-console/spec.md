## MODIFIED Requirements

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Teams, Matching on HR, Deduplication, Payments, Queue, Export. Teams stands immediately after Fencers because the two are read together: Fencers lists who will fight, Teams lists the entries those fighters fight under, and a reader moving between them is answering one question. Queue stands before Export because it changes who holds a seat, and Export is what leaves the tournament once nothing further changes it. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Deduplication, Teams, Queue and Export SHALL likewise replace the fencer table with their own views, as fixed by **Deduplication candidate review**, `team-disciplines`, `seating-queue` and `export-tables`. The Export tab SHALL present a band of tables derived from the tournament — the fencer list, one per individual discipline, one per extra-item category it offers — rather than one table of its own, and SHALL therefore declare no phase columns. Its fencer table is one tab of that band and remains the fencer table in every respect this requirement fixes.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it that shows a fencer table SHALL show one and the same set of fencers** — every fencer who will fight, as **The fencer list is the tournament's start field** fixes: the fencers of in-app and imported registrations, those entered by hand, and every member of every team's roster — as that set stands at the moment of viewing, minus the rows a removal earlier in the phase order has already taken out of it (Reversible row deletion). **Payments is the one exception among the tabs that show a fencer table:** it SHALL list that same set without its roster member rows, together with every registration whose holder fights nothing, because what it reads is orders and a member row holds none (**The fencer list is the tournament's start field**). On a tournament with no team discipline the two sets are the same, so Payments lists exactly what Fencers lists. A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), the log of manual edits belonging to that phase, and the removals it stands after. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which fencers are listed.

Deduplication is the other tab after Fencers whose population differs. It differs because it shows candidate groups rather than the fencer table at all; which rows may become candidates is fixed by **The fencer list is the tournament's start field**.

A phase whose operation concerns a small and usually empty subset of the fencers SHALL NOT be given the fencer table for that reason: where the work is a handful of rows out of fifty, listing the fifty states the work in the one place it is hardest to see. Deduplication is such a phase and shows its candidates instead.

Which phases are offered SHALL follow the tournament's settings. The Teams phase SHALL be offered only while the team disciplines feature is on (`tournament-features`). **The Import phase SHALL be offered only on a manual tournament** (`table-import`): an automatic tournament's entrants register in the application or are entered by hand, and neither arrives by file. **The Queue phase SHALL be offered only on an automatic tournament** (`tournament-mode`): a manual tournament never places anyone in a queue, so the phase would hold a capacity mark with nothing to act on. **The Payments phase SHALL be offered on every tournament**, whoever handles its payments: where Squire handles them it holds what it holds today, and where it does not it is boned out to the settled mark alone (`payments`). It is the place a reader looks for who has paid, and that answer SHALL NOT move to another phase depending on a setting the reader may not know about. The remaining phases SHALL always be offered, since they are what every tournament is made of. Whichever phases are offered SHALL keep the fixed order above; a setting removes phases, it never reorders them.

A phase's **columns** SHALL remain a property of that phase. Where a phase's contents follow a tournament's settings, it SHALL be the phase that branches, not its column table — so that no column has to be understood as sometimes present.

A phase the mode does not offer SHALL NOT be reachable by its URL either. Addressing it SHALL open the console on the phase it opens on by default rather than on an empty view, so that a bookmark saved before a feature was turned off still lands somewhere useful.

#### Scenario: Switching phases
- **WHEN** the organizer switches from Matching on HR to Payments
- **THEN** the table re-renders with payment columns and the Payments parameter panel and edits log, over the same fencer list less its roster member rows, and the URL names the Payments phase

#### Scenario: Import shows imported rows alone
- **WHEN** a manual tournament has ten registrations entered by other roads and a five-row imported batch, and the organizer opens Import
- **THEN** the five imported rows are listed and none of the ten registrations is

#### Scenario: Fencers shows both populations
- **WHEN** the same organizer opens Fencers
- **THEN** all fifteen rows are listed together

#### Scenario: Teams stands beside Fencers
- **WHEN** an organizer of a tournament with a team discipline reads the phase tabs
- **THEN** Teams is the tab immediately after Fencers

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

#### Scenario: Payments lists orders on a team tournament
- **WHEN** a tournament holds sixteen registrations, each entering one team, and the rosters of those teams hold fifty-nine members, among them the sixteen holders
- **THEN** Fencers lists fifty-nine rows, and Payments lists sixteen rows, one per registration

### Requirement: The fencer list is the tournament's start field

The fencer list SHALL be the list of everyone who will fight: the fencer of every
registration holding an individual entry, every imported and hand-entered row,
and **every member of every team's roster**. A roster member SHALL therefore be a
row of the console's projection, alongside the three populations the list already
carries.

A registration that holds no individual entry — one whose whole content is team
entries — SHALL NOT be listed, and its holder SHALL NOT appear as a fencer on the
strength of having entered a team. Entering a team is not fighting: the roster's
prefill is a convenience and marks no role (`team-disciplines`). Such a
registration SHALL remain fully present where its agenda is — the Teams phase,
Payments, and the Queue — so that nothing about it becomes unreachable.

**A member row SHALL carry what a fighter has and nothing a contract has.** It
SHALL state a name, nationality, club, the HEMA Ratings identifier claimed for
it, the evidence and verdict standing against that claim, the team it fights for
and that team's discipline, and a fixed number of its own. It SHALL NOT state a
variable symbol, a total, an outstanding balance, a payment state, an expiry, a
seat or a queue place: a member holds no registration, and a cell that would
state one SHALL read as absent in the idiom the list already uses for a row that
has none. **A member row SHALL NOT be listed on Payments at all**: that phase reads orders, and a member row is none. The money of the team the member fights for is read on the registration that entered it.

A member row's Disciplines cell SHALL state its team's discipline, faded and never
open for editing, so the start field reads a discipline on every fighter. The
statement SHALL be the cell's alone: what the row entered stays empty, so no export
tab, count or rating reads the member as having entered the discipline itself. A
registration row's cell SHALL NOT state the disciplines of the teams it entered, since
entering a team is not fighting in it.

**A row SHALL offer the actions its own registration gives it, and no others.**
A row holding a live registration SHALL keep what it has today: correcting the
disciplines and items that registration bought, cancelling it, and handing it to
somebody else. A member row SHALL offer none of those, because it holds no
registration to correct, cancel or hand over; the agenda of the registration a
team was entered on SHALL be offered on that team, in the Teams phase. What a
member row SHALL offer is what a fighter has: its identity, correctable as every
other row's identity is, and its HEMA Ratings binding.

Replacing a fighter SHALL NOT be an action of the fencer list. Handing over a
registration and replacing a member of a roster are different acts on different
things, and the roster has one editor, in the Teams phase.

**Matching SHALL reach member rows.** The identifier an entrant typed into a
roster SHALL be read as a claim, exactly as a registration's own identifier is;
the fighters index SHALL answer it as evidence; and the organizer's verdict SHALL
be recorded as the verdict on any other row is. The ratings snapshot SHALL fetch
for every identifier the projection carries, not for registrations alone.

**Deduplication SHALL NOT take a member row as a candidate.** Two rosters naming
one person are two places in two competitions rather than one record entered
twice, and a member row standing beside the registration row of the fencer who
entered its team is one person in two roles. Neither is a duplicate, and merging
either would destroy a fact rather than a repetition. Deduplication shows
candidate groups rather than the fencer list, so excluding these rows removes
nothing from what that phase shows.

#### Scenario: The start field is everyone who fights
- **WHEN** a tournament holds eighteen registrations, each entering one team, and those teams' rosters hold sixty-seven members between them
- **THEN** the fencer list states sixty-seven rows

#### Scenario: A fencer who entered a team but fights nothing
- **WHEN** such a registration's holder is on no roster
- **THEN** they are not listed as a fencer, and their registration is still listed on Teams, Payments and the Queue

#### Scenario: A fencer who both fights individually and is on a roster
- **WHEN** a fencer holds a registration with two individual entries and is also named on a team's roster
- **THEN** they occupy two rows: the registration's, stating its disciplines and money, and the roster's, stating the team

#### Scenario: A member row states no money
- **WHEN** the organizer opens the Payments phase of a tournament whose rosters hold members
- **THEN** no member row is listed there. Every money cell a member row would carry has nowhere to stand, and no payment can be recorded against a member

#### Scenario: A member row offers no cancellation
- **WHEN** the organizer opens the row actions of a member row
- **THEN** neither cancellation nor deletion nor handing over a registration is offered

#### Scenario: A member is matched like anybody else
- **WHEN** the organizer opens Matching on a tournament whose rosters hold sixty-seven members
- **THEN** each member is a row with its claimed identifier, the index's evidence beside it, and a verdict to give

#### Scenario: The snapshot reaches the fighters
- **WHEN** a ratings snapshot is taken
- **THEN** the identifiers of matched roster members are fetched with everyone else's

#### Scenario: Two rosters naming one person are not duplicates
- **WHEN** two teams in different disciplines each name the same fighter and both are matched to the same profile
- **THEN** deduplication offers no candidate group for them and both rows stand

#### Scenario: A member beside their own entrant's registration
- **WHEN** a fencer enters a team and is also the first member of its roster
- **THEN** the registration row and the member row both stand, and deduplication offers neither against the other
