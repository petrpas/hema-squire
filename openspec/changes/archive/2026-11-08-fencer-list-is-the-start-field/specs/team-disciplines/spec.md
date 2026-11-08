## ADDED Requirements

### Requirement: Cancelling one team

The organizer SHALL be able to cancel a single team of a registration, leaving that
registration and every other team and entry on it standing. A registration may carry
several teams, in one discipline or several (**A team is entered by one registered
fencer**), so cancelling the registration is too blunt an instrument for a team that has
withdrawn.

Cancelling a team SHALL be an amendment of the registration it was entered on: the team's
fee SHALL leave the registration's total, the registration SHALL be repriced on its own
frozen prices, and what that leaves owed or overpaid SHALL be stated as any amendment's
result is. A seated team's place SHALL be freed, and the discipline's waitlist SHALL NOT
be promoted from automatically — a freed place waits for the organizer, as a freed
individual seat does (`seating-queue`).

The team's roster SHALL go with it and SHALL NOT be retained as a roster of nobody. Its
members SHALL leave the fencer list, since they will not fight.

The organizer SHALL confirm it, and the confirmation SHALL state in plain words what the
cancellation does before it is taken: that it cannot be undone, that the team's fee leaves
what the registration pays while its other teams and entries stand, that the roster goes
with the team and its members leave the fencer list, that the place is freed and nobody
moves up from the waitlist by itself, and that the entering fencer is written to. No part
of it SHALL be stated in the vocabulary of the pricing machinery: the reader is an
organizer cancelling a team, not a reader of the repricing rules.

It SHALL be refused on a registration that is cancelled or expired, and on a tournament
whose team disciplines feature is off — the teams a hidden feature holds are retained
untouched.

The entering fencer SHALL be told, naming the team and the discipline and stating what
the registration now owes or is owed, unless it is a registration Squire sends nothing
to. This is money changing hands and is not the silent correction a roster edit is.

#### Scenario: The confirmation says what will happen
- **WHEN** the organizer opens the cancellation of a seated team of four
- **THEN** it states that the cancellation cannot be undone, that the fee leaves the registration, that four fighters leave the fencer list, that the freed place promotes nobody, and that the entering fencer is told

#### Scenario: One team of two cancelled
- **WHEN** a registration carrying two teams has one cancelled
- **THEN** the other team stands, the registration stands, and its total is reduced by the cancelled team's fee alone

#### Scenario: The place is freed but nobody is promoted
- **WHEN** a seated team is cancelled in a discipline with a waitlist
- **THEN** the discipline states one free place and no waitlisted team is admitted

#### Scenario: Its fighters leave the start field
- **WHEN** a team of four is cancelled
- **THEN** those four members are no longer listed on the fencer list

#### Scenario: The entrant is told
- **WHEN** the organizer cancels a team on a paid registration
- **THEN** the entering fencer receives one message naming the team and the discipline and stating the resulting balance

#### Scenario: Refused on a dead registration
- **WHEN** the organizer attempts to cancel a team on a cancelled registration
- **THEN** it is refused

### Requirement: A team discipline carries a rating category for its fighters

A team discipline SHALL derive a HEMA Ratings category from its taxonomy code, as an
individual discipline does, and the tournament's category map SHALL offer and store an
entry for it. A team discipline classified alike with an individual one SHALL share that
one entry, since the map is keyed by taxonomy code and not by a discipline's identity
(`hr-integration`).

The category SHALL rate the discipline's **fighters**, not its teams. A team SHALL carry
no rating and no rank of its own: what a tournament makes of four fighters' ratings when
it seeds is the tournament's decision and SHALL NOT be computed here.

A team discipline whose weapon lies outside the HEMA taxonomy SHALL be skipped by the
snapshot without being reported as a failure, on the same terms as an individual one.

#### Scenario: Team discipline present in the map
- **WHEN** a tournament offering an individual and a team discipline of different weapons exposes its HR category map
- **THEN** both are present, each with its own entry

#### Scenario: Alike disciplines share one entry
- **WHEN** a tournament offers sabre individually and sabre in teams
- **THEN** the map offers one sabre entry governing both, and a snapshot fetches one sabre rating per fighter

#### Scenario: A team carries no rating of its own
- **WHEN** a snapshot has been taken for a tournament with a team discipline
- **THEN** each matched roster member carries a rating and a rank, and no team carries either

## REMOVED Requirements

### Requirement: Team disciplines carry no HR rating category
**Reason**: Reversed. The decision rested on a team having no rating, which is still
true — but its fighters do, and the pools of a team discipline are drawn from them. A
tournament offering only team disciplines maps no taxonomy code under this requirement
and so fetches no rating for anybody, which is the gap this change exists to close.
**Migration**: No data moves. A tournament whose category map was refused a team
discipline's code may now store one; a map saved without it keeps working and simply
carries no entry for that code until the organizer configures one, exactly as an
unconfigured individual code behaves.

## MODIFIED Requirements

### Requirement: Organizer's teams view
The console SHALL present, per team discipline, the teams entered into it: the team name, the entering fencer, the roster in order with each member's name and — where bound — HEMA Ratings identifier, club, and nationality, the member count, and the team's waitlist position where it is waitlisted. Teams marked below minimum after the composition deadline SHALL be distinguished.

The view SHALL be offered only while the tournament's team disciplines feature is on, as fixed by `tournament-features`. An organizer who has turned the feature off SHALL see no Teams phase; the teams, rosters and waitlist positions it would have shown SHALL be retained untouched and SHALL be shown again when the feature is turned back on. The entering fencer's own roster editor on the tournament detail page SHALL be unaffected by the feature, which governs the organizer's console alone.

**The view SHALL let the organizer edit a roster**: add a member, remove one, restore a removed one, and correct a member's name, HEMA Ratings identifier, club or nationality. A team arrives at the tournament and the fencer who entered it cannot always reach their own editor; the organizer acting for them is the remedy, and it is a safe one — a roster edit moves no money, as **Roster editing changes no money** fixes. Every such edit SHALL be recorded as **Every roster change is recorded in one log** fixes, and the log SHALL be shown beside the roster.

**The view SHALL be a table**, one row per team, read the way the fencer list is read: the team's name, its discipline, the fencer who entered it, its member count, its waitlist position where it is waitlisted, and the payment standing of the registration it was entered on. The count SHALL be stated as the number alone, without the bounds beside it — the organizer configured the discipline and knows the size it asks for, and a bound repeated on eighteen rows is eighteen readings of one fact. A count the bounds do not admit, short of the minimum or over the maximum, SHALL be distinguished from one they do, which is the comparison the bounds were there to make. The roster SHALL be reachable from its team's row rather than printed under every row, so that a tournament's teams can be read as a list. The phase SHALL stand immediately after Fencers (`etl-console`): Fencers lists who will fight, this lists the entries they fight under.

**The view SHALL carry the agenda of a team entry**, since a registration that entered a team offers that agenda nowhere else: a fencer who entered a team and fights nothing is not on the fencer list at all (`etl-console`). The organizer SHALL be able to cancel one team of a registration, as **Cancelling one team** fixes.

Admission from the waitlist and return to it remain the Queue phase's (`seating-queue`), and the view SHALL say so where it shows a waitlisted team: admission moves money and opens a payment window, and the phase that does that is the phase that shows the queue.

#### Scenario: Teams listed per discipline
- **WHEN** an organizer opens the teams view for a team discipline holding six teams
- **THEN** each team is listed with its name, entering fencer, ordered roster, and member count

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
