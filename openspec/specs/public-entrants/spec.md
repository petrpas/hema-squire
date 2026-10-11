# public-entrants Specification

## Purpose
Define the public rosters on a tournament's page: one per discipline and per listed
side event, what each lists and in what order, what its Paid cell may claim, where the
queue is shown, what a count beside a capacity states, and what the answer behind them
may carry.
## Requirements
### Requirement: A published tournament's entrants are listed per discipline
A published, non-cancelled tournament SHALL present one roster for each discipline it
offers, individual and team alike, in the tournament's own discipline order, each
labelled by the discipline's name and never by its slug (`discipline-identity`).

The band SHALL name each discipline and state no count beside it. A count of places
there would sit beside rows that do not add up to it, and how full a discipline is
is the information screen's to say.

A discipline nobody has entered SHALL still have its roster, stating in one line that
nobody is entered yet, rather than being left out of the band. Its absence would read
as a discipline the tournament does not offer.

#### Scenario: One roster per discipline
- **WHEN** a visitor opens the entrants of a tournament offering Longsword Open, Sabre Open and a longsword team event
- **THEN** three rosters are offered in that order, each under its discipline's name

#### Scenario: An empty discipline keeps its roster
- **WHEN** nobody has entered Sabre Open
- **THEN** its roster is offered and states that nobody is entered yet

### Requirement: An individual roster lists who is entered
An individual discipline's roster SHALL list the columns No., Fencer, Nat., Club, HRID
and Paid: the columns of the printed roster (`roster-print`) without the rank. The
columns stating a number SHALL stand right-aligned, as on the Export tables. An HEMA
Ratings identifier SHALL lead to that fighter's profile on hemaratings.com, opened
apart from the roster, as the identifier in the top bar does.

Its rows SHALL be the rows of that discipline's Export tab (`export-tables`), restricted
to the rows standing for a live registration. The organizer's corrections SHALL
therefore be applied, a row the organizer deleted SHALL be absent, and where a row is
bound to a HEMA Ratings profile its nationality and club SHALL be stated as HEMA Ratings
records them. A row standing for no registration, such as an imported row not yet issued,
and a row whose registration has expired or been cancelled SHALL NOT be listed.

Neither the rating nor the rank SHALL be shown. A reader who wants either follows the
identifier to HEMA Ratings, where both are current.

Rows above the capacity line SHALL be ordered paid first, then in registration order, as
the Export tab orders them before any seeding order is ticked, and SHALL be numbered from
1 in that order. The seeding order is the organizer's own view and SHALL NOT reach the
public roster.

#### Scenario: A corrected name is the public name
- **WHEN** the organizer has corrected a fencer's name from "Jan Novak" to "Jan Novák"
- **THEN** the roster lists "Jan Novák"

#### Scenario: A deleted row is not listed
- **WHEN** the organizer has deleted a duplicate row from the table
- **THEN** it appears on no roster

#### Scenario: HEMA Ratings' club stands over the fencer's
- **WHEN** a fencer bound to a HEMA Ratings profile gave no club and HEMA Ratings records one
- **THEN** the roster states the club HEMA Ratings records

#### Scenario: An expired reservation is gone
- **WHEN** a reservation expires for non-payment
- **THEN** its fencer is no longer listed on any roster

#### Scenario: An identifier leads to HEMA Ratings
- **WHEN** a visitor selects the identifier 10234 on a roster
- **THEN** that fighter's HEMA Ratings profile opens apart from the roster

#### Scenario: Paid first
- **WHEN** a discipline holds, in registration order, an unpaid A, a paid B and a paid C
- **THEN** the roster lists B as 1, C as 2 and A as 3

### Requirement: The Paid column states only what Squire can stand behind
Where Squire collects the money (the payments setting is on and the tournament is in
automatic mode), a seated row's Paid cell SHALL read yes when its registration is
settled and no otherwise. An unpaid seated row SHALL always be listed and SHALL be drawn
in faded ink, never hidden.

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

#### Scenario: Unpaid shown faded
- **WHEN** a visitor reads a roster of a tournament Squire collects for, holding a reservation not yet paid
- **THEN** that fencer is listed, drawn faded, with Paid reading no

#### Scenario: A hand tick is the only mark where Squire does not collect
- **WHEN** a payments-off tournament's organizer has settled three of twenty entrants by hand
- **THEN** those three read yes, the other seventeen leave Paid empty, and none is drawn faded

#### Scenario: A queued row states nothing about money
- **WHEN** a fencer is seated and paid in Sabre Open and queued in Longsword Open
- **THEN** their Sabre Open row reads yes and their Longsword Open queue row leaves Paid empty

### Requirement: The queue is public where Squire keeps it
In automatic mode, an individual roster SHALL draw a line at the discipline's capacity,
under its last seated row. Below the line it SHALL list the discipline's queued
placements in queue order (`seating-queue`). Each queued row's number SHALL be its
position in the queue, the same position the fencer is shown on their own registration,
and not a continuation of the seated numbering.

A queued placement that waits under a participation condition (`registration`) SHALL
carry a mark saying it is entered only together with its other conditional disciplines.
Such a placement can stand in the queue while places are free, and without the mark the
roster would read as a mistake.

In manual mode the roster SHALL list no queued placement and SHALL draw no capacity
line. There the organizer keeps the real waiting list outside Squire, and importing
seats every row whatever the capacity. A queue drawn from what Squire holds would be
empty or partial, and a line would put regularly entered fencers beneath it as though
they were waiting.

#### Scenario: The queue below the line
- **WHEN** an automatic tournament's discipline of capacity 32 holds 32 seated placements and 3 queued ones
- **THEN** its roster lists the 32 above a line and the 3 below it numbered 1, 2 and 3 in queue order

#### Scenario: The fencer's own position agrees
- **WHEN** a queued fencer reads their registration stating they are 2nd in the queue
- **THEN** the public roster numbers them 2 below the line

#### Scenario: A conditional placement is marked
- **WHEN** a fencer queued in Longsword Open entered it only together with Sabre Open
- **THEN** their queue row carries the mark saying so

#### Scenario: No queue and no line in manual mode
- **WHEN** a manual tournament's imported roster seats 48 fencers in a discipline of capacity 42
- **THEN** its roster lists all 48 numbered 1 to 48 with no line drawn and no queue

### Requirement: A team roster names the team and its members
A team discipline's roster SHALL list each team by its name, with its members beneath it
in roster order, each member with nationality, club and HEMA Ratings identifier where
the roster records them. A team's Paid cell SHALL state its entering registration under
the rules of the Paid column, and an unpaid team SHALL be drawn faded where Squire
collects the money.

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

### Requirement: A count states who is shown above the line
Wherever a public screen states a discipline's count beside its capacity — the
information screen, the list card, the registration form — the count SHALL be the
entrants its roster lists above the line: live seated placements, or teams in a team
discipline, less the registrations whose row the organizer has taken out of the table by
deleting it or merging it into another. 28/32 then means twenty-eight entrants listed and
places still to be had, and a reader counting the roster arrives at the same number.

This governs what the count states and nothing else. A live registration's row can no
longer be deleted (`etl-console`, Reversible row deletion); a person is cancelled instead,
which frees the seat. A row deleted while holding a live registration before that rule
stood SHALL keep its seat until the organizer restores it and cancels the registration:
placement, the free places that decide whether a new entry is seated or queued, and the
queue SHALL count it as before. For such a row the count MAY show a place free while a new
entry is queued.

#### Scenario: A removed row is not counted
- **WHEN** a discipline of capacity 32 holds 30 live seated registrations and the organizer has deleted the rows of two of them
- **THEN** the information screen and the list card state 28/32, and the roster lists 28

#### Scenario: Restoring counts it again
- **WHEN** the organizer restores one of those rows
- **THEN** the count reads 29/32

#### Scenario: The seat is not released
- **WHEN** the same discipline is asked how many places are free
- **THEN** the two removed registrations still hold their seats

### Requirement: Side events have rosters, the afterparty does not
After the disciplines, the band SHALL offer one roster for each seminar and each other
side event the tournament offers, in the order they were offered, labelled by the
event's name. The afterparty SHALL have no roster: who goes to the party is not the
tournament's to publish. Goods (rentals, merchandise, other items) are not events and
SHALL have none.

An event's roster SHALL list the fencers holding a place at it, under the same columns,
order, Paid rules and fading as an individual roster, and under the same restriction
to live registrations whose row the organizer has not removed. An event has no
capacity, so its roster SHALL draw no line and list no queue.

An event's roster SHALL have an address of its own, apart from the disciplines', so
that an event can never be read as a discipline (`routing`).

#### Scenario: A seminar is listed
- **WHEN** two fencers have taken a place at the Liechtenauer seminar, one of them paid
- **THEN** its roster lists the paid one first and the other faded, with no line

#### Scenario: No afterparty roster
- **WHEN** a tournament offers a seminar, a castle tour and an afterparty
- **THEN** the band offers rosters for the seminar and the tour after the disciplines, and none for the afterparty

### Requirement: A held tournament keeps its rosters without a queue
A tournament dated before today, by the boundary that splits the public tournament list
(`day-boundaries`), SHALL keep its rosters readable. They SHALL list no queued placement
and no waitlisted team, and SHALL draw no capacity line. Who waited for a place no longer
matters once the tournament has been fenced.

#### Scenario: Past rosters remain
- **WHEN** a visitor opens the entrants of a tournament held last month
- **THEN** each discipline's seated entrants are listed and no queue and no line are shown

### Requirement: A roster carries only what it states
The answer a roster is drawn from SHALL carry, for each row, only the values the roster
states: the number, the name, the nationality, the club, the HEMA Ratings identifier, the
paid statement, whether the row is drawn faded, and the conditional mark, plus
a team's name and members. It SHALL NOT carry an address, a variable symbol, an amount, a
balance, a note, a problem, matching evidence, or any identifier of a registration or a
row.

The headers and the yes/no SHALL be in the reader's language. Names, clubs and team
names SHALL be stated as written.

#### Scenario: No contact details in the answer
- **WHEN** the entrants of a tournament are requested
- **THEN** the answer carries no email address, no variable symbol and no amount for any row

