## ADDED Requirements

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
A VS-matched transaction SHALL be accepted as full payment when its amount is within the tournament's configured tolerance (default ±5 %) of the amount due, absorbing currency-conversion noise. Outside tolerance, the transaction SHALL be flagged for manual resolution rather than silently accepted or ignored.

#### Scenario: Foreign-currency payment slightly short
- **WHEN** a payment converted from another currency arrives 3 % below the amount due with the correct VS
- **THEN** the registration is marked paid

#### Scenario: Amount far off
- **WHEN** a payment with a correct VS arrives 40 % below the amount due
- **THEN** the transaction is flagged for the organizer instead of confirming the registration

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
The system SHALL send an automatic reminder email, including the payment QR, on the tournament's configured reminder day of an unpaid reservation, and a notification when a reservation expires. Both events SHALL be audited.

#### Scenario: Reminder sent
- **WHEN** a reservation reaches the configured reminder day unpaid
- **THEN** the fencer receives a reminder with the original payment instructions and QR

### Requirement: Foreign transfers without a VS field
Payment instructions for foreign payers SHALL request the VS in the payment message, and ingestion SHALL parse message fields for a VS. Foreign payments that still fail to match SHALL be resolved manually; the system MAY suggest candidates by name and amount, but only a human confirms the match.

#### Scenario: SEPA payment with VS in the message
- **WHEN** a SEPA transaction carries the VS in its message text
- **THEN** it matches automatically like a domestic VS payment
