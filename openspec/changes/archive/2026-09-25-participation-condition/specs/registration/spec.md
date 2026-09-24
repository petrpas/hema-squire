## MODIFIED Requirements

### Requirement: Capacity and substitutes
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When an individual discipline is full, further registrations SHALL join a substitute queue, in the queue order `seating-queue` fixes — for a placement queued at registration, its registration time. When a team discipline is full, further teams SHALL join a team waitlist in entry order, counted in teams rather than fencers, as fixed by `team-disciplines`. When a spot frees through expiry or cancellation, the organizer SHALL be able to admit substitutes from the individual queue; admitting a waitlisted team is not offered.

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

### Requirement: Participation condition
A registration MAY carry a **participation condition**: a set of its individual disciplines that the fencer attends only together. The system SHALL hold the condition as a set, so that any subset of the registration's individual disciplines can be expressed. Team disciplines SHALL NOT be part of it.

**The form offers it as one tick.** Where a submission selects at least two individual disciplines, the registration form SHALL offer a single tick stating that the fencer attends only if they get a place in every individual discipline selected. Ticked, the condition is every individual discipline selected; unticked, there is none. The tick SHALL be unticked by default. Where fewer than two individual disciplines are selected it SHALL NOT be offered, and a submission carrying a condition over fewer than two disciplines SHALL be refused. The tick's text SHALL state its consequence: while any of the disciplines is full, the fencer waits in the queue for all of them and holds no place in any.

**Placement.** A submission with a condition SHALL be placed as follows:
- where every discipline of the condition has a free place, those disciplines SHALL be seated together, and every other discipline of the submission SHALL then be placed against its own capacity;
- where any discipline of the condition has no free place, **every** individual placement of the submission SHALL be queued, including disciplines with free places and disciplines outside the condition. Such a registration holds no seat anywhere and owes nothing; a fencer waiting for all their disciplines does not block a place anyone else could take.
- once seating has settled, every placement is queued, as for any registration.

The confirmation and the fencer's registration detail SHALL state the condition, and where it is not met, which of its disciplines has no free place.

**Invariant.** At every moment a registration's condition SHALL be either wholly seated or wholly queued. No path — placement, promotion, return, demotion, amendment, hand entry — SHALL leave part of a condition seated and part queued.

**Amendment.** An amendment SHALL re-place the registration under its new selection and condition. Ticking the condition, or adding to it a discipline that has no free place, SHALL queue the whole registration; unticking it, or removing the full discipline from it, SHALL place what is free. The amendment form SHALL state, before submitting, when the amendment would move the registration into the queue. An amendment that would move into the queue a registration holding credit SHALL be refused with a reason directing the fencer to the organizer: a fencer's own edit SHALL NOT put money in the queue.

Every registration existing before the condition was introduced SHALL have none.

#### Scenario: Condition met
- **WHEN** a fencer ticks the condition on Longsword and Sabre and both have free places
- **THEN** both are seated and billed

#### Scenario: Condition not met
- **WHEN** a fencer ticks the condition on Longsword and Sabre, Longsword has a free place and Sabre is full
- **THEN** both placements are queued, no seat is taken in Longsword, nothing is owed, and the confirmation states that Sabre is full

#### Scenario: No condition, as today
- **WHEN** a fencer selects the same two disciplines without the tick
- **THEN** Longsword is seated and Sabre queued

#### Scenario: Tick not offered for one discipline
- **WHEN** a fencer selects one individual discipline
- **THEN** the tick is not offered

#### Scenario: A general condition over a subset
- **WHEN** a registration's condition is Longsword and Sabre, it also enters Rapier, and all three have free places
- **THEN** Longsword and Sabre are seated together and Rapier is seated on its own

#### Scenario: Outside disciplines wait with an unmet condition
- **WHEN** that registration's condition cannot be met because Sabre is full while Rapier has a free place
- **THEN** Rapier is queued too, and the registration holds no seat

#### Scenario: Amendment ticking the condition warns first
- **WHEN** a fencer seated in Longsword and queued in Sabre opens an amendment and ticks the condition
- **THEN** the form states that the registration will move into the queue before it is submitted

#### Scenario: Amendment refused where money would enter the queue
- **WHEN** a fencer who has paid for Longsword ticks the condition while Sabre is full
- **THEN** the amendment is refused and the fencer is directed to the organizer

#### Scenario: Existing registrations unchanged
- **WHEN** the condition is introduced on a deployment holding registrations
- **THEN** none of them carries a condition and none is re-placed
