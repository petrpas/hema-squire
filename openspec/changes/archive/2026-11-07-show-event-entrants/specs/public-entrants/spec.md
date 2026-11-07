## MODIFIED Requirements

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
