## ADDED Requirements

### Requirement: Seating settles on the tournament's own day
The seating deadline SHALL be evaluated as a whole day in the tournament's
timezone, as `day-boundaries` fixes for every date the organizer entered.
Seating settles once the whole of the deadline's local day has passed, and not
before — a tournament held in Prague settles after midnight in Prague, whatever
timezone the deployment runs in.

The three questions the deadline answers SHALL be answered on that one clock:
when the automatic settlement pass fires, whether seating counts as settled for
a registration arriving now, and how far a reservation is from its reminder day
when the deadline is what anchors it. A deployment SHALL NOT be able to reach a
state where seating counts as settled while the settlement pass has not run.

#### Scenario: Settlement waits for the local midnight
- **WHEN** a tournament held in a zone ahead of UTC has a seating deadline of the 20th, and a lifecycle pass runs after midnight UTC on the 21st but before midnight where the tournament is held
- **THEN** seating is not settled, no registration is demoted, and a registration arriving now still takes a free seat

#### Scenario: Settled-ness and settlement agree
- **WHEN** a registration is submitted at the same moment a lifecycle pass runs, on a deployment whose process timezone is not UTC
- **THEN** the registration is placed by the same answer the pass acted on — queued if the pass settled, seated if it did not

#### Scenario: The deadline holds across process timezones
- **WHEN** the same tournament and the same moment are judged on deployments in different process timezones
- **THEN** seating settles on the same day in all of them
