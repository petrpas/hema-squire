## ADDED Requirements

### Requirement: A removed row states where it was removed
Replay SHALL state, on every row it marks removed, the phase of the rule that
removed it — the deletion, or the merge that absorbed it. Where several rules
have removed and returned a row in turn, the stated phase SHALL be that of the
latest removal standing, and a row a restoration has returned SHALL state no
removing phase at all.

The removing phase SHALL be a replay product, derived afresh from the rule set
on every replay and stored nowhere: identical inputs state the same phase, and
withdrawing the removing rule withdraws it.

A row whose removing phase is not one the console offers SHALL be treated as
removed nowhere in particular rather than as removed everywhere, so that a
phase no longer in the order cannot make a row unreachable.

#### Scenario: A deletion states its phase
- **WHEN** a row is deleted by a rule belonging to the Payments phase
- **THEN** the replayed row is marked removed and states Payments as where it was removed

#### Scenario: A restoration clears it
- **WHEN** that row is then restored
- **THEN** the replayed row is neither marked removed nor states a removing phase

#### Scenario: The latest removal wins
- **WHEN** a row deleted on Import is restored and deleted again on Deduplication
- **THEN** the replayed row states Deduplication, not Import

#### Scenario: A merge states its phase
- **WHEN** a merge decided on Deduplication absorbs a row
- **THEN** the absorbed row states Deduplication as where it was removed, alongside the row it was merged into

#### Scenario: Withdrawing the rule withdraws the phase
- **WHEN** the rule that deleted a row is removed from the rule set
- **THEN** the next replay produces a row that is neither removed nor states a removing phase, without any stored value to clean up
