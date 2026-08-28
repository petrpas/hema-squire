## MODIFIED Requirements

### Requirement: Queue view for the organizer
The organizer SHALL have a view of the substitute queue per discipline, listing each queued registration in queue order with the fencer, their registration time, and their position. It SHALL show the discipline's free places, so the organizer can see how many promotions are available.

Each entry's registration time SHALL be stated as a day and a clock time together, on the 24-hour scale to the minute, read in the tournament's own zone — never as a day alone. The queue is ordered by that moment, and two fencers on either side of the line can share a day; the view SHALL show what it is ordering by.

The view SHALL offer promotion on each queued entry and return-to-queue on each seated one, and SHALL state plainly when a queue is empty rather than being hidden.

After the seating deadline the system SHALL NOT promote anyone automatically by any rule. The view presents the data; the organizer decides.

#### Scenario: Queue listed in order
- **WHEN** the organizer opens the queue for a discipline with four waiting fencers
- **THEN** all four are listed in registration order with their positions and the discipline's free places

#### Scenario: Two entries registered on one day
- **WHEN** two of the queued fencers registered on the same day, minutes apart
- **THEN** their entries state different clock times, and the order they are listed in is legible from those times

#### Scenario: Empty queue stated
- **WHEN** a discipline has no substitutes
- **THEN** the view states that the queue is empty rather than omitting the discipline

#### Scenario: No automatic promotion
- **WHEN** the seating deadline passes and seats are freed by demotion
- **THEN** no queued registration is promoted automatically, and every seat is filled by an explicit organizer action
