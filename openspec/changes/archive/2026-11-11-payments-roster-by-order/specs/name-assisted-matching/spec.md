## MODIFIED Requirements

### Requirement: The link dialog offers the ranked roster
Resolving a payment by hand SHALL offer the tournament's fencers ranked by how
well they match the payment, with the strongest marked, rather than requiring the
organizer to know and type a variable symbol.

The dialog SHALL also offer a text lookup over the whole roster, so a fencer the
ranking placed poorly can be found by typing part of their name. The lookup SHALL
also reach the club the registration was made under and the names of the teams it
entered, because on a team tournament the money arrives from a club or under a
team's name, not from the holder. Each listed registration SHALL state the same
contents summary the Payments registration table states (`payments-console`), so
the organizer can see which order the payment is being attached to. The ranking
itself is unchanged: neither the club nor a team name enters the score. Typing a
variable symbol directly SHALL remain available, and one payment SHALL still be
attachable to several registrations.

#### Scenario: The roster is offered ranked
- **WHEN** the organizer opens the link dialog on an unresolved payment
- **THEN** the tournament's fencers are listed ordered by how well they match it, with the strongest marked

#### Scenario: A poorly ranked fencer is found by typing
- **WHEN** the payment names nobody recognisable and the organizer types part of a fencer's name
- **THEN** the matching fencers are shown and can be chosen

#### Scenario: Typing a variable symbol still works
- **WHEN** the organizer types a variable symbol rather than choosing a fencer
- **THEN** it resolves as it does today

#### Scenario: One payment covering several fencers
- **WHEN** the organizer chooses more than one fencer for one payment
- **THEN** the payment is linked to each of their registrations

#### Scenario: Found by the team's name
- **WHEN** a payment arrives from "HEMA PRAHA Z.S." and the organizer types "hema praha" into the lookup
- **THEN** the registration that entered the team "Hema Praha" is listed, with its contents summary, although its holder's name contains neither word

#### Scenario: Found by the club
- **WHEN** the organizer types part of a club's name
- **THEN** every registration made under that club is listed
