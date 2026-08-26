## MODIFIED Requirements

### Requirement: The substitute queue holds no money
A substitute placement SHALL owe nothing. Substitute placements SHALL NOT be priced, SHALL NOT be billed, and SHALL NOT be offered payment instructions, whatever else the registration carrying them holds. Money SHALL be requested for a queued placement only when the organizer promotes it.

This is what keeps the queue free of money that would otherwise need refunding for a seat that never existed. It is a property of the **placement**, not of the registration: a registration may hold a seated placement it owes for and a queued placement it does not, and the money follows the placement in each case.

Three consequences follow and SHALL hold:

- Queue length and queue position SHALL be counted from substitute placements on **live** registrations — those reserved within their validity window, and those paid — rather than from the registration's state. A registration that has paid for a seated placement SHALL still be counted, at its place in registration order, for a placement it holds in the queue. Counting from reserved registrations alone would drop a paid fencer out of the queue they are waiting in and hand their position to somebody else.
- A registration holding a substitute placement SHALL NOT expire on a lapsed payment window; it is demoted instead, as `registration` fixes. Money owed for a seat SHALL NOT cost the fencer a queue place they never owed for.
- Returning a placement to the queue SHALL be refused once the registration has been paid. Demoting a seat that has been paid for would leave money in the queue, and the organizer's route for a paid registration is cancellation, which carries the existing refund handling.

#### Scenario: Queued registration owes nothing
- **WHEN** a fencer's registration is entirely substitute placements
- **THEN** its total is zero, no payment instructions are available to it, and no reminder is sent

#### Scenario: Queued placement on a billed registration still owes nothing
- **WHEN** a registration holds one seated placement and one queued placement
- **THEN** its total covers the seated placement alone, and the queued placement adds nothing to what is owed

#### Scenario: Money requested on promotion
- **WHEN** the organizer promotes a queued registration
- **THEN** its total is computed for the promoted placements, a payment window opens, and payment instructions are sent

#### Scenario: A paid fencer keeps their queue position
- **WHEN** a fencer who has paid for a seated placement also holds a queued placement, and a second fencer registered later holds a queued placement in the same discipline
- **THEN** the paid fencer is counted in that discipline's queue length and ranks ahead of the later fencer by registration time

#### Scenario: Paid registration cannot be returned to the queue
- **WHEN** the organizer attempts to return a paid registration to the queue
- **THEN** the action is refused with a message directing them to cancellation, and the registration keeps its seat

### Requirement: Organizer promotion from the queue
The organizer SHALL be able to promote a queued registration into a seat, one discipline at a time, whenever that discipline has a free place. Promotion SHALL mark the placement as seated, compute what is now owed, open a payment window, and send payment instructions.

Promotion SHALL be available whatever the registration has already paid. A registration that has settled its seated placements and still holds a queued one SHALL be promotable, and promotion SHALL bill the **difference** its new placement adds rather than a fresh total: what the fencer has already paid stands, and a registration that has paid in full does not revert to being unpaid because it gained a placement. This follows the same rule an amendment does when it adds a priced row to a paid registration.

The notice a promotion sends SHALL name the discipline whose place has opened, state the amount now due rather than the registration's total, and state the date by which it is due. A fencer who has already paid once SHALL NOT be sent a demand that reads as though nothing had been paid.

**WHEN the tournament's payments feature is off, promotion SHALL seat the placement and stop there**: no payment window SHALL open, no due date SHALL be set, and no payment instructions SHALL be sent. The promoted fencer SHALL be notified that they have a place, and the amount their registration comes to SHALL be stated as information. A promotion that opens no window cannot lapse, so such a registration SHALL never return to the queue on a clock; it stays seated until the organizer returns it.

The payment window opened by promotion SHALL NOT outlive the tournament: it SHALL be the configured payment window or the remainder of the time until the tournament date, whichever is shorter.

Promotion SHALL be refused when the discipline has no free place, and when the registration is in a state that cannot hold a seat — cancelled or expired. Having been paid SHALL NOT be such a state.

A promoted registration whose payment window then lapses unpaid SHALL return to the substitute queue rather than expiring out of it, keeping its place by registration time — once seating has settled the queue is the tournament's holding area, and expiring would discard a fencer the organizer deliberately chose. Before seating settles, a lapsed payment window SHALL expire the reservation as it does today, unless the registration still holds a substitute placement, which `registration` demotes rather than expires.

#### Scenario: Promotion into a free seat
- **WHEN** the organizer promotes a queued fencer into a discipline with a free place
- **THEN** the placement becomes seated, the amount owed is computed, a payment window opens, and payment instructions are sent

#### Scenario: Promotion of a paid registration bills the difference
- **WHEN** the organizer promotes the queued placement of a registration whose seated placements are paid in full
- **THEN** the placement becomes seated, the fencer owes only what the new placement adds, the registration does not revert to unpaid, and a fresh payment window opens

#### Scenario: Promotion notice states the discipline and the amount due
- **WHEN** a promotion opens a payment window
- **THEN** the notice names the discipline whose place has opened, states the amount now due rather than the registration's total, and states the date by which it is due

#### Scenario: Promotion on a payments-off tournament asks for nothing
- **WHEN** the organizer of a payments-off tournament promotes a queued fencer into a free place
- **THEN** the placement becomes seated, no payment window opens, no due date is set, and the fencer is told they have a place with no payment instructions

#### Scenario: Promotion into a full discipline refused
- **WHEN** the organizer attempts to promote into a discipline at capacity
- **THEN** the action is refused and the queue is unchanged

#### Scenario: Promotion of a cancelled registration refused
- **WHEN** the organizer attempts to promote a placement on a cancelled or expired registration
- **THEN** the action is refused and the queue is unchanged

#### Scenario: Payment window clamped to the tournament
- **WHEN** a fencer is promoted three days before the tournament on a tournament with a seven-day payment window
- **THEN** the payment window closes at the tournament date rather than after seven days

#### Scenario: Promoted fencer lets the window lapse
- **WHEN** a fencer promoted after seating settled does not pay before their payment window closes
- **THEN** they return to the substitute queue in their original registration order, still reserved and owing nothing, rather than expiring

#### Scenario: Lapsed window before settlement still expires
- **WHEN** a reservation's payment window closes unpaid on a tournament whose seating has not settled, and the registration holds no substitute placement
- **THEN** the reservation expires as it does today

#### Scenario: A payments-off promotion never lapses back
- **WHEN** time passes on a payments-off tournament after a promotion
- **THEN** the promoted registration stays seated and returns to the queue only if the organizer returns it
