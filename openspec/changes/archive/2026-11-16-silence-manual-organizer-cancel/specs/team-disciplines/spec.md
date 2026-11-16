## MODIFIED Requirements

### Requirement: Cancelling one team

The organizer SHALL be able to cancel a single team of a registration, leaving that
registration and every other team and entry on it standing. A registration may carry
several teams, in one discipline or several (**A team is entered by one registered
fencer**), so cancelling the registration is too blunt an instrument for a team that has
withdrawn.

Cancelling a team SHALL be an amendment of the registration it was entered on: the team's
fee SHALL leave the registration's total, the registration SHALL be repriced on its own
frozen prices, and what that leaves owed or overpaid SHALL be stated as any amendment's
result is. A seated team's place SHALL be freed, and the discipline's waitlist SHALL NOT
be promoted from automatically — a freed place waits for the organizer, as a freed
individual seat does (`seating-queue`).

The team's roster SHALL go with it and SHALL NOT be retained as a roster of nobody. Its
members SHALL leave the fencer list, since they will not fight.

The organizer SHALL confirm it, and the confirmation SHALL state in plain words what the
cancellation does before it is taken: that it cannot be undone, that the team's fee leaves
what the registration pays while its other teams and entries stand, that the roster goes
with the team and its members leave the fencer list, that the place is freed and nobody
moves up from the waitlist by itself, and, on an automatic tournament, that the entering
fencer is written to. No part of it SHALL be stated in the vocabulary of the pricing machinery: the reader is an
organizer cancelling a team, not a reader of the repricing rules.

It SHALL be refused on a registration that is cancelled or expired, and on a tournament
whose team disciplines feature is off — the teams a hidden feature holds are retained
untouched.

The entering fencer SHALL be told, naming the team and the discipline and stating what
the registration now owes or is owed, unless it is a registration Squire sends nothing
to. This is money changing hands and is not the silent correction a roster edit is.

On a manual tournament Squire sends nothing to any registration, so **no mail SHALL be
sent** there, and the confirmation SHALL NOT state that the entering fencer is written to.

#### Scenario: The confirmation says what will happen
- **WHEN** the organizer opens the cancellation of a seated team of four
- **THEN** it states that the cancellation cannot be undone, that the fee leaves the registration, that four fighters leave the fencer list, that the freed place promotes nobody, and that the entering fencer is told

#### Scenario: One team of two cancelled
- **WHEN** a registration carrying two teams has one cancelled
- **THEN** the other team stands, the registration stands, and its total is reduced by the cancelled team's fee alone

#### Scenario: The place is freed but nobody is promoted
- **WHEN** a seated team is cancelled in a discipline with a waitlist
- **THEN** the discipline states one free place and no waitlisted team is admitted

#### Scenario: Its fighters leave the start field
- **WHEN** a team of four is cancelled
- **THEN** those four members are no longer listed on the fencer list

#### Scenario: The entrant is told
- **WHEN** the organizer cancels a team on a paid registration
- **THEN** the entering fencer receives one message naming the team and the discipline and stating the resulting balance

#### Scenario: A manual tournament's entrant is not told
- **WHEN** the organizer cancels a team on a manual tournament, on a registration carrying an address
- **THEN** the team is cancelled, no mail is sent, and the confirmation said nothing about one

#### Scenario: Refused on a dead registration
- **WHEN** the organizer attempts to cancel a team on a cancelled registration
- **THEN** it is refused
