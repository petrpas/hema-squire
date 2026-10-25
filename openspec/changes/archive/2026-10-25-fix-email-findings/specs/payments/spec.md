## MODIFIED Requirements

### Requirement: Payments arriving after expiry
A VS-matched payment SHALL NOT be left permanently unresolved because the reservation it names is no longer reserved. Every such transaction SHALL reach one of three outcomes: reinstated and paid, resolved by an explicit organizer action, or routed to refund.

A payment whose VS resolves to an **expired** reservation SHALL reinstate that reservation and proceed to the normal amount comparison when both conditions hold: the transaction arrives no later than the tournament's expiry grace period after the reservation's expiry instant, and every seated discipline on the registration still has a free place.

The grace period SHALL be 48 hours and SHALL NOT be an organizer parameter, as fixed by `tournament-admin`; matching SHALL nevertheless read it from the tournament rather than from a constant, so that a tournament carrying a different stored value is matched against that value and the period can be offered again without a migration. Reinstatement SHALL be recorded in the audit trail under its own event kind, distinct from a clean match, so a reinstated registration is never indistinguishable from one paid on time. Reinstatement SHALL NOT seat a fencer ahead of a waiting substitute: where a discipline has since filled, the payment SHALL NOT reinstate, whatever its timing.

A payment that does not qualify — outside the grace period, or into a discipline that has filled — SHALL remain flagged, with a reason distinguishing the two cases, and the organizer SHALL have two explicit actions on the flagged transaction: reinstate the registration, offered only where capacity allows and applying the same effect as automatic reinstatement; and mark the payment for refund, recording the amount against the fencer for manual settlement. Both actions SHALL be audited and SHALL leave the transaction resolved rather than flagged.

**The organizer's reinstatement SHALL follow its credit with the same amount comparison as automatic reinstatement**, against the same tolerance. It SHALL NOT treat the registration as paid because a person chose to reinstate it.

**A reinstatement whose credit leaves more than tolerance outstanding** — automatic or by the organizer — SHALL leave the registration reserved and owing. It SHALL open a fresh payment window of the tournament's configured length from the moment of reinstatement, since the window it had has already closed. The fencer SHALL be sent one message that says the reservation was reinstated, states the amount received and the amount still due, and carries the payment instructions with a QR code for the remainder. That message SHALL NOT state that participation is confirmed.

A payment whose VS resolves to a **cancelled** registration SHALL always be routed to the refund path and SHALL never reinstate the registration, regardless of when it arrived.

The fencer SHALL be notified of the outcome in both directions: that the reservation was reinstated and the payment accepted, or that the payment arrived after the reservation had expired and the organizer will be in contact. A fencer whose payment arrives late SHALL NOT be left with the expiry notice as the last word from the system.

#### Scenario: Payment inside the grace period reinstates
- **WHEN** a transaction carrying the VS of a reservation that expired 12 hours ago arrives, the grace period is 48 hours, and the discipline still has a free place
- **THEN** the reservation is reinstated, the amount is compared as usual, the registration becomes paid, and the reinstatement is recorded in the audit trail under its own event kind

#### Scenario: Payment outside the grace period stays flagged with organizer actions
- **WHEN** a transaction carrying a reservation's VS arrives 5 days after that reservation expired and the grace period is 48 hours
- **THEN** the transaction is flagged with a reason naming the elapsed grace, and the organizer is offered the reinstate and mark-for-refund actions on it

#### Scenario: Grace does not displace a substitute
- **WHEN** a payment arrives within the grace period but the reservation's discipline has filled since the expiry
- **THEN** the reservation is not reinstated, the transaction is flagged with a capacity reason, and no waiting substitute loses their place

#### Scenario: Organizer reinstates a late payment
- **WHEN** the organizer applies the reinstate action to a flagged post-expiry payment that covers the total, and whose discipline has a free place
- **THEN** the registration becomes reserved and then paid, the action is audited, and the transaction is no longer flagged

#### Scenario: Organizer reinstates a payment that falls short
- **WHEN** the organizer reinstates a registration totalling 1800 Kč on a flagged payment of 500 Kč
- **THEN** the registration is reserved and owes 1300 Kč under a fresh payment window, and the fencer is told it was reinstated, that 500 Kč was received and 1300 Kč is still due, with a QR code for 1300 Kč and no statement that participation is confirmed

#### Scenario: Automatic reinstatement on a partial payment
- **WHEN** a payment of 500 Kč arrives within grace on an expired registration totalling 1800 Kč with a seat free
- **THEN** the reservation is reinstated under a fresh payment window, and the fencer receives the single reinstatement message stating 500 Kč received and 1300 Kč still due, not the plain partial-payment message

#### Scenario: Organizer marks a late payment for refund
- **WHEN** the organizer applies the mark-for-refund action to a flagged post-expiry payment
- **THEN** the amount is recorded against the fencer for manual settlement, the refund state becomes pending, the action is audited, and the transaction is no longer flagged

#### Scenario: Payment on a cancelled registration never reinstates
- **WHEN** a transaction carrying the VS of a cancelled registration arrives one hour after the cancellation
- **THEN** the registration stays cancelled and the payment is routed to the refund path

#### Scenario: Fencer told their late payment arrived
- **WHEN** a payment is received for a reservation that had already expired and cannot be reinstated
- **THEN** the fencer is notified that the payment arrived after expiry and that the organizer will be in contact

#### Scenario: Fencer told of a reinstatement
- **WHEN** a reservation is reinstated by a payment within the grace period
- **THEN** the fencer is notified that the reservation was reinstated and the payment accepted

### Requirement: Reminders and expiry notices
The system SHALL send an automatic reminder email, including the payment QR, to an unpaid reservation, a notification when a reservation expires, and a notification when a registration is moved to the substitute queue for non-payment, as `registration` fixes under **Demotion is announced**. Reminder emails SHALL carry the same payment content as the original confirmation, including the EUR amount and EUR QR when the tournament has EUR payments enabled on a non-EUR local currency, with one exception. **Once a registration holds credit, its reminder SHALL state the outstanding balance, and each QR code SHALL encode the outstanding balance of its own currency** rather than the total, so that following the reminder never overpays. Each of these events SHALL be audited.

What a reminder states about when money is due SHALL follow the payment mode as the confirmation does (`registration`, Confirmation email with QR payment). It SHALL name the date the payment window closes where one is running, and the seating deadline where the seat is held without one. It SHALL NOT state an expiry or a release of the place where neither will happen.

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
- **THEN** a reminder is sent once, naming the amount and the seating deadline, and stating that an unpaid seat is moved to the substitute queue that day rather than that it expires

#### Scenario: Queued registration not reminded
- **WHEN** a registration sits entirely in the substitute queue as the seating deadline approaches
- **THEN** no reminder is sent, because nothing is owed

#### Scenario: Deposit paid, balance outstanding
- **WHEN** a deposit-mode registration totalling 1800 Kč has paid its 500 Kč deposit and the seating deadline approaches
- **THEN** a reminder is sent naming the outstanding 1300 Kč and the seating deadline, and its QR code encodes 1300 Kč

#### Scenario: Demotion notified
- **WHEN** a registration is moved to the substitute queue at seating settlement for owing money
- **THEN** the fencer is notified of the move, and the notice is audited
