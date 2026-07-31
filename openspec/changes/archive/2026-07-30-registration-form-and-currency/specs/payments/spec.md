## MODIFIED Requirements

### Requirement: Amount tolerance
A VS-matched transaction SHALL be compared against the amount due in the tournament's primary currency. When the transaction's currency differs from the primary currency, its amount SHALL first be converted into the primary currency at the tournament's stored exchange rate; a transaction in a currency for which no rate is configured SHALL be flagged with a distinct currency reason rather than compared as if the amounts were commensurable. The converted transaction SHALL be accepted as full payment when it is within the tournament's configured tolerance (default ±5 %) of the amount due, absorbing both conversion noise and the spread between the organizer's configured rate and the payer's bank's rate. Outside tolerance, the transaction SHALL be flagged for manual resolution rather than silently accepted or ignored.

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
