# payments Specification

## Purpose
Match bank payments to reservations by variable symbol, with idempotent ingestion, amount tolerance, manual matching rules, reminders, and foreign-transfer handling.

## Requirements

### Requirement: Payment identity via variable symbol
Each reservation SHALL receive a variable symbol that is unique across the whole deployment, not merely within its tournament. Transaction matching SHALL be performed exclusively by VS — or by the VS quoted in the payment message for transfers that cannot carry a VS field — never by payer name or amount alone.

A newly issued VS SHALL take the structured form `YYNNnnn`: two digits of the tournament's VS year, two digits of the tournament's series within that year, and three digits of registration sequence within that tournament. The value SHALL be seven digits with a leading nonzero digit, so that it survives banks that strip leading zeros and fits both the ten-digit domestic limit and the SPAYD variable-symbol field. Sequence allocation SHALL be per tournament and SHALL be correct when two registrations are created concurrently. Allocation SHALL fail with a clear error when a tournament exhausts its sequence rather than wrapping, truncating, or issuing a value that overruns into the series digits.

**The prefix is documentation, not routing.** Matching SHALL resolve a registration by looking up the complete VS value in a deployment-wide index, and SHALL take the tournament from the registration it resolved. It SHALL NOT parse the year or series digits to decide which tournament a transaction belongs to, because a payer who mistypes one digit would otherwise have their payment reconciled against a different event.

A VS issued before the structured format SHALL continue to match unchanged, and no already-issued VS SHALL ever be rewritten to the new format.

When a transaction's VS resolves to a registration belonging to a **different** tournament than the one being processed — the normal case when two tournaments share one bank account and each ingests the whole statement — the transaction SHALL be recorded as belonging to that other tournament and SHALL be excluded from this tournament's unmatched and flagged queues. It SHALL NOT mark any registration paid, SHALL NOT send any email, and SHALL NOT alter any registration state. The organizer SHALL be told how many transactions were set aside this way, so that a quiet queue is distinguishable from a queue that silently swallowed someone's payment.

#### Scenario: Third party pays for a fencer
- **WHEN** a transaction from a different sender carries a registration's VS
- **THEN** it matches that registration regardless of the sender's name

#### Scenario: Structured VS issued
- **WHEN** a fencer registers for the fifth tournament created for 2026 and is the third registration to it
- **THEN** the issued VS is 2605003

#### Scenario: Sequence is per tournament
- **WHEN** the first registration is created for each of two different tournaments in the same year
- **THEN** both carry sequence 001 and they differ only in their series digits

#### Scenario: Concurrent registrations get distinct symbols
- **WHEN** two fencers register for the same tournament at the same moment
- **THEN** each receives a different VS and neither registration fails

#### Scenario: Sequence exhaustion refused
- **WHEN** a tournament that has issued 999 variable symbols attempts to issue another
- **THEN** the registration is refused with a clear error and no eight-digit or overrunning value is issued

#### Scenario: Sibling tournament's payment is set aside, not queued
- **WHEN** a tournament ingests a statement containing a transaction whose VS belongs to another tournament's registration
- **THEN** the transaction is recorded as belonging to that other tournament, is absent from this tournament's unmatched queue, and no registration is marked paid and no email is sent

#### Scenario: Sibling payment matched by its own tournament
- **WHEN** the tournament that owns that registration ingests its own copy of the same transaction
- **THEN** the transaction matches normally and the registration is marked paid

#### Scenario: Set-aside count reported
- **WHEN** an ingestion sets transactions aside as belonging to other tournaments
- **THEN** the result reports how many were set aside, distinctly from matched, flagged, and unmatched counts

#### Scenario: Mistyped prefix does not route to a sibling
- **WHEN** a transaction carries a VS whose series digits name a different tournament but whose complete value matches no registration
- **THEN** the transaction enters the unmatched queue and no tournament is selected from its prefix

#### Scenario: Legacy variable symbol still matches
- **WHEN** a transaction carries a VS issued before the structured format
- **THEN** it resolves to its registration and matches exactly as it did before

### Requirement: Bank transaction ingestion
The system SHALL ingest transactions via the Fio bank REST API on a schedule and via manual statement import (CSV). Ingestion SHALL be idempotent: each transaction is processed at most once.

#### Scenario: Overlapping statement re-import
- **WHEN** the organizer imports a statement overlapping already-ingested transactions
- **THEN** no transaction is matched or counted twice

### Requirement: Amount tolerance
A VS-matched transaction SHALL be compared against the amount due **denominated in the transaction's own currency**. Where the transaction's currency is the tournament's local currency, it SHALL be compared against the registration's local total; where it is EUR and the tournament prices in EUR as a second currency, it SHALL be compared against the registration's EUR total. The amount due in a currency SHALL be that currency's total less the amount already credited to the registration in that same currency, so that a registration amended upward after payment is owed the difference and one amended downward carries an overpayment rather than appearing settled.

**No conversion SHALL occur at any point in the payment path,** and no exchange ratio SHALL be consulted. A transaction in a currency the tournament does not price in SHALL be flagged with a distinct not-accepted reason and SHALL NOT be compared numerically against a total in another currency.

A transaction SHALL be accepted as full payment when the amount still due in its currency falls within the tournament's configured tolerance (default ±5 %) of zero. That tolerance absorbs bank fees and payer rounding; it is no longer required to absorb any difference between an organizer's recorded ratio and a payer's bank's rate, because neither reaches the comparison. Outside tolerance, the transaction SHALL be flagged for manual resolution rather than silently accepted or ignored.

Amounts credited to a registration SHALL be recorded per currency, and SHALL NOT be summed across currencies — doing so would require an exchange ratio the payment path does not use. A registration SHALL be settled when the amount credited in **either** currency covers that currency's total within tolerance. A registration part-paid in each of two currencies SHALL be flagged for the organizer rather than aggregated. Reverting a manual payment link SHALL remove exactly the amount that link credited, from the currency it credited.

#### Scenario: Local-currency payment matched against the local total
- **WHEN** a CZK transaction carrying a registration's VS arrives against a registration whose local total is 1500 Kč
- **THEN** it is compared against 1500 and no exchange ratio is consulted

#### Scenario: EUR payment matched against the stored EUR total
- **WHEN** a 60 € transaction carrying the VS of a registration whose EUR total is 60 € arrives on a CZK + EUR tournament
- **THEN** it is compared against the stored EUR total, matches exactly, and the registration is marked paid

#### Scenario: Payment slightly short after bank fees
- **WHEN** a payment arrives 3 % below the amount due in its own currency with the correct VS
- **THEN** the registration is marked paid

#### Scenario: Unpriced currency flagged as not accepted
- **WHEN** a VS-matched transaction arrives in a currency the tournament does not price in
- **THEN** the transaction is flagged with a not-accepted reason and is not compared against any total

#### Scenario: EUR payment to a tournament pricing only locally
- **WHEN** a EUR transaction arrives against a CZK-only tournament
- **THEN** it is flagged as not accepted rather than converted and compared

#### Scenario: Amount far off
- **WHEN** a payment with a correct VS arrives 40 % below the amount due in its currency
- **THEN** the transaction is flagged for the organizer instead of confirming the registration

#### Scenario: Ratio change does not affect reconciliation
- **WHEN** the organizer changes the recorded exchange ratio and a payment then arrives for an existing reservation
- **THEN** the comparison is unaffected, because the ratio is not read by matching

#### Scenario: Credited amount recorded in its own currency
- **WHEN** a transaction is matched to a registration
- **THEN** the amount credited in that transaction's currency increases by the transaction's amount, the other currency's credited amount is unchanged, and the audit entry records the amount and its currency

#### Scenario: Credits not summed across currencies
- **WHEN** a registration owing 1500 Kč or 60 € receives 750 Kč and then 30 €
- **THEN** neither currency's credit covers its own total, the payments are not combined, and the registration is flagged for the organizer

#### Scenario: Either currency settles the registration
- **WHEN** a registration owing 1500 Kč or 60 € is credited 60 €
- **THEN** it is marked paid, and no local-currency balance is treated as outstanding

#### Scenario: Reverted link removes its credit
- **WHEN** the organizer removes a manual payment link that had credited a registration
- **THEN** the amount credited in that link's currency returns to what it was before the link was applied

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
The system SHALL send an automatic reminder email, including the payment QR, on the tournament's configured reminder day of an unpaid reservation, and a notification when a reservation expires. Reminder emails SHALL carry the same payment content as the original confirmation, including the EUR amount and EUR QR when the tournament has EUR payments enabled on a non-EUR local currency. Both events SHALL be audited.

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
