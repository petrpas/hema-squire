## ADDED Requirements

### Requirement: A registration's paid date is the day the money arrived
A registration that has become paid SHALL carry the day the money reached the
tournament, not the moment the system learned of it. Where a bank transaction
settled it, that day is the transaction's own date as the statement stated it;
where a payment the organizer recorded settled it, it is the date they entered
as received.

The two are one rule and SHALL be applied at the single place a credit's
consequences are decided, so that a registration cannot be dated one way by a
statement and another way by cash at the desk.

A registration settled by more than one credit SHALL take the day of the credit
that completed it. Where credits are ingested out of the order they arrived in,
that day may precede a credit already held; the system SHALL NOT reconstruct a
later day from the credits already counted, which are amounts and not a history.

Widening the amount tolerance settles registrations on money already received.
Such a settlement SHALL take the day of the transaction it accepted, not the day
the organizer widened the tolerance — the organizer's act is recorded as the
reason on that transaction and as an event, which is where a decision belongs.

Marking a registration settled by hand is the one settlement no money arrived
for, and it SHALL go on carrying the moment of the mark. There is no statement
day behind it, and the day it became settled is the day somebody said so.

Withdrawing every credit that settled a registration SHALL clear the paid date,
exactly as it does today.

The date SHALL be stored as the start of that day in the tournament's own zone —
the zone every other date on that tournament's timeline is read in. A statement
states a day and no clock, and a day belongs to the place the tournament is held.

#### Scenario: A statement imported a week late
- **WHEN** a transaction dated the 3rd settles a registration and the statement carrying it is imported on the 10th
- **THEN** the registration's paid date is the 3rd

#### Scenario: A fortnight of statements imported in one sitting
- **WHEN** several statements spanning two weeks are imported together and each settles a different registration
- **THEN** each registration carries its own transaction's day, and they differ

#### Scenario: Cash recorded days after it was taken
- **WHEN** the organizer records a payment received on the 1st and enters it on the 4th
- **THEN** the registration it settles carries the 1st

#### Scenario: Two half-payments
- **WHEN** a registration is settled by a second transaction dated the 12th, the first having been dated the 5th
- **THEN** its paid date is the 12th

#### Scenario: The tolerance is widened over an old payment
- **WHEN** a transaction dated the 2nd left a registration short, and on the 20th the organizer widens the tolerance so that it settles
- **THEN** the registration's paid date is the 2nd, and the transaction records that the tolerance was what settled it

#### Scenario: A late payment reinstated by the organizer
- **WHEN** the organizer reinstates an expired registration against a transaction dated the 8th
- **THEN** the registration's paid date is the 8th

#### Scenario: A hand mark carries the moment of the mark
- **WHEN** the organizer marks a registration settled by hand
- **THEN** its paid date is that moment, because no money arrived for it to name a day

#### Scenario: The day is the tournament's day
- **WHEN** a transaction dated the 3rd settles a registration on a tournament held in a zone ahead of UTC
- **THEN** the stored paid date is the start of the 3rd in that tournament's zone, not the start of the 3rd in UTC

#### Scenario: The credit is withdrawn
- **WHEN** the payment link that settled a registration is removed and nothing else covers it
- **THEN** the registration returns to reserved and holds no paid date
