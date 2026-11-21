## MODIFIED Requirements

### Requirement: The fencer list is the tournament's start field

The fencer list SHALL be the list of everyone who will fight: the fencer of every
registration holding an individual entry, every imported and hand-entered row,
and **every member of every team's roster**. A roster member SHALL therefore be a
row of the console's projection, alongside the three populations the list already
carries.

Only a team that will fight puts its fighters on the list. **The members of a team
whose entering registration has expired or been cancelled SHALL NOT be listed**,
whether or not the team was seated, because neither kind of team fights. A team
cancelled alone already takes its members off the list (`team-disciplines`,
Cancelling one team), and a team whose registration lapsed SHALL do the same. The
registration's own row, where the registration holds an individual entry, SHALL
stay listed and state its state as it does today. Where the organizer still reads
such a team is the Teams and Queue phases (`team-disciplines`, `seating-queue`). A
registration reinstated by a late payment SHALL bring its members back, each under
the fixed number it already holds.

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

#### Scenario: A lapsed team's fighters leave the start field
- **WHEN** a registration holding one individual entry and one team of four expires unpaid
- **THEN** the four member rows are no longer listed, and the registration's row stands stating that its reservation expired

#### Scenario: Reinstated, the fighters return
- **WHEN** that registration is reinstated by a payment within the grace period
- **THEN** the four member rows are listed again, each under the number it held before

