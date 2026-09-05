## ADDED Requirements

### Requirement: Outstanding balance in the Payments phase table
The Payments phase's fencer table SHALL carry an outstanding-balance column alongside the total: the registration's total less what has been credited to it. The balance SHALL be a value on the sheet row, so it sorts, exports and reruns with the rest of the table rather than living only in a side panel or in the fencer's own view. Where the tournament prices in a second currency, the column SHALL show the balance in the currency the registration is being settled in.

#### Scenario: Part-paid reservation
- **WHEN** a fencer has paid half of a reservation's total and the organizer opens the Payments phase
- **THEN** the row shows the total and the remaining balance, without the organizer subtracting anything by hand

#### Scenario: Settled reservation
- **WHEN** a registration has been paid in full
- **THEN** its outstanding balance reads as zero

#### Scenario: Balance survives a rerun
- **WHEN** the organizer reruns processing
- **THEN** the outstanding column is recomputed from the current credited amounts, with no rule required to maintain it

#### Scenario: The Payments phase keeps its table
- **WHEN** the organizer opens the Payments phase
- **THEN** the fencer table is present with the outstanding column, below the phase's resolution queues — unlike Deduplication, which replaces the table entirely
