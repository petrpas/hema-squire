## MODIFIED Requirements

### Requirement: Partial payments
A payment that credits a registration less than it owes SHALL leave the reservation reserved, with the credited amount recorded and the remaining balance derivable from it. The fencer SHALL be told what is still outstanding, with its currency, rather than being left to work the difference out from a total and a payment they may not have recorded.

A partial payment SHALL NOT change the reservation's payment window. A reservation holding a partial payment SHALL expire on its original schedule like any other.

**In deposit mode this is refined rather than reversed.** The deposit is a threshold the organizer published, not an arbitrary amount the fencer chose, so it cannot be used to renew a hold by paying in dribbles. When the credited amount reaches the tournament's deposit, the payment window SHALL be closed rather than extended: the reservation keeps its seat with no window running, and the balance is owed by the seating deadline instead. Reaching the deposit SHALL be recorded under a distinct audit event. A credit that falls short of the deposit SHALL leave the payment window running unchanged.

Because that expiry leaves the organizer holding money for a reservation that no longer exists, a reservation expiring with a credited amount SHALL be recorded under a distinct audit event, SHALL be presented to the organizer separately from ordinary expiries, and its expiry notice to the fencer SHALL state that the payment is held by the organizer who will be in contact. The notice SHALL NOT imply the money is lost, and SHALL NOT promise a seat.

A deposit SHALL NOT be refunded when the balance never arrives. A registration moved to the substitute queue at the seating deadline keeps its credited amount recorded against it, so that a later promotion counts what was already paid; but the organizer SHALL be under no obligation to return it, and the forfeit terms SHALL be stated in the tournament's registration instructions.

#### Scenario: Partial payment leaves the reservation reserved
- **WHEN** a transaction credits 900 against a reservation owing 1750
- **THEN** the reservation stays reserved, 900 is recorded against it, and 850 is outstanding

#### Scenario: Fencer told the outstanding balance
- **WHEN** a partial payment is credited to a reservation
- **THEN** the fencer is notified of the amount still outstanding with its currency

#### Scenario: Partial payment does not extend the window
- **WHEN** a partial payment is credited on day 4 of a 5-day payment window
- **THEN** the reservation still expires at the end of day 5

#### Scenario: Deposit reached closes the payment window
- **WHEN** a deposit-mode reservation owing 1750 with a 500 deposit is credited 500 on day 2 of a 5-day window
- **THEN** the payment window closes, the reservation does not expire on day 5, 1250 remains outstanding until the seating deadline, and reaching the deposit is recorded

#### Scenario: Credit short of the deposit does not close the window
- **WHEN** the same reservation is credited 300 against a 500 deposit
- **THEN** the payment window keeps running and the reservation expires on schedule if nothing further arrives

#### Scenario: Deposit not refunded on demotion
- **WHEN** a deposit-mode registration reaches the seating deadline with its deposit paid and its balance unpaid
- **THEN** it is moved to the substitute queue, the credited deposit stays recorded against it, and no refund is initiated

#### Scenario: Expiry holding money is recorded distinctly
- **WHEN** a reservation carrying a partial payment expires
- **THEN** a distinct audit event records that it expired holding a credited amount, and the organizer sees it separately from ordinary expiries

#### Scenario: Expiry notice explains the held payment
- **WHEN** a reservation carrying a partial payment expires
- **THEN** the fencer's expiry notice states that the payment is held by the organizer who will be in contact, without implying the money is lost or promising a seat

#### Scenario: Remaining balance arriving in grace settles it
- **WHEN** the rest of the amount arrives within the tournament's expiry grace period and the discipline still has a free place
- **THEN** the reservation is reinstated, the credited amounts together settle the total, and the registration is marked paid

### Requirement: Reminders and expiry notices
The system SHALL send an automatic reminder email, including the payment QR, to an unpaid reservation, and a notification when a reservation expires. Reminder emails SHALL carry the same payment content as the original confirmation, including the EUR amount and EUR QR when the tournament has EUR payments enabled on a non-EUR local currency. Both events SHALL be audited.

The reminder SHALL be sent once, the configured number of days before the obligation the reservation is under falls due — before the payment window closes where one is running, and before the seating deadline where the seat is held without a payment window. A reservation that owes nothing SHALL NOT be reminded.

A registration sitting entirely in the substitute queue owes nothing and SHALL NOT be reminded, in any mode.

#### Scenario: Reminder sent
- **WHEN** a reservation reaches the configured reminder day unpaid
- **THEN** the fencer receives a reminder with the original payment instructions and QR

#### Scenario: Reminder carries the EUR option
- **WHEN** a reminder goes out on a CZK tournament with EUR payments enabled
- **THEN** it carries both the CZK and EUR amounts with their respective QR codes

#### Scenario: Reminder before a payment window closes
- **WHEN** a reservation with a 5-day payment window and a reminder day of 3 reaches day 3 unpaid
- **THEN** a reminder is sent once, naming the amount and the date the window closes

#### Scenario: Reminder before the seating deadline
- **WHEN** a reservation-mode registration holds a seat with no payment window and the seating deadline is the configured number of days away
- **THEN** a reminder is sent once, naming the amount and the seating deadline

#### Scenario: Queued registration not reminded
- **WHEN** a registration sits entirely in the substitute queue as the seating deadline approaches
- **THEN** no reminder is sent, because nothing is owed

#### Scenario: Deposit paid, balance outstanding
- **WHEN** a deposit-mode registration has paid its deposit and the seating deadline approaches with a balance outstanding
- **THEN** a reminder is sent naming the outstanding balance and the seating deadline
