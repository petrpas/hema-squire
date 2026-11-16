## ADDED Requirements

### Requirement: A bare token is judged against the same tolerance
Whether a transaction carrying a bare variable symbol covers the registration's outstanding balance SHALL be judged against the tolerance every other comparison uses: the tournament's percentage of the registration's total in the transaction's currency, not of what is still owed. A payment SHALL NOT be held to a narrower window because its symbol was written without a label.

#### Scenario: A top-up quoting a bare symbol
- **WHEN** a registration totalling 1000 Kč has paid 500 Kč, the tolerance is 5 %, and a transaction of 470 Kč carries its symbol as a bare number
- **THEN** it is credited, the registration reads as paid, and it is not left as a candidate
