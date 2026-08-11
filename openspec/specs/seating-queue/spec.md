# seating-queue Specification

## Purpose
Define the substitute queue as the tournament's holding area once seating has
settled: that a queued registration holds no money, how the organizer promotes a
queued registration into a free seat and returns a seated one to the queue, how
the organizer settles seating by hand ahead of the deadline, and what the
organizer sees when reading a queue.

## Requirements

### Requirement: The substitute queue holds no money
A registration sitting entirely in the substitute queue SHALL owe nothing. Substitute placements SHALL NOT be priced, SHALL NOT be billed, and SHALL NOT be offered payment instructions. Money SHALL be requested only when the organizer promotes the registration.

This is what keeps the queue free of money that would otherwise need refunding for a seat that never existed. Two consequences follow and SHALL hold:

- A registration in the queue SHALL never be in the paid state, so queue length and queue position remain countable from reserved registrations alone.
- Returning a registration to the queue SHALL be refused once it has been paid. The organizer's route for a paid registration is cancellation, which carries the existing refund handling.

#### Scenario: Queued registration owes nothing
- **WHEN** a fencer's registration is entirely substitute placements
- **THEN** its total is zero, no payment instructions are available to it, and no reminder is sent

#### Scenario: Money requested on promotion
- **WHEN** the organizer promotes a queued registration
- **THEN** its total is computed for the promoted placements, a payment window opens, and payment instructions are sent

#### Scenario: Paid registration cannot be returned to the queue
- **WHEN** the organizer attempts to return a paid registration to the queue
- **THEN** the action is refused with a message directing them to cancellation, and the registration keeps its seat

### Requirement: Organizer promotion from the queue
The organizer SHALL be able to promote a queued registration into a seat, one discipline at a time, whenever that discipline has a free place. Promotion SHALL mark the placement as seated, compute what is now owed, open a payment window, and send payment instructions.

The payment window opened by promotion SHALL NOT outlive the tournament: it SHALL be the configured payment window or the remainder of the time until the tournament date, whichever is shorter.

Promotion SHALL be refused when the discipline has no free place, and when the registration is not in a state that can hold a seat.

A promoted registration whose payment window then lapses unpaid SHALL return to the substitute queue rather than expiring out of it, keeping its place by registration time — once seating has settled the queue is the tournament's holding area, and expiring would discard a fencer the organizer deliberately chose. Before seating settles, a lapsed payment window SHALL expire the reservation as it does today.

#### Scenario: Promotion into a free seat
- **WHEN** the organizer promotes a queued fencer into a discipline with a free place
- **THEN** the placement becomes seated, the amount owed is computed, a payment window opens, and payment instructions are sent

#### Scenario: Promotion into a full discipline refused
- **WHEN** the organizer attempts to promote into a discipline at capacity
- **THEN** the action is refused and the queue is unchanged

#### Scenario: Payment window clamped to the tournament
- **WHEN** a fencer is promoted three days before the tournament on a tournament with a seven-day payment window
- **THEN** the payment window closes at the tournament date rather than after seven days

#### Scenario: Promoted fencer lets the window lapse
- **WHEN** a fencer promoted after seating settled does not pay before their payment window closes
- **THEN** they return to the substitute queue in their original registration order, still reserved and owing nothing, rather than expiring

#### Scenario: Lapsed window before settlement still expires
- **WHEN** a reservation's payment window closes unpaid on a tournament whose seating has not settled
- **THEN** the reservation expires as it does today

### Requirement: Organizer return to the queue
The organizer SHALL be able to return a seated registration to the substitute queue, one discipline at a time — the inverse of promotion. Returning SHALL mark the placement as a substitute, free the seat, and close any payment window the registration was under.

A returned registration SHALL keep its position by registration time, so returning and promoting again does not cost the fencer their place relative to other substitutes.

#### Scenario: Seated registration returned to the queue
- **WHEN** the organizer returns a reserved, unpaid, seated registration to the queue
- **THEN** its placement becomes a substitute, the seat is freed, and no payment window remains on it

#### Scenario: Queue position preserved
- **WHEN** a registration is returned to the queue among substitutes who registered both before and after it
- **THEN** it sits between them in registration order

### Requirement: Organizer-triggered seating settlement
The organizer SHALL be able to settle seating from the console before the seating deadline arrives — closing seating early once the roster is as they want it. It SHALL do exactly what the deadline does: demote every registration still owing money to the substitute queue, and place every subsequent registration in the queue rather than a seat.

It SHALL be available in every payment mode. In immediate mode it demotes nobody but still closes seating.

It SHALL be refused on a tournament whose seating has already settled, so settlement happens once however it is triggered.

It SHALL NOT be reversible, and the console SHALL confirm before firing it, stating how many registrations will be demoted. The organizer's route to correct an individual case afterwards is promotion.

#### Scenario: Organizer settles early
- **WHEN** the organizer settles seating a week before the seating deadline
- **THEN** every registration still owing money is demoted to the queue, and the tournament is recorded as settled

#### Scenario: Confirmation states the effect
- **WHEN** the organizer opens the settle action on a tournament with eleven unpaid seated registrations
- **THEN** the confirmation states that eleven registrations will be moved to the queue and that the action cannot be undone

#### Scenario: Settling twice refused
- **WHEN** the organizer attempts to settle a tournament whose seating has already settled
- **THEN** the action is refused and nothing changes

#### Scenario: Scheduled settlement does not follow a manual one
- **WHEN** the seating deadline passes on a tournament the organizer already settled by hand
- **THEN** no registration is demoted a second time, including any the organizer promoted in between

#### Scenario: Settling in immediate mode
- **WHEN** the organizer settles seating on an immediate-mode tournament
- **THEN** no registration is demoted and subsequent registrations join the queue

### Requirement: Queue view for the organizer
The organizer SHALL have a view of the substitute queue per discipline, listing each queued registration in queue order with the fencer, their registration time, and their position. It SHALL show the discipline's free places, so the organizer can see how many promotions are available.

The view SHALL offer promotion on each queued entry and return-to-queue on each seated one, and SHALL state plainly when a queue is empty rather than being hidden.

After the seating deadline the system SHALL NOT promote anyone automatically by any rule. The view presents the data; the organizer decides.

#### Scenario: Queue listed in order
- **WHEN** the organizer opens the queue for a discipline with four waiting fencers
- **THEN** all four are listed in registration order with their positions and the discipline's free places

#### Scenario: Empty queue stated
- **WHEN** a discipline has no substitutes
- **THEN** the view states that the queue is empty rather than omitting the discipline

#### Scenario: No automatic promotion
- **WHEN** the seating deadline passes and seats are freed by demotion
- **THEN** no queued registration is promoted automatically, and every seat is filled by an explicit organizer action
