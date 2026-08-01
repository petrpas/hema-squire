## MODIFIED Requirements

### Requirement: Payment and reservation parameters
Per tournament, the organizer SHALL configure: reservation validity in days, reminder day, amount-matching tolerance in percent, refundable-until date, the bank account used in payment instructions, the public-list treatment of unpaid registrations, and the expiry grace period in hours.

The expiry grace period SHALL define how long after a reservation expires a payment carrying its VS may still reinstate it, subject to capacity. It SHALL default to 48 hours for a new tournament and SHALL accept zero, which disables automatic reinstatement and routes every post-expiry payment to explicit organizer action.

The reminder day MUST fall before the reservation validity period ends. A reminder day at or beyond the validity period SHALL be rejected with a message naming both values, because expiry runs before reminders: such a reservation would always be expired before its reminder was due, and no reminder would ever be sent.

#### Scenario: Parameters applied
- **WHEN** the organizer sets reservation validity to 10 days and the reminder to day 5
- **THEN** new reservations expire after 10 unpaid days and reminder emails go out on day 5

#### Scenario: Grace period default
- **WHEN** the organizer creates a tournament without touching the grace period
- **THEN** it is 48 hours, and a payment arriving within 48 hours of expiry can reinstate the reservation

#### Scenario: Grace period disabled
- **WHEN** the organizer sets the expiry grace period to zero
- **THEN** no payment reinstates a reservation automatically and every post-expiry payment is flagged for organizer action

#### Scenario: Reminder day at or beyond expiry rejected
- **WHEN** the organizer sets the reminder day to 10 with a reservation validity of 10 days
- **THEN** the update is rejected with a message naming both values, and no tournament is left in a state where reminders are silently never sent

#### Scenario: Reminder day shortened below a valid reminder
- **WHEN** the organizer shortens reservation validity to 5 days on a tournament whose reminder day is 7
- **THEN** the update is rejected, since the combination would stop reminders being sent
