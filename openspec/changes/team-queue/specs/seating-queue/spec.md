## ADDED Requirements

### Requirement: The team waitlist in the Queue phase
While the tournament's team disciplines feature is on, the Queue phase SHALL carry one tab per team discipline, after the individual disciplines' tabs, in the tournament's discipline order, counted as seated teams and waitlisted teams.

Each tab SHALL list the discipline's teams on live registrations — reserved within their validity window, or paid: seated teams above a line at the discipline's capacity, waitlisted teams below it in waitlist order. A row SHALL state the team's name, its entering fencer, its member count against the discipline's minimum and maximum, and the money of the entering fencer's registration as an individual seated row states it; a waitlisted row SHALL state its position and its moment, as a queued individual placement does. The tab SHALL state the discipline's free slots.

The organizer SHALL be able to **admit** a waitlisted team while the discipline has a free slot. Admission SHALL seat the team, bill its fee to the entering fencer's registration as the difference it adds, open a payment window where the registration's clocks run and not otherwise, and notify the entering fencer — naming the team and the discipline and stating what is now due — unless the registration is one Squire sends nothing to. It SHALL be refused when the discipline has no free slot or the registration cannot hold a place. An admission not paid for SHALL be taken back alone when its window lapses, as **Organizer promotion from the queue** fixes for every promotion.

The organizer SHALL be able to **return** a seated team to the waitlist while the entering fencer's registration is unpaid, freeing its slot, repricing the registration, and keeping the team's moment. It SHALL be refused on a paid registration, directing the organizer to cancellation.

Each action SHALL be offered on a row only where it would be carried out, and a refusal SHALL be reported in words, as on the individual rosters.

Admitting a team SHALL be an organizer's action only: no rule and no payment SHALL admit a team.

#### Scenario: A waitlisted team admitted
- **WHEN** a team discipline of capacity 8 holds 7 seated teams and the organizer admits the first waitlisted team
- **THEN** it is seated, its fee is billed to the entering fencer's registration, a payment window opens, and the entering fencer is told the team has a place and what is due

#### Scenario: No slot, no arrow
- **WHEN** the team discipline holds 8 seated teams
- **THEN** no waitlisted team carries the admit arrow

#### Scenario: A paid seat is safe from an unpaid team admission
- **WHEN** a fencer who paid for Longsword has their team admitted and does not pay the team fee before the window lapses
- **THEN** the team returns to the end of the waitlist and the Longsword seat stays, paid

#### Scenario: Returning a team
- **WHEN** the organizer returns a seated team whose entering fencer has not paid
- **THEN** the team is waitlisted at its previous place, its slot is freed, and the registration no longer owes its fee

#### Scenario: A dead registration's team is not listed
- **WHEN** a team's entering registration has expired
- **THEN** the team is not listed and takes no waitlist position
