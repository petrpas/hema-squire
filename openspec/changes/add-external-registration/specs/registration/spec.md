## MODIFIED Requirements

### Requirement: Public participant list
The public participant list SHALL present who is entered for the tournament. What it says about payment SHALL depend on whether Squire guarantees a payment state at all.

**Where Squire collects the money** — the payments feature is on and Squire keeps the registrations — the list SHALL show confirmed (paid) registrations only. Unpaid reservations SHALL be either hidden or shown greyed as unconfirmed, according to the tournament setting; the default for a new tournament is greyed.

**Where Squire does not** — the payments feature is off, or the organizer keeps the registrations (`registration-ownership`) — the list SHALL present every entrant plainly, and SHALL draw no confirmed or unconfirmed distinction. It SHALL NOT mark an entrant unconfirmed, and the unpaid-list setting SHALL NOT apply, because there are no unpaid reservations in the sense that setting means: no money was requested, so none is outstanding. Reading a registration's payment state as its attendance SHALL NOT happen on a tournament whose payments Squire was never asked to handle.

A list drawn from a roster Squire does not maintain SHALL state **how current it is**, naming the moment the roster last reached Squire. It SHALL state that moment as a fact and SHALL NOT characterise it — it SHALL NOT claim the list is up to date, nor warn that it may be stale, both being assessments the system has no basis for. A list Squire maintains itself SHALL state no such moment, being live by construction.

#### Scenario: Unpaid fencer not presented as confirmed
- **WHEN** a visitor views the public participant list of a tournament Squire collects for
- **THEN** unpaid reservations never appear as confirmed participants

#### Scenario: Payments-off list shows entrants without a payment claim
- **WHEN** a visitor views the public participant list of a tournament whose payments feature is off
- **THEN** every seated entrant is listed, none is marked unconfirmed, and the unpaid-list setting has no effect

#### Scenario: Organizer-kept list states its currency
- **WHEN** a visitor views the public participant list of a tournament whose registrations the organizer keeps, imported four days ago
- **THEN** the entrants are listed plainly and the list states that it stands as of the moment the roster last reached Squire

#### Scenario: A live list does not date itself
- **WHEN** a visitor views the participant list of a tournament Squire keeps the registrations for
- **THEN** no as-of moment is stated
