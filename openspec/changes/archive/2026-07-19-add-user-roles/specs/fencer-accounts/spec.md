# fencer-accounts Specification (delta)

## ADDED Requirements

### Requirement: Administrative HR unbinding
An Admin SHALL be able to unbind a wrongly linked HEMA Ratings profile from an account: the hr_id is cleared while profile fields keep their current values, and the change is recorded in the profile audit trail. The account can then be bound to the correct profile through the existing binding flow. Fencer-initiated rebinding SHALL remain rejected — the binding stays write-once from the fencer's side.

#### Scenario: Admin unbinds a wrong profile
- **WHEN** an Admin clears the hr_id of an account linked to the wrong HEMA Ratings profile
- **THEN** the hr_id is empty, the unbinding is audited, and the fencer can bind the correct profile

#### Scenario: Fencer still cannot rebind
- **WHEN** a fencer whose account already has an hr_id attempts to bind a different profile
- **THEN** the request is rejected as before
