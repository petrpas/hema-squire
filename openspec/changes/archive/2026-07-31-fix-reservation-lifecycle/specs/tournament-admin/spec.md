## MODIFIED Requirements

### Requirement: Payment and reservation parameters
Per tournament, the organizer SHALL configure: reservation validity in days, reminder day, amount-matching tolerance in percent, refundable-until date, the bank account used in payment instructions, the public-list treatment of unpaid registrations, and the expiry grace period in hours.

The expiry grace period SHALL define how long after a reservation expires a payment carrying its VS may still reinstate it, subject to capacity. It SHALL default to 48 hours for a new tournament and SHALL accept zero, which disables automatic reinstatement and routes every post-expiry payment to explicit organizer action.

#### Scenario: Parameters applied
- **WHEN** the organizer sets reservation validity to 10 days and the reminder to day 5
- **THEN** new reservations expire after 10 unpaid days and reminder emails go out on day 5

#### Scenario: Grace period default
- **WHEN** the organizer creates a tournament without touching the grace period
- **THEN** it is 48 hours, and a payment arriving within 48 hours of expiry can reinstate the reservation

#### Scenario: Grace period disabled
- **WHEN** the organizer sets the expiry grace period to zero
- **THEN** no payment reinstates a reservation automatically and every post-expiry payment is flagged for organizer action

### Requirement: Registration window
A tournament SHALL have optional registration-opens and registration-closes dates. Registration SHALL be unavailable before the opens date (when set) and after the closes date (when set); with no closes date, registration stays available until the tournament date. With no opens date, registration is available as soon as setup is complete.

A tournament SHALL additionally have an optional amendments-close date, after which fencers may no longer amend their registrations even while registration itself remains open. With no amendments-close date set, amendment SHALL be available on exactly the same window as registration. When both are set, the amendments-close date MUST NOT fall after the registration-closes date, and the combination SHALL be rejected with a clear message — a later value would never be reached.

#### Scenario: Before opening
- **WHEN** a fencer visits registration before the registration-opens date
- **THEN** registration is unavailable and the opening date is shown

#### Scenario: No close date set
- **WHEN** no registration-closes date is set
- **THEN** registration remains available through the tournament date

#### Scenario: Amendments close before registration
- **WHEN** the organizer sets an amendments-close date two weeks before the registration-closes date
- **THEN** fencers may still register in those two weeks but may no longer amend an existing registration

#### Scenario: Amendments follow registration by default
- **WHEN** no amendments-close date is set
- **THEN** amendment is available exactly while registration is available

#### Scenario: Amendments-close after registration-close rejected
- **WHEN** the organizer sets an amendments-close date later than the registration-closes date
- **THEN** the update is rejected with a message naming the conflict
