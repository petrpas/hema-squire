## MODIFIED Requirements

### Requirement: Organizer's teams view
The console SHALL present, per team discipline, the teams entered into it: the team name, the entering fencer, the roster in order with each member's name and — where bound — HEMA Ratings identifier, club, and nationality, the member count, and which teams are waitlisted and in what order. Teams marked below minimum after the composition deadline SHALL be distinguished.

The view SHALL be offered only while the tournament's team disciplines feature is on, as fixed by `tournament-features`. An organizer who has turned the feature off SHALL see no Teams phase; the teams, rosters and waitlist positions it would have shown SHALL be retained untouched and SHALL be shown again when the feature is turned back on. The entering fencer's own roster editor on the tournament detail page SHALL be unaffected by the feature, which governs the organizer's console alone.

**The view SHALL let the organizer edit a roster**: add a member, remove one, restore a removed one, and correct a member's name, HEMA Ratings identifier, club or nationality. A team arrives at the tournament and the fencer who entered it cannot always reach their own editor; the organizer acting for them is the remedy, and it is a safe one — a roster edit moves no money, as **Roster editing changes no money** fixes. Every such edit SHALL be recorded as **Every roster change is recorded in one log** fixes, and the log SHALL be shown beside the roster.

**The view SHALL be a table**, one row per team, read the way the fencer list is read: the team's name, the fencer who entered it, the address mail about that registration goes to (`outgoing-mail`), the extra items that registration bought, its member count, and the payment standing of the registration it was entered on. The waitlisted teams SHALL stand below a capacity line, in waitlist order, as the public roster draws them; the line SHALL be drawn only where a team waits, and no column SHALL state a waitlist position, since the line says which teams wait and the rows' order says in what order. The table SHALL count its rows in a gutter, as **Position in the list** (`etl-console`) draws it: the seated teams from one, and below the line the waitlisted teams from one again, so each waiting team's count is its place on the waitlist, as the public roster numbers it. The member count and the payment standing SHALL be centred in their columns. The table SHALL list one team discipline at a time and SHALL NOT state the discipline as a column: where the tournament offers two or more team disciplines, tabs under the view's heading SHALL choose the discipline, each counting its teams; where it offers one, no tabs SHALL be drawn, since most tournaments hold a single team discipline. The count SHALL be stated as the number alone, without the bounds beside it — the organizer configured the discipline and knows the size it asks for, and a bound repeated on eighteen rows is eighteen readings of one fact. A count the bounds do not admit, short of the minimum or over the maximum, SHALL be distinguished from one they do, which is the comparison the bounds were there to make. The roster SHALL be reachable from its team's row rather than printed under every row, so that a tournament's teams can be read as a list: a disclosure control beside the member count SHALL unfold it beneath the row and fold it again. The phase SHALL stand immediately after Fencers (`etl-console`): Fencers lists who will fight, this lists the entries they fight under.

**The view SHALL carry the agenda of a team entry**, since a registration that entered a team offers that agenda nowhere else: a fencer who entered a team and fights nothing is not on the fencer list at all (`etl-console`). The organizer SHALL be able to cancel one team of a registration, as **Cancelling one team** fixes.

Admission from the waitlist and return to it remain the Queue phase's (`seating-queue`), and the view SHALL say so on the capacity line above the waitlisted teams: admission moves money and opens a payment window, and the phase that does that is the phase that shows the queue.

**The view SHALL list the teams the organizer has lost.** A team whose entering registration has expired or been cancelled SHALL NOT disappear from the view. It SHALL stand below the discipline's live teams, the waitlisted ones included, beneath a line of its own that names what stands below it. Its row SHALL be drawn faded, the way a queued row is. An expiry happens on its own, by the payment clock, and a team that vanished without a word is one the organizer still expects at the venue.

Such a row SHALL state the team's name, the entering fencer, the address mail about that registration goes to, and the member count, as a live row does. In place of the payment standing it SHALL state **why** the team is gone, expired or cancelled, together with the day it happened, read in the tournament's own zone. Where the registration still holds credited money it SHALL also state that amount, as the fencer table states an expiry holding money, so that the organizer sees the money is the organizer's to settle with the fencer. Its roster SHALL unfold from the row as a live team's does, and SHALL NOT be editable. No action SHALL be offered on the row: no roster edit, no cancellation, and no statement about admission.

Below the line the rows SHALL be ordered by that day, the most recent first. The gutter SHALL NOT count them, because a count there would read as a place, and these teams hold none. They SHALL NOT enter the count on the discipline's tab, take a place against capacity, or take a place on the waitlist (**Team capacity and the team waitlist**). A registration reinstated by a late payment brings its team back among the live teams on its own, with no action of the view's.

A team cancelled on its own (**Cancelling one team**) takes its roster with it and SHALL NOT be listed here: nothing of it remains to show. Where no team of the discipline has lapsed, no line SHALL be drawn and nothing SHALL be said.

#### Scenario: Teams listed per discipline
- **WHEN** an organizer opens the teams view for a team discipline holding six teams
- **THEN** each team is listed with its name, entering fencer, ordered roster, and member count

Extra items belong to the registration, not to one of its teams, and a registration
that entered two or more teams cannot say whose they are. Each of its teams SHALL state
all of the registration's items, and SHALL carry a marker, opened on demand, naming the
other teams of the same registration that share them. A registration that entered one
team SHALL carry no such marker.

#### Scenario: Items shared by two teams of one registration
- **WHEN** a registration entered the teams "Wolves" and "Bears" and bought two swords to rent
- **THEN** both teams' rows state the swords, and each carries a marker naming the other team as sharing them

#### Scenario: Two team disciplines are chosen by tab
- **WHEN** an organizer opens the teams view of a tournament offering a longsword team event and a sabre team event
- **THEN** tabs under the heading name both with their team counts, and the table lists the teams of the chosen one with no discipline column

#### Scenario: One team discipline draws no tabs
- **WHEN** the tournament offers a single team discipline
- **THEN** the view lists its teams with no tabs above the table

#### Scenario: A bound member states its identifier here too
- **WHEN** a listed roster holds a member bound to a HEMA Ratings profile
- **THEN** the view states that identifier, as the public entrants roster already does

#### Scenario: Short teams distinguished after the deadline
- **WHEN** the composition deadline has passed and two of the listed teams are below minimum
- **THEN** those two are distinguished from the rest

#### Scenario: Unbound members shown plainly
- **WHEN** a listed roster contains members with no HEMA Ratings identifier
- **THEN** those members are shown by name with no identifier, club, or nationality, and are not marked as a problem

#### Scenario: The organizer swaps a member at the venue
- **WHEN** the organizer removes a member of a listed team and adds another in their place
- **THEN** the roster states the new member, the log holds both changes naming the organizer, and the entering fencer's registration is unchanged

#### Scenario: No actions offered
- **WHEN** an organizer views a waitlisted team
- **THEN** the view offers no control to admit it, and its row states that admission is on the Queue phase

#### Scenario: A count the bounds do not admit
- **WHEN** a discipline asking for three to four members holds a team of two and a team of three
- **THEN** both rows state the number alone, and the two is distinguished while the three is not

#### Scenario: Teams read as a table
- **WHEN** an organizer opens the Teams phase of a tournament holding eighteen teams
- **THEN** the teams are one table of eighteen rows, each stating its discipline, entering fencer, member count and payment standing, with its roster reachable from the row

#### Scenario: No teams view while the feature is off
- **WHEN** an organizer opens the console of a tournament whose team disciplines feature is off
- **THEN** no Teams phase is offered

#### Scenario: Teams reappear with the feature
- **WHEN** that organizer turns the team disciplines feature back on
- **THEN** the Teams phase is offered again, listing the same teams and rosters as before

#### Scenario: Entrants keep their roster editor
- **WHEN** a fencer who entered a team opens the tournament detail page while the team feature is off
- **THEN** the team is listed and its roster editor is offered as usual

#### Scenario: An expired team stays in sight
- **WHEN** the reservation of a fencer who entered the team "Wolves" expires unpaid on 12 November
- **THEN** the Teams view lists "Wolves" below the discipline's live teams, beneath its own line, faded, stating that it expired on 12 November, with its entering fencer and member count

#### Scenario: A cancelled registration's team stays in sight
- **WHEN** the organizer cancels a registration that entered one team
- **THEN** that team is listed below the line stating that it was cancelled and on which day

#### Scenario: Money still held is stated
- **WHEN** a registration that entered a team expires holding 500 credited
- **THEN** the team's row below the line states the 500 the registration still holds

#### Scenario: A lapsed team offers nothing
- **WHEN** the organizer unfolds the roster of a team below the line
- **THEN** the roster is shown read-only, and the row offers no edit, no cancellation and no admission

#### Scenario: A lapsed team holds no place
- **WHEN** a discipline of capacity 8 holds 8 seated teams and one lapsed team
- **THEN** the tab counts 8 teams, the gutter numbers the seated teams 1 to 8, and the lapsed team's row carries no number

#### Scenario: Reinstated, the team returns
- **WHEN** a payment arriving within the grace period reinstates an expired registration that entered a team
- **THEN** the team stands among the live teams again and no longer below the line

#### Scenario: A team cancelled alone is not listed
- **WHEN** the organizer cancels one team of a registration that stands
- **THEN** that team is listed nowhere in the view

#### Scenario: Nothing lapsed, no line
- **WHEN** no team of the discipline stands on an expired or cancelled registration
- **THEN** the view draws no line below the live teams and says nothing about lapsed teams

