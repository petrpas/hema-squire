## MODIFIED Requirements

### Requirement: A team roster names the team and its members
A team discipline's roster SHALL list each team by its name, with its members beneath it
in roster order, each member with nationality, club and HEMA Ratings identifier where
the roster records them. A member's identifier SHALL be the one the console has settled,
not the one typed into the roster where the two differ: an identifier the organizer has
ruled on is the tournament's answer, and an individual entrant's row already states it
that way. Where no verdict has been given, the roster SHALL state the identifier as
claimed. A team's Paid cell SHALL state its entering registration under
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

#### Scenario: The settled identifier is the one shown
- **WHEN** a roster member was entered with one HEMA Ratings identifier and the organizer bound that member to another
- **THEN** the public roster states the organizer's, and it leads to that profile
