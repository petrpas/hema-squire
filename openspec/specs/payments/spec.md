# payments Specification

## Purpose
Match bank payments to reservations by variable symbol, with idempotent ingestion, amount tolerance, manual matching rules, reminders, and foreign-transfer handling.

## Requirements

### Requirement: Payment identity via variable symbol
Each reservation SHALL receive a unique numeric VS. Transaction matching SHALL be performed exclusively by VS — or by the VS quoted in the payment message for transfers that cannot carry a VS field — never by payer name or amount alone.

#### Scenario: Third party pays for a fencer
- **WHEN** a transaction from a different sender carries a registration's VS
- **THEN** it matches that registration regardless of the sender's name

### Requirement: Bank transaction ingestion
The system SHALL ingest transactions via the Fio bank REST API on a schedule and via manual statement import (CSV). Ingestion SHALL be idempotent: each transaction is processed at most once.

#### Scenario: Overlapping statement re-import
- **WHEN** the organizer imports a statement overlapping already-ingested transactions
- **THEN** no transaction is matched or counted twice

### Requirement: Amount tolerance
A VS-matched transaction SHALL be compared against the amount due in the tournament's primary currency. The amount due SHALL be the registration's current total less the amount already credited to it, so that a registration amended upward after payment is owed the difference and one amended downward carries an overpayment rather than appearing settled. When the transaction's currency differs from the primary currency, its amount SHALL first be converted into the primary currency at the tournament's stored exchange rate; a transaction in a currency for which no rate is configured SHALL be flagged with a distinct currency reason rather than compared as if the amounts were commensurable. The converted transaction SHALL be accepted as full payment when it is within the tournament's configured tolerance (default ±5 %) of the amount due, absorbing both conversion noise and the spread between the organizer's configured rate and the payer's bank's rate. Outside tolerance, the transaction SHALL be flagged for manual resolution rather than silently accepted or ignored.

The amount credited to a registration SHALL be recorded in the primary currency at the rate applied when the payment was matched, and reverting a manual payment link SHALL remove exactly the amount that link credited.

#### Scenario: Foreign-currency payment slightly short
- **WHEN** a payment converted from another currency arrives 3 % below the amount due with the correct VS
- **THEN** the registration is marked paid

#### Scenario: EUR payment matched against a CZK total
- **WHEN** a CZK tournament with EUR payments enabled at 25.5 receives a 68.63 EUR transaction carrying the VS of a reservation owing 1750 CZK
- **THEN** the amount is converted at the stored rate, falls within tolerance, and the registration is marked paid

#### Scenario: Unconvertible currency flagged with its own reason
- **WHEN** a VS-matched transaction arrives in a currency for which the tournament has no configured rate
- **THEN** the transaction is flagged with a currency reason and is not compared numerically against the primary-currency total

#### Scenario: Amount far off
- **WHEN** a payment with a correct VS arrives 40 % below the amount due
- **THEN** the transaction is flagged for the organizer instead of confirming the registration

#### Scenario: Credited amount recorded on the match
- **WHEN** a transaction is matched to a registration
- **THEN** the amount credited to that registration increases by the transaction's amount in the primary currency, and the audit entry records both what arrived and what it counted as

#### Scenario: Reverted link removes its credit
- **WHEN** the organizer removes a manual payment link that had credited a registration
- **THEN** the amount credited to that registration returns to what it was before the link was applied

### Requirement: Payments arriving after expiry
A VS-matched payment SHALL NOT be left permanently unresolved because the reservation it names is no longer reserved. Every such transaction SHALL reach one of three outcomes: reinstated and paid, resolved by an explicit organizer action, or routed to refund.

A payment whose VS resolves to an **expired** reservation SHALL reinstate that reservation and proceed to the normal amount comparison when both conditions hold: the transaction arrives no later than the tournament's configured expiry grace period after the reservation's expiry instant, and every seated discipline on the registration still has a free place. Reinstatement SHALL be recorded in the audit trail under its own event kind, distinct from a clean match, so a reinstated registration is never indistinguishable from one paid on time. Reinstatement SHALL NOT seat a fencer ahead of a waiting substitute: where a discipline has since filled, the payment SHALL NOT reinstate, whatever its timing.

A payment that does not qualify — outside the grace period, or into a discipline that has filled — SHALL remain flagged, with a reason distinguishing the two cases, and the organizer SHALL have two explicit actions on the flagged transaction: reinstate the registration, offered only where capacity allows and applying the same effect as automatic reinstatement; and mark the payment for refund, recording the amount against the fencer for manual settlement. Both actions SHALL be audited and SHALL leave the transaction resolved rather than flagged.

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
- **WHEN** the organizer applies the reinstate action to a flagged post-expiry payment whose discipline has a free place
- **THEN** the registration becomes reserved and then paid, the action is audited, and the transaction is no longer flagged

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

### Requirement: Automatic matching outcome
WHEN a transaction matches a reservation within tolerance, the system SHALL mark the registration paid, confirm its capacity, send a payment confirmation email, update the public participant list, and record the match in the audit trail. Transactions with an unknown or missing VS SHALL enter an unmatched queue.

#### Scenario: Clean match
- **WHEN** a scheduled Fio poll ingests a transaction with a known VS and a valid amount
- **THEN** the reservation becomes paid and the fencer appears on the public list without organizer action

### Requirement: Manual matching
The organizer SHALL be able to link an unmatched transaction to one or more registrations in the Payments phase. The link SHALL persist as a rule (surviving reruns and re-ingestion) and SHALL support one payer covering multiple registrations.

#### Scenario: One transfer covers two fencers
- **WHEN** the organizer links a single transaction to two registrations
- **THEN** both registrations are marked paid and the link is recorded as a removable rule

### Requirement: Reminders and expiry notices
The system SHALL send an automatic reminder email, including the payment QR, on the tournament's configured reminder day of an unpaid reservation, and a notification when a reservation expires. Reminder emails SHALL carry the same payment content as the original confirmation, including the EUR amount and EUR QR when the tournament has EUR payments enabled on a non-EUR primary currency. Both events SHALL be audited.

#### Scenario: Reminder sent
- **WHEN** a reservation reaches the configured reminder day unpaid
- **THEN** the fencer receives a reminder with the original payment instructions and QR

#### Scenario: Reminder carries the EUR option
- **WHEN** a reminder goes out on a CZK tournament with EUR payments enabled
- **THEN** it carries both the CZK and EUR amounts with their respective QR codes

### Requirement: Foreign transfers without a VS field
Payment instructions for foreign payers SHALL request the VS in the payment message, and ingestion SHALL parse message fields for a VS. Where the tournament accepts EUR, the foreign payer SHALL be given a EUR amount and a EUR-denominated SPAYD QR against the tournament's configured IBAN. Foreign payments that still fail to match SHALL be resolved manually; the system MAY suggest candidates by name and amount, but only a human confirms the match.

#### Scenario: SEPA payment with VS in the message
- **WHEN** a SEPA transaction carries the VS in its message text
- **THEN** it matches automatically like a domestic VS payment

#### Scenario: Foreign payer receives a EUR amount
- **WHEN** a fencer registers for a CZK tournament that has EUR payments enabled
- **THEN** the payment instructions state a EUR amount and offer a EUR-denominated QR code against the same IBAN
