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
apart from the roster, as the identifier in the top bar does. The Paid column's header
SHALL read "Zapl." in Czech and "Paid" in English, its own words on this roster rather
than the Export tables' header.

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

#### Scenario: The Paid header is short
- **WHEN** a visitor reading Czech opens a roster on a desktop screen
- **THEN** the Paid column's header reads "Zapl."

#### Scenario: Paid first
- **WHEN** a discipline holds, in registration order, an unpaid A, a paid B and a paid C
- **THEN** the roster lists B as 1, C as 2 and A as 3

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
A team discipline's roster SHALL list the columns No., Team, Nat., Club and Paid, the
Paid header worded as on an individual roster. It SHALL NOT state any HEMA Ratings
identifier, on a team's row or a member's: a team has none, and a reader looking for a
member's rating has their name.

The roster SHALL list each team by its name, with its members beneath it in roster
order, each member with nationality and club where the roster records them, read from
the console's projection where a row stands for the member. Each team SHALL open
folded, its members hidden until the visitor opens it, and SHALL fold again on a second
activation. A team's own row SHALL state a nationality where every member records the
same one, and a club where every member records the same one; where they differ, or a
member records none, that cell SHALL be empty. A member's row SHALL state a club only
where the team's row states none: a club the team's row states is every member's, and
repeating it on each member's row says nothing more. A team's Paid cell SHALL state its entering registration under
the rules of the Paid column, and an unpaid team SHALL be drawn faded where Squire
collects the money and that registration's money is due.

A team whose roster names nobody yet SHALL be listed by name alone, with nothing to
open and no line beneath it.

A team whose entering registration's row the organizer has taken out of the table SHALL
NOT be listed, as an individual's removed row is not.

In automatic mode, the roster SHALL draw a line at the discipline's capacity in teams and
list the waitlisted teams below it in waitlist order (`team-disciplines`), each numbered
by its waitlist position, its members beneath it, and its Paid cell empty. In manual mode
it SHALL list no waitlisted team and draw no line.

#### Scenario: A team with its members
- **WHEN** a visitor opens the roster of a team discipline holding "Ostravští draci" with four members
- **THEN** the team is listed by name, folded, and opening it shows its four members beneath it, in roster order

#### Scenario: The team row states what its members share
- **WHEN** a team's three members all fence for "Ostravští draci" and two are Czech, one Slovak
- **THEN** the team's row states the club and leaves the nationality empty

#### Scenario: A team not yet composed
- **WHEN** a team has been entered and its roster names nobody
- **THEN** it is listed by name with no toggle and nothing beneath it

#### Scenario: The team waitlist below the line
- **WHEN** an automatic tournament's team discipline of capacity 8 holds 8 teams and 2 waitlisted
- **THEN** the 2 are listed below the line, numbered 1 and 2 in waitlist order

#### Scenario: A seated team owing nothing yet carries no mark
- **WHEN** a reservation-mode team discipline holds sixteen seated teams before the seating deadline, none of them paid
- **THEN** all sixteen leave Paid empty and none is drawn faded

#### Scenario: The organizer's verdict names a team member
- **WHEN** a roster member was entered with one HEMA Ratings identifier and the organizer bound that member to another profile
- **THEN** the public roster names the member as the organizer's verdict states, and states no identifier for them

#### Scenario: Members sharing the team's club do not repeat it
- **WHEN** a visitor opens a team whose four members all fence for "Duelanti od Svatého Rocha"
- **THEN** the team's row states the club and no member's row does

#### Scenario: A member from another club states theirs
- **WHEN** a visitor opens a team of three from "Klub X" and one from "Klub Y"
- **THEN** the team's row leaves the club empty and each member's row states their own

#### Scenario: No identifier on a team roster
- **WHEN** a visitor opens a team discipline's roster and a team's members are bound to HEMA Ratings profiles
- **THEN** no column states an identifier and no row leads to HEMA Ratings

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
SHALL have none. On a record with no discipline (`discipline-less-events`) the side
events' rosters are the whole band.

A side event's roster SHALL list the fencers holding a place at it, under the same columns,
order, Paid rules and fading as an individual roster, and under the same restriction
to live registrations whose row the organizer has not removed. A side event keeps no
queue (`item-capacity`), so its roster SHALL list no queue. Where its item has a capacity,
the roster SHALL draw the capacity line under its last listed row, with nothing listed
below it, wherever a discipline's roster of the same record would draw its line. That
line SHALL be labelled with the capacity it marks (`kapacita 20` / `capacity 20`), not
as a plain capacity line: with nothing below it, a plain line under twelve rows would
read as twelve places. The roster's answer SHALL carry that capacity where it draws the
line, and none otherwise. Where its item has no capacity, the roster SHALL draw no line.

A side event's roster SHALL have an address of its own, apart from the disciplines', so
that a side event can never be read as a discipline (`routing`).

#### Scenario: A seminar is listed
- **WHEN** two fencers have taken a place at the uncapped Liechtenauer seminar, one of them paid
- **THEN** its roster lists the paid one first and the other faded, with no line

#### Scenario: A capped seminar draws its line
- **WHEN** an automatic record's seminar of capacity 20 has 20 places taken
- **THEN** its roster lists the 20 and draws the line labelled `kapacita 20` under the last of them, with nothing below it

#### Scenario: A capped seminar not yet full
- **WHEN** an automatic record's seminar of capacity 20 has 12 places taken
- **THEN** its roster lists the 12 and draws the line labelled `kapacita 20` under the twelfth

#### Scenario: A held record draws no line
- **WHEN** a visitor opens the roster of a capped seminar on a record dated last month
- **THEN** its entrants are listed and no line is drawn

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

### Requirement: A deleted account's row states no payment
On a held tournament's roster, the row of a deleted account SHALL leave the Paid cell empty, whatever the tournament's mode and whatever its registration's settled state, and SHALL NOT be drawn faded. This takes precedence over the Paid column's rules. The row's position SHALL NOT change.

#### Scenario: A paid fencer deletes their account
- **WHEN** a visitor opens a held tournament's roster listing a deleted account that had paid
- **THEN** the row shows the name, identifier, club and nationality and an empty Paid cell

### Requirement: Nationality is stated as a flag
On every roster of the public entrants view, the Nat. cell SHALL state a nationality from
which a country can be read as that country's national flag, alone, in place of any code
or name. A nationality is read as a country the way the familiar-entrants match reads one
(`public-browsing`), as an ISO 3166 alpha-2 code whatever vocabulary it was written in:
either ISO code, the English name, the official name, or one of the aliases Squire keeps, so "CZ", "CZE" and "Czech Republic" all draw the
Czech flag and "England" draws the flag of the United Kingdom. The flag SHALL carry the
country's name in the page's language as its accessible name and as the title shown on
hover. A nationality from which no country can be read SHALL be stated as written, as
text. An empty nationality SHALL leave the cell empty.

This SHALL hold for an individual's row, a side event's row, a team member's row and a
team's row where it states the nationality all its members share. A team whose members'
nationalities differ SHALL leave the cell empty, as now.

The flag SHALL be drawn small enough to sit within the row's line height, at the flag's
own proportions with no cropping, framed by a hairline so that a flag mostly white
still reads against the paper. It SHALL be a file Squire serves itself; no flag SHALL be
fetched from a third party, and no emoji SHALL draw one.

The flag of Russia SHALL be drawn in greyscale, not in its colors; it is otherwise drawn
and named as every other flag.

The flag SHALL NOT reach any other screen or output: the organizer console, the Export
tables, the data export and the printed roster (`roster-print`) SHALL keep stating the
nationality as they do.

#### Scenario: A Czech fencer
- **WHEN** a visitor reading Czech opens a roster holding a fencer whose nationality is "CZ"
- **THEN** the Nat. cell shows the Czech flag and no code, and its accessible name is "Česko"

#### Scenario: Spellings of one country draw one flag
- **WHEN** a roster holds three fencers whose nationalities read "PL", "Poland" and "POL"
- **THEN** all three Nat. cells show the Polish flag

#### Scenario: The Russian flag in greyscale
- **WHEN** a roster holds a fencer whose nationality reads "Russia"
- **THEN** the Nat. cell shows the Russian flag in greyscale, named as Russia, while the other flags on the roster keep their colors

#### Scenario: A spelling no country is read from
- **WHEN** a fencer's nationality reads "Bohemia"
- **THEN** the Nat. cell states "Bohemia" as text and shows no flag

#### Scenario: A team sharing a country
- **WHEN** every member of a team records nationality "SK"
- **THEN** the team's row shows the Slovak flag, and each member's row, when opened, shows it too

#### Scenario: The console keeps codes
- **WHEN** the organizer opens the Export tab of the discipline whose public roster shows flags
- **THEN** its Nat. column states the codes, and no flag is drawn

### Requirement: A roster fits a phone
Below 768px wide (`responsive-layout`), a roster SHALL fit the screen's width with no
column out of sight: no part of a row SHALL be reached by scrolling sideways.

The name — a fencer's, or a team's and its members' — SHALL take the width the
roster has to give and MAY wrap onto further lines. The club SHALL stand on one line,
cut short with an ellipsis where it does not fit: a visitor knows the clubs, and a
name wrapping to three lines while the club stands whole is the wrong way round. The
same priority SHALL hold on a wider screen where a name and a club compete for space.
The Nat. column SHALL be as wide as a flag; a nationality stated as text there SHALL
likewise be cut with an ellipsis. The Nat. and Paid columns SHALL stand centred, their
headers with them, at every width: a column of flags or of short words reads as one
column when it shares an axis.

Below 768px the Paid column's header SHALL read "Zap." in Czech and stay "Paid" in
English, and on an individual roster the HRID cell SHALL state only the mark that
leads to the fighter's HEMA Ratings profile, not the number. The link SHALL carry the
identifier as its accessible name, so that a screen reader states it. The column's
header SHALL read "HR".

Every team's name SHALL begin at the same distance from the number column, whether
the team can be opened or not. A team's toggle SHALL stand in the space between the
number column and the name, centred in it, and level with the first line of the name
where the name wraps; it SHALL NOT push the name to the right.

#### Scenario: A phone shows every column
- **WHEN** a visitor opens an individual roster on a screen 390px wide
- **THEN** No., Fencer, Nat., Club, HR and Paid all stand within the screen and the roster does not scroll sideways

#### Scenario: The name wraps, the club is cut
- **WHEN** a team "Pardubičtí šavlisté" of the club "Pardubický spolek šermířský" is listed on a screen 390px wide
- **THEN** the team's name may take two lines, and the club stands on one line ending in an ellipsis

#### Scenario: The identifier as a mark on a phone
- **WHEN** a visitor opens an individual roster on a phone, listing a fencer with identifier 12714
- **THEN** the HR cell shows the mark alone, it leads to that profile, and its accessible name states 12714

#### Scenario: Team names stand in one column
- **WHEN** a roster lists a team that can be opened above one whose roster names nobody
- **THEN** both names begin at the same distance from the number column, and the first team's toggle stands centred in the space before its name

#### Scenario: Flags and Paid centred
- **WHEN** a visitor opens any roster
- **THEN** the flags of the Nat. column and the words of the Paid column stand centred under centred headers

#### Scenario: The short header on a phone
- **WHEN** a visitor reading Czech opens a roster on a screen 390px wide
- **THEN** the Paid column's header reads "Zap."

