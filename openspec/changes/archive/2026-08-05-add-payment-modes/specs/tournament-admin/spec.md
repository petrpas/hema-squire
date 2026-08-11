## MODIFIED Requirements

### Requirement: Payment and reservation parameters
Per tournament, the organizer SHALL configure: the payment mode, the payment window in days, the reminder day, the amount-matching tolerance in percent, the refundable-until date, the bank account used in payment instructions, the public-list treatment of unpaid registrations, and the expiry grace period in hours. In deposit mode the organizer SHALL additionally configure the deposit amount.

The **payment mode** SHALL be one of:

- **immediate payment** — the full amount is owed at registration;
- **reservation with deposit** — a deposit is owed at registration and the balance by the seating deadline;
- **reservation without deposit** — nothing is owed at registration and the full amount is owed by the seating deadline.

It SHALL default to immediate payment, which is the behaviour of a tournament created before the mode existed.

The **payment window** is the number of days between money being requested and money being due; it exists because bank transfers do not settle instantly. It SHALL apply wherever money is requested — at registration in immediate and deposit modes, and on promotion from the substitute queue in every mode. It SHALL be accepted between 2 and 7 days inclusive. A tournament configured before that range was introduced SHALL keep its stored value until the parameter is next edited.

The **deposit** SHALL be a flat amount, never a percentage of the total, so that amending a registration can never change a deposit that has already been paid. It is a price like every other: a whole-unit amount in the tournament's local currency, plus an independent EUR amount where the tournament prices in EUR, and it participates in the setup completeness check on the same terms as other prices. It SHALL be required and greater than zero in deposit mode, and SHALL be ignored in the other modes.

The expiry grace period SHALL define how long after a reservation expires a payment carrying its VS may still reinstate it, subject to capacity. It SHALL default to 48 hours for a new tournament and SHALL accept zero, which disables automatic reinstatement and routes every post-expiry payment to explicit organizer action.

The reminder day MUST fall before the payment window ends. A reminder day at or beyond the payment window SHALL be rejected with a message naming both values, because expiry runs before reminders: such a reservation would always be expired before its reminder was due, and no reminder would ever be sent.

#### Scenario: Parameters applied
- **WHEN** the organizer sets the payment window to 5 days and the reminder to day 3
- **THEN** new reservations expire after 5 unpaid days and reminder emails go out on day 3

#### Scenario: Mode defaults to immediate payment
- **WHEN** the organizer creates a tournament without choosing a payment mode
- **THEN** it is immediate payment, the full amount is owed at registration, and no deposit or seating behaviour applies

#### Scenario: Payment window outside the accepted range
- **WHEN** the organizer sets the payment window to 14 days
- **THEN** the update is rejected with a message naming the accepted range

#### Scenario: Existing longer window kept until edited
- **WHEN** a tournament configured with a 10-day payment window is loaded and other parameters are read
- **THEN** its stored window is unchanged and reservations continue to behave as before

#### Scenario: Deposit required in deposit mode
- **WHEN** the organizer selects reservation with deposit and leaves the deposit amount empty
- **THEN** the update is rejected, naming the missing deposit

#### Scenario: Deposit priced in both currencies
- **WHEN** the tournament prices in EUR alongside its local currency and the organizer sets a deposit
- **THEN** both the local and the EUR deposit amounts are required, neither is derived from the other, and setup is incomplete until both are filled

#### Scenario: Grace period default
- **WHEN** the organizer creates a tournament without touching the grace period
- **THEN** it is 48 hours, and a payment arriving within 48 hours of expiry can reinstate the reservation

#### Scenario: Grace period disabled
- **WHEN** the organizer sets the expiry grace period to zero
- **THEN** no payment reinstates a reservation automatically and every post-expiry payment is flagged for organizer action

#### Scenario: Reminder day at or beyond expiry rejected
- **WHEN** the organizer sets the reminder day to 5 with a payment window of 5 days
- **THEN** the update is rejected with a message naming both values, and no tournament is left in a state where reminders are silently never sent

#### Scenario: Reminder day shortened below a valid reminder
- **WHEN** the organizer shortens the payment window to 3 days on a tournament whose reminder day is 4
- **THEN** the update is rejected, since the combination would stop reminders being sent

## ADDED Requirements

### Requirement: Seating deadline
The organizer SHALL be able to set a **seating deadline**: the date on which the tournament's seating settles. It is distinct from the registration close, and the difference SHALL be stated where it is configured:

- **registration close** — the hard boundary; after it no registration is accepted at all;
- **seating deadline** — a soft boundary inside it; after it registration is still accepted but grants only a place in the substitute queue, and any money still owed on a seated registration has become overdue.

The seating deadline SHALL be optional. Unset, it SHALL resolve to the registration close, which itself resolves to the tournament date — so a tournament with no explicit deadline settles its seating when registration closes and has no organizer-managed tail.

A seating deadline later than the registration close SHALL be rejected, since it could never be reached.

The seating deadline SHALL apply to the whole tournament, never to an individual discipline.

#### Scenario: Deadline set within the registration window
- **WHEN** the organizer sets a seating deadline four weeks before the registration close
- **THEN** it is accepted, and registrations submitted after it join the substitute queue

#### Scenario: Deadline after registration close rejected
- **WHEN** the organizer sets a seating deadline later than the registration close
- **THEN** the update is rejected with a message naming both dates

#### Scenario: Deadline left unset
- **WHEN** the organizer saves a tournament with no seating deadline
- **THEN** seating settles at the registration close, and no separate deadline is presented to fencers

#### Scenario: Deadline distinguished from registration close in setup
- **WHEN** the organizer views the payment and reservation parameters
- **THEN** the seating deadline is labelled and explained so it cannot be mistaken for the registration close
