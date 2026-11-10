# data-retention Specification

## Purpose
Define the periods after which personal data ages out: finished mail and expired tokens by age, and a tournament's bank text, contact addresses and free-text details twelve months after its date, while money stays reconcilable and rosters are kept without a period.

## Requirements
### Requirement: Finished mail and expired tokens are deleted
A scheduler pass SHALL delete an outgoing message 30 days after it was sent or given up on, an expired pending signup, and an expired password reset. A message still waiting for delivery SHALL NOT be deleted.

#### Scenario: Sent message ages out
- **WHEN** a pass runs 31 days after a message was sent
- **THEN** the message no longer exists

#### Scenario: Waiting message stays
- **WHEN** a message has not finished delivery
- **THEN** it stays and keeps being retried

### Requirement: Bank text is removed 12 months after the tournament
Twelve months after a tournament's date, its bank transactions SHALL lose payer name, payer account, message and every other free-text field. Amount, currency, date, variable symbol, matching status, matched registration and the bank's transaction id SHALL remain, and every balance and revenue figure SHALL read as before. A statement imported again SHALL NOT re-create a pruned transaction.

#### Scenario: Balances unchanged
- **WHEN** a tournament passes its 12 months
- **THEN** payer details are gone and every registration's credited sum and the revenue figures are unchanged

#### Scenario: Statement imported again
- **WHEN** a statement holding a pruned transaction is imported
- **THEN** no row is added and no text returns

### Requirement: Contact and free-text details are removed with it
At the same moment, the tournament's registrations SHALL lose their contact address, notes and accommodation, its manual rows their address and notes, and its imported rows their addresses and free-text values. Each tournament SHALL be pruned once and the moment SHALL be recorded.

#### Scenario: Held roster unchanged
- **WHEN** a tournament has been pruned
- **THEN** its rosters and Export tab list the same people in the same order

### Requirement: Rosters are not subject to a period
No retention period SHALL remove a name, HR ID, club or nationality from a roster. Such data SHALL leave only through `account-deletion`'s rules and Admin erasure.

#### Scenario: Ten years later
- **WHEN** a tournament is ten years old
- **THEN** its rosters still list their entrants
