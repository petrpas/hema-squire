## MODIFIED Requirements

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
