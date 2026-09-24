## MODIFIED Requirements

### Requirement: Capacity and substitutes
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When an individual discipline is full, further registrations SHALL join a substitute queue, in the queue order `seating-queue` fixes — for a placement queued at registration, its registration time. When a team discipline is full, further teams SHALL join a team waitlist in entry order, counted in teams rather than fencers, as fixed by `team-disciplines`. When a spot frees, the organizer SHALL be able to admit substitutes from the individual queue and waitlisted teams from a team waitlist, as `seating-queue` fixes.

**Each discipline in a submission without a participation condition SHALL be placed against its own capacity**, independently of every other discipline in the same submission. A submission carrying a participation condition is placed as **Participation condition** fixes. A selection mixing full and open disciplines SHALL seat the open ones and queue the full ones, in one operation. A full discipline SHALL NOT cost the fencer a seat in an open one, and an open discipline SHALL NOT seat a fencer in a full one. Teams follow the same rule per team, as they already do.

The system SHALL NOT ask the fencer to choose between trimming a full discipline from their selection and waiting for all of them. The placement follows from capacity and the fencer's own participation condition alone, and the fencer SHALL be told, per discipline, which of their choices were seated and which were queued.

A registration holding both seated and queued placements SHALL be billed for its seated placements only, on the ordinary terms of the tournament's payment mode. Its queued placements SHALL remain unpriced, as `seating-queue` fixes for every substitute placement.

#### Scenario: Discipline full
- **WHEN** a fencer registers for a discipline at capacity
- **THEN** the registration enters the substitute queue and the fencer is informed of their position

#### Scenario: Team discipline full
- **WHEN** a fencer enters a team into a team discipline holding teams to capacity
- **THEN** the team is waitlisted in entry order, its fee is not charged, and the fencer is informed

#### Scenario: Mixed selection placed per discipline
- **WHEN** a fencer submits one registration for a full discipline and a discipline with free places
- **THEN** the open discipline is seated and the full one is queued, in the same registration

#### Scenario: Mixed registration billed for its seat only
- **WHEN** a registration holds one seated placement and one queued placement
- **THEN** its total covers the seated placement and its extras, the queued placement adds nothing, and a payment window opens on the ordinary terms of the tournament's payment mode

#### Scenario: Fencer told what was seated and what was queued
- **WHEN** a submission mixing full and open disciplines is accepted
- **THEN** the response and the confirmation state, per discipline, which placements are seated and which are queued, with the queue position of each queued placement

#### Scenario: No trim-or-wait choice is demanded
- **WHEN** a fencer submits a selection containing a full discipline
- **THEN** the submission is accepted and placed, and is never refused in order to ask the fencer to choose between trimming the selection and queueing all of it

## ADDED Requirements

## ADDED Requirements
