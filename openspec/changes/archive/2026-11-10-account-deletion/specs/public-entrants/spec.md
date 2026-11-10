## ADDED Requirements

### Requirement: A deleted account's row states no payment
On a held tournament's roster, the row of a deleted account SHALL leave the Paid cell empty, whatever the tournament's mode and whatever its registration's settled state, and SHALL NOT be drawn faded. This takes precedence over the Paid column's rules. The row's position SHALL NOT change.

#### Scenario: A paid fencer deletes their account
- **WHEN** a visitor opens a held tournament's roster listing a deleted account that had paid
- **THEN** the row shows the name, identifier, club and nationality and an empty Paid cell
