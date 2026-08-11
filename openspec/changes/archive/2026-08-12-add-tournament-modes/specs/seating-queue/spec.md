## MODIFIED Requirements

### Requirement: Organizer promotion from the queue
The organizer SHALL be able to promote a queued registration into a seat, one discipline at a time, whenever that discipline has a free place. Promotion SHALL mark the placement as seated, compute what is now owed, open a payment window, and send payment instructions.

**WHEN the tournament's payments feature is off, promotion SHALL seat the placement and stop there**: no payment window SHALL open, no due date SHALL be set, and no payment instructions SHALL be sent. The promoted fencer SHALL be notified that they have a place, and the amount their registration comes to SHALL be stated as information. A promotion that opens no window cannot lapse, so such a registration SHALL never return to the queue on a clock; it stays seated until the organizer returns it.

The payment window opened by promotion SHALL NOT outlive the tournament: it SHALL be the configured payment window or the remainder of the time until the tournament date, whichever is shorter.

Promotion SHALL be refused when the discipline has no free place, and when the registration is not in a state that can hold a seat.

A promoted registration whose payment window then lapses unpaid SHALL return to the substitute queue rather than expiring out of it, keeping its place by registration time — once seating has settled the queue is the tournament's holding area, and expiring would discard a fencer the organizer deliberately chose. Before seating settles, a lapsed payment window SHALL expire the reservation as it does today.

#### Scenario: Promotion into a free seat
- **WHEN** the organizer promotes a queued fencer into a discipline with a free place
- **THEN** the placement becomes seated, the amount owed is computed, a payment window opens, and payment instructions are sent

#### Scenario: Promotion on a payments-off tournament asks for nothing
- **WHEN** the organizer of a payments-off tournament promotes a queued fencer into a free place
- **THEN** the placement becomes seated, no payment window opens, no due date is set, and the fencer is told they have a place with no payment instructions

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

#### Scenario: A payments-off promotion never lapses back
- **WHEN** time passes on a payments-off tournament after a promotion
- **THEN** the promoted registration stays seated and returns to the queue only if the organizer returns it
