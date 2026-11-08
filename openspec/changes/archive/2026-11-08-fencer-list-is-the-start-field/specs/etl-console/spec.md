## ADDED Requirements

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
has none.

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
- **WHEN** the organizer reads a member row on the Payments phase
- **THEN** its variable symbol, total, balance and payment state all read as absent, and no payment can be recorded against it

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

### Requirement: Position in the list

Every phase that shows the console's fencer table SHALL state, in the leftmost column
and left of the fencer's own number, the row's position among the rows that stand — one
for the first, rising by one down the table, so that the last number read is how many fencers the view
lists. This is what the fixed number cannot answer: a number names a fencer, carries the
gaps of retired numbers, and stands out of sequence where a backdated row was numbered
late (**Fixed fencer number**). An organizer counting a start field of seventy needs the
count, and counting it by hand down a column of numbers that skips is the work this
column removes.

A row a removal has taken out of the table but which the phase still lists SHALL take no
position: it is not a fencer the tournament has, and the positions of the rows around it
SHALL read as though it were absent. Its own number SHALL stand, struck through with the
rest of the row.

The position SHALL be the table's own reading of itself: it SHALL NOT be stored, SHALL NOT
be carried into an export, and SHALL NOT name a fencer anywhere. A phase listing a subset
of the tournament's rows SHALL count the rows it lists, since the count answers how many
this view holds.

#### Scenario: The count rises by one whatever the numbers
- **WHEN** the organizer reads a fencer list whose rows are numbered seven, twelve and three
- **THEN** the leftmost column reads one, two, three, and the numbers seven, twelve and three stand beside them

#### Scenario: The last position is the size of the field
- **WHEN** the organizer reads a fencer list of sixty-seven standing rows
- **THEN** the last row's position reads sixty-seven

#### Scenario: A removed row takes no position
- **WHEN** a phase lists a deleted row struck through among the rows that stand
- **THEN** that row states no position, the rows after it continue the count unbroken, and its own number is still shown


## MODIFIED Requirements

### Requirement: The teams a row entered, on the fencer list

On a tournament that has a team discipline, the Fencers phase's table SHALL state,
in a column of its own placed directly after Club, the team each row stands in. The
column SHALL be labelled as the team, in both languages the console speaks.

What a row's team is follows from what the row is. **A member row states the team
it fights for** and nothing else: it is on one roster, and that is its place in the
tournament. **A registration row states the teams that registration entered** —
which it may have done while also holding individual entries, and which is a fact
about the contract rather than about where anybody fights. The two readings are
one sentence: the column states the team this row stands in, as a fighter or as an
entry.

A row MAY have entered several teams — in different team disciplines, or more than
one in the same discipline. The cell SHALL state every one of them, one team per
line, in the order the teams were entered.

Where the tournament has **more than one** team discipline, each team SHALL be
named with the discipline it was entered into: there a bare name does not say
which of the tournament's team disciplines this team stands in. Where the
tournament has **one** team discipline, the team SHALL be stated by name alone —
every team is in that discipline, and naming it on every row repeats what the
reader already knows.

A registration row's column SHALL state the teams that registration **entered** —
those billed on it — and no roster it is merely named on. A fencer named on
somebody else's roster SHALL NOT be shown by that row as being in that team; they
are shown by their own member row, which is where they fight.

A row standing in no team SHALL read a dash, on the same terms as an absent club:
an imported row, a row entered by hand, and a registration holding only individual
entries all read a dash rather than an empty cell. A member row SHALL never read a
dash: a member is on a roster by definition.

The column SHALL be read-only. A team's name belongs to the fencer who entered it
and is corrected in that fencer's own roster editor (`team-disciplines`); the cell
SHALL NOT open for editing and an edit to it SHALL NOT be offered, so that the
console never shows a correction the roster never received.

The column SHALL be offered only where the tournament's team disciplines feature is
on and the tournament has at least one team discipline. A tournament with no team
discipline SHALL show the fencer table it shows today, unwidened. In keeping with
**Phase-tabbed fencer table**, this SHALL be a second declared set of columns for
the phase rather than a condition inside one set, so that no column has to be
understood as sometimes present.

The column SHALL belong to the Fencers phase alone. The Export tables, the public
entrants rosters and the read-only Teams view SHALL be unchanged by it.

#### Scenario: The team stands after the club
- **WHEN** the organizer of a tournament with a team discipline opens the Fencers phase
- **THEN** the table's columns read name, nationality, club, team, and then the phase's own columns

#### Scenario: Two teams in two disciplines
- **WHEN** a row's registration entered "Rudá růže" into the longsword team discipline and "Ulice 2" into the sabre team discipline
- **THEN** its team cell states both, each with the discipline it was entered into, one above the other

#### Scenario: The tournament's only team discipline is not named
- **WHEN** the tournament has one team discipline and a row entered "Rudá růže" into it
- **THEN** its team cell reads the name alone, without the discipline

#### Scenario: Two teams in one discipline
- **WHEN** a row's registration entered two teams into the same team discipline, on a tournament that has another team discipline as well
- **THEN** its team cell states both, each naming that discipline, in the order they were entered

#### Scenario: A row that entered no team
- **WHEN** the row holds only individual entries, or arrived by import, or was entered by hand
- **THEN** its team cell reads a dash

#### Scenario: A roster member is not a team entry
- **WHEN** a fencer holds a registration of their own and is also named on a team another fencer entered
- **THEN** their registration row does not state that team, and their member row does

#### Scenario: A member row states the team it fights for
- **WHEN** the organizer reads the fencer list of a tournament with two team disciplines
- **THEN** each member row states its own team with that team's discipline, and no member row reads a dash

#### Scenario: The cell does not open
- **WHEN** the organizer clicks a team cell on the Fencers phase
- **THEN** nothing opens for editing, and the manual-edits log gains no entry

#### Scenario: No team discipline, no column
- **WHEN** the organizer of a tournament whose team disciplines feature is off, or which has the feature on but no team discipline configured, opens the Fencers phase
- **THEN** the table has no team column, and the columns read name, nationality, club, and then the phase's own

### Requirement: Phase-tabbed fencer table
The organizer console SHALL present phase tabs in the fixed order Setup, Import, Fencers, Teams, Matching on HR, Deduplication, Payments, Queue, Export. Teams stands immediately after Fencers because the two are read together: Fencers lists who will fight, Teams lists the entries those fighters fight under, and a reader moving between them is answering one question. Queue stands before Export because it changes who holds a seat, and Export is what leaves the tournament once nothing further changes it. Every tab, including Setup, SHALL be clickable from every other tab. Selecting a phase tab SHALL change the console's URL to that phase and push a browser history entry, so that Back returns to the previously open phase and a reload reopens the phase on display. The Setup tab (step 0) SHALL present the tournament configuration — identity fields, titular organizers, disciplines, registration window, pricing, and the completeness checklist — instead of a fencer table. Deduplication, Teams, Queue and Export SHALL likewise replace the fencer table with their own views, as fixed by **Deduplication candidate review**, `team-disciplines`, `seating-queue` and `export-tables`. The Export tab SHALL present a band of tables derived from the tournament — the fencer list, one per individual discipline, one per extra-item category it offers — rather than one table of its own, and SHALL therefore declare no phase columns. Its fencer table is one tab of that band and remains the fencer table in every respect this requirement fixes.

**The Import tab SHALL show imported rows alone.** In-app registrations SHALL NOT appear there, whatever their state.

**The Fencers tab and every processing tab after it that shows a fencer table SHALL show one and the same set of fencers** — every fencer who will fight, as **The fencer list is the tournament's start field** fixes: the fencers of in-app and imported registrations, those entered by hand, and every member of every team's roster — as that set stands at the moment of viewing, minus the rows a removal earlier in the phase order has already taken out of it (Reversible row deletion). A phase tab SHALL NOT present a state frozen as of some earlier operation; what distinguishes one from another is the columns it shows, the parameter panel of the operation it runs (general rules), the log of manual edits belonging to that phase, and the removals it stands after. A phase whose operation has already run and one whose operation has not therefore differ in what the rows say, never in which fencers are listed.

Deduplication is the one tab after Fencers whose population differs, and it differs because it shows candidate groups rather than the fencer table at all; which rows may become candidates is fixed by **The fencer list is the tournament's start field**.

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

### Requirement: Fixed fencer number
Every row of the fencer list SHALL carry a number that identifies the fencer within the tournament. The number SHALL be allocated once, when the row first enters the tournament — by registration, by import, by manual entry, or by being added to a team's roster — and SHALL NOT change afterwards for any reason: not when the table is sorted, not when an earlier row is deleted or restored, not when a duplicate is merged away, and not when a further import arrives.

A number SHALL NOT be reissued. The number of a row deleted or merged away SHALL remain retired rather than passing to another fencer; a restored row SHALL come back with the number it had.

Clearing the tournament's imported content SHALL be the one exception: the numbers held by the cleared rows SHALL be released, since the tournament is asserting that those rows never existed. No number still held by a row that survives the clear SHALL be reissued.

The number SHALL be allocated in the order rows enter the tournament, which is not necessarily the order the table displays. Where an imported row states a registration moment earlier than that of rows already numbered, the table SHALL sort it into its chronological place and its number SHALL stand out of sequence there. The number counts nobody's position in the list; it names a fencer.

Every view SHALL number its rows by this number, the Import view included. No view SHALL number rows by their line in an uploaded file: a line number describes a file, and the Import view describes what the tournament imported across every file it was given. Import's numbers SHALL therefore be those of the tournament, gaps and all, where rows of other populations were numbered between them.

#### Scenario: Deletion does not renumber
- **WHEN** the organizer deletes the third row of a fifteen-row table
- **THEN** the remaining rows keep the numbers they had, and no number moves up

#### Scenario: Merge retires a number
- **WHEN** two rows are merged and the absorbed row disappears
- **THEN** the surviving row keeps its own number and the absorbed row's number is used by no one

#### Scenario: Backdated import numbers out of sequence
- **WHEN** an import brings a fencer whose registration moment precedes existing rows
- **THEN** that row is displayed among the earliest rows while carrying a number higher than theirs

#### Scenario: Import shows the tournament's numbers
- **WHEN** the organizer opens the Import view of a tournament whose imported rows are numbered three, four, seven and eight, in-app registrations holding the rest
- **THEN** those four rows are shown numbered three, four, seven and eight, and no numbering starts again at one

#### Scenario: A second upload continues the numbering
- **WHEN** a second file brings four rows to a tournament numbered one to thirty
- **THEN** they are numbered thirty-one to thirty-four, and the rows of the first file keep the numbers they had

#### Scenario: Manual entry takes the next number
- **WHEN** the organizer enters a fencer by hand into a table whose highest number is forty
- **THEN** that row is numbered forty-one, whatever registration moment it states

#### Scenario: Clearing releases the cleared numbers
- **WHEN** a tournament numbered one to thirty, of which eleven to thirty came from a file, is cleared
- **THEN** the surviving rows keep numbers one to ten and the next row entered is numbered eleven

#### Scenario: A roster member is numbered when it is added
- **WHEN** a fencer adds a member to a team's roster
- **THEN** that member carries a number of its own from then on, and removing and restoring it returns the same number

### Requirement: Order of the fencer list
The fencer list SHALL be ordered by registration moment, earliest first, across all populations together — an imported row, a manually entered row and an in-app registration SHALL interleave by their moments rather than being grouped by origin.

A roster member's moment SHALL be the moment its team's registration was made, and members of one team SHALL be ordered among themselves by their place in the roster. A team therefore stands together in the list, at the moment the team entered, rather than scattering by when each member happened to be typed in. This is the team's own moment, not an invented one.

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

#### Scenario: A team stands together
- **WHEN** a team entered between two individual registrations has four members added over several days
- **THEN** the four are listed together, in roster order, between those two registrations
