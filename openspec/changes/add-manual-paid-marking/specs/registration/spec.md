## MODIFIED Requirements

### Requirement: Public participant list
The public participant list SHALL present who is entered for the tournament. What it says about payment SHALL depend on whether Squire guarantees a payment state at all.

**Where Squire collects the money** — the payments feature is on and Squire keeps the registrations — the list SHALL show confirmed (paid) registrations only. Unpaid reservations SHALL be either hidden or shown greyed as unconfirmed, according to the tournament setting; the default for a new tournament is greyed.

**Where Squire does not** — it handles no payments for the tournament, or the tournament is in manual mode (`tournament-mode`) — the list SHALL NOT read a registration's payment state as its attendance of its own accord, and the unpaid-list setting SHALL NOT apply, because there are no unpaid reservations in the sense that setting means: no money was requested, so none is outstanding.

Such a list SHALL present every entrant, and SHALL mark **only** those the organizer has settled by hand (`payments`). A marked entrant SHALL be shown as confirmed, because a person who collected the money has said so. An entrant not marked SHALL carry **no mark whatever** and SHALL NOT be shown as unconfirmed: the absence of a mark is not a claim that anyone has failed to pay, only that the organizer has not reached that row, and turning it into one would have the system assert precisely what it has no basis for.

A list drawn from a roster Squire does not maintain SHALL state **how current it is**, naming the moment the roster last reached Squire. It SHALL state that moment as a fact and SHALL NOT characterise it — it SHALL NOT claim the list is up to date, nor warn that it may be stale, both being assessments the system has no basis for. A list Squire maintains itself SHALL state no such moment, being live by construction.

#### Scenario: Unpaid fencer not presented as confirmed
- **WHEN** a visitor views the public participant list of a tournament Squire collects for
- **THEN** unpaid reservations never appear as confirmed participants

#### Scenario: A list Squire collects nothing for makes no claim of its own
- **WHEN** a visitor views the public participant list of a tournament whose payments Squire does not handle, none of whose registrations has been marked settled
- **THEN** every seated entrant is listed, none carries any payment mark, and the unpaid-list setting has no effect

#### Scenario: A hand-settled entrant is shown as confirmed
- **WHEN** the organizer has marked three of twenty entrants settled and a visitor views the list
- **THEN** those three are shown as confirmed

#### Scenario: The unmarked are not called unconfirmed
- **WHEN** the same visitor reads the other seventeen
- **THEN** none of them is described as unconfirmed or unpaid, and each is listed as an entrant like any other

#### Scenario: Organizer-kept list states its currency
- **WHEN** a visitor views the public participant list of a tournament whose registrations the organizer keeps, imported four days ago
- **THEN** the entrants are listed plainly and the list states that it stands as of the moment the roster last reached Squire

#### Scenario: A live list does not date itself
- **WHEN** a visitor views the participant list of a tournament Squire keeps the registrations for
- **THEN** no as-of moment is stated
