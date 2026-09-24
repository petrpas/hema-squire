## MODIFIED Requirements

### Requirement: Reminders and expiry notices
The system SHALL send an automatic reminder email, including the payment QR, to an unpaid reservation, a notification when a reservation expires, and a notification when a registration is moved to the substitute queue for non-payment, as `registration` fixes under **Demotion is announced**. Reminder emails SHALL carry the same payment content as the original confirmation, including the EUR amount and EUR QR when the tournament has EUR payments enabled on a non-EUR local currency. Each of these events SHALL be audited.

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

#### Scenario: Demotion notified
- **WHEN** a registration is moved to the substitute queue at seating settlement for owing money
- **THEN** the fencer is notified of the move, and the notice is audited

## ADDED Requirements

### Requirement: Payments arriving on a queued registration
A payment whose VS resolves to a registration sitting entirely in the substitute queue SHALL NOT be credited to it, by an automatic pass or by a bare token. The queue holds no money, and a registration credited there would read as a fencer who paid for a place they do not hold. The transaction SHALL be flagged with a reason of its own, distinct from every expiry reason, naming that the registration is queued.

The fencer SHALL be notified that the payment arrived, that they are waiting in the queue and hold no place, and that the organizer will be in contact. The notice SHALL NOT promise a place and SHALL NOT imply the money is lost.

The organizer SHALL resolve such a transaction in one of two ways:
- by **promoting** the fencer, which re-evaluates the transaction at once, as `seating-queue` fixes, so that it is credited against the placement the fencer now owes for; or
- by **marking it for refund**, the existing action on a flagged transaction, recording the amount against the fencer for manual settlement.

A matching pass SHALL keep re-evaluating such a transaction, as it re-evaluates every flagged one, so that a transaction whose registration has since been promoted by any path is credited by the next pass even where the promotion did not reach it.

A registration holding a seated placement beside a queued one is not sitting entirely in the queue: money arriving on it SHALL be matched against what its seated placements owe, as today.

#### Scenario: Payment on a queued registration held
- **WHEN** a transaction carrying the VS of a registration demoted at settlement arrives
- **THEN** it is flagged with the queued reason, nothing is credited, and the fencer is told the payment arrived and the organizer will be in contact

#### Scenario: Promotion credits the held payment
- **WHEN** the organizer promotes that fencer into a free place
- **THEN** the flagged transaction is credited against the place, and it leaves the flagged list

#### Scenario: Refund instead of a place
- **WHEN** the organizer marks the held transaction for refund
- **THEN** the amount is recorded against the fencer for manual settlement and the registration stays in the queue

#### Scenario: A mixed registration is paid as usual
- **WHEN** a transaction arrives for a registration holding one unpaid seat and one queued placement
- **THEN** it is matched against what the seat owes, exactly as any other payment
