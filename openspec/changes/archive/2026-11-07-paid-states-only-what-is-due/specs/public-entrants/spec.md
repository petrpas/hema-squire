## MODIFIED Requirements

### Requirement: The Paid column states only what Squire can stand behind
Where Squire collects the money (the payments setting is on and the tournament is in
automatic mode), a seated row's Paid cell SHALL read yes when its registration is
settled. An unsettled seated row's cell SHALL read no only where that registration's
money is due: a payment window is running on it, or the obligation its seat is held
under has fallen due. Such a row SHALL always be listed and SHALL be drawn in faded
ink, never hidden.

An unsettled seated row on which nothing is due yet SHALL leave the cell empty and
SHALL NOT be drawn faded. In reservation mode nothing is owed until the seating
deadline (`registration`, Payment mode), and in deposit mode nothing beyond the deposit
is; a roster reading no before then would state a failure to pay against a fencer nobody
has asked. Owing nothing and having paid are different statements, and the roster SHALL
make neither out of the other: a row that owes nothing yet reads yes if it has paid
early and empty otherwise.

Where Squire does not collect the money (the payments setting is off, or the tournament
is in manual mode), a row SHALL read yes only where the organizer has settled it by hand
(`payments`), and SHALL otherwise leave the cell empty. No row SHALL be drawn faded and
none SHALL read no: the absence of a mark is not a claim that anybody has failed to pay.

A queued row's and a waitlisted team's Paid cell SHALL be empty in every mode. A
registration's settled state covers its seated placements only, and a queued placement
is not priced. The registration-wide value would therefore read no for a substitute who
owes nothing, yes for a substitute whose other discipline is paid, and no for a
substitute whose payment is held for the organizer. None of the three is a fact about
the queued placement.

An entry that holds no seat at all — the items of a side event bought on their own
(`discipline-less-events`) — owes in full at once whatever mode the tournament stores,
so its row's money is due from the moment it is made.

#### Scenario: Unpaid shown faded
- **WHEN** a visitor reads a roster of a tournament Squire collects for, holding a reservation not yet paid whose payment window is running
- **THEN** that fencer is listed, drawn faded, with Paid reading no

#### Scenario: Nothing is claimed before the seating deadline
- **WHEN** a visitor reads a reservation-mode roster a week before its seating deadline, holding sixteen seated registrations of which three have paid early
- **THEN** the three read yes and the other thirteen leave Paid empty, and none of the thirteen is drawn faded

#### Scenario: The seating deadline is when the roster may say no
- **WHEN** the seating deadline of that tournament has passed with those thirteen still unpaid
- **THEN** each of the thirteen still listed reads no and is drawn faded

#### Scenario: A deposit paid is paid enough to carry no mark
- **WHEN** a deposit-mode registration has been credited its deposit, closing its payment window, and the seating deadline has not passed
- **THEN** its row leaves Paid empty and is not drawn faded, the balance being owed by a date that has not come

#### Scenario: A side event's item owes at once
- **WHEN** a visitor reads the roster of a side event bought by a registration holding no discipline and no team, unpaid
- **THEN** that row reads no and is drawn faded, the mode's held seat being nothing it holds

#### Scenario: A hand tick is the only mark where Squire does not collect
- **WHEN** a payments-off tournament's organizer has settled three of twenty entrants by hand
- **THEN** those three read yes, the other seventeen leave Paid empty, and none is drawn faded

#### Scenario: A queued row states nothing about money
- **WHEN** a fencer is seated and paid in Sabre Open and queued in Longsword Open
- **THEN** their Sabre Open row reads yes and their Longsword Open queue row leaves Paid empty

### Requirement: A team roster names the team and its members
A team discipline's roster SHALL list each team by its name, with its members beneath it
in roster order, each member with nationality, club and HEMA Ratings identifier where
the roster records them. A team's Paid cell SHALL state its entering registration under
the rules of the Paid column, and an unpaid team SHALL be drawn faded where Squire
collects the money and that registration's money is due.

A team whose roster names nobody yet SHALL be listed by name, with one line stating that
its members are not yet named.

A team whose entering registration's row the organizer has taken out of the table SHALL
NOT be listed, as an individual's removed row is not.

In automatic mode, the roster SHALL draw a line at the discipline's capacity in teams and
list the waitlisted teams below it in waitlist order (`team-disciplines`), each numbered
by its waitlist position, its members beneath it, and its Paid cell empty. In manual mode
it SHALL list no waitlisted team and draw no line.

#### Scenario: A team with its members
- **WHEN** a visitor opens the roster of a team discipline holding "Ostravští draci" with four members
- **THEN** the team is listed by name with its four members beneath it, in roster order

#### Scenario: A team not yet composed
- **WHEN** a team has been entered and its roster names nobody
- **THEN** it is listed by name with a line stating its members are not yet named

#### Scenario: The team waitlist below the line
- **WHEN** an automatic tournament's team discipline of capacity 8 holds 8 teams and 2 waitlisted
- **THEN** the 2 are listed below the line, numbered 1 and 2 in waitlist order

#### Scenario: A seated team owing nothing yet carries no mark
- **WHEN** a reservation-mode team discipline holds sixteen seated teams before the seating deadline, none of them paid
- **THEN** all sixteen leave Paid empty and none is drawn faded
