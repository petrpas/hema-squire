## ADDED Requirements

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

## MODIFIED Requirements

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

#### Scenario: The settled identifier is the one shown
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
