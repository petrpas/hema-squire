## ADDED Requirements

### Requirement: Discount codes survive an export
The canonical export document SHALL carry the tournament's discount codes, and each registration SHALL state the code it carries and whether a code covered its total. A restore SHALL reconstruct them, so that a registration's total, what it owes and whether it reads as paid are unchanged. A document produced before codes existed SHALL load as a tournament with none. The export document is available only to console access, as it is today.

#### Scenario: Codes round-trip
- **WHEN** a tournament with two codes, one holder of which is covered in full, is exported and restored
- **THEN** both codes exist with their limits and effects, uses read as before, and the covered holder reads as paid with no credit

#### Scenario: Older document
- **WHEN** a v19 document is restored
- **THEN** it loads with no codes and no registration carries one
