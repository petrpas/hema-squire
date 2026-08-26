## MODIFIED Requirements

### Requirement: Capacity and substitutes
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When an individual discipline is full, further registrations SHALL join a substitute queue in registration order. When a team discipline is full, further teams SHALL join a team waitlist in entry order, counted in teams rather than fencers, as fixed by `team-disciplines`. When a spot frees through expiry or cancellation, the organizer SHALL be able to admit substitutes from the individual queue; admitting a waitlisted team is not offered.

**Each discipline in a submission SHALL be placed against its own capacity**, independently of every other discipline in the same submission. A selection mixing full and open disciplines SHALL seat the open ones and queue the full ones, in one operation. A full discipline SHALL NOT cost the fencer a seat in an open one, and an open discipline SHALL NOT seat a fencer in a full one. Teams follow the same rule per team, as they already do.

The system SHALL NOT ask the fencer to choose between trimming a full discipline from their selection and waiting for all of them. The placement follows from capacity alone, and the fencer SHALL be told, per discipline, which of their choices were seated and which were queued.

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

### Requirement: Reservation lifecycle
A reservation's lifecycle SHALL depend on the tournament's payment mode, and SHALL be governed by two independent clocks that produce two different outcomes:

- The **payment window** is the interval between money being requested and money being due, configured per tournament in days. It belongs to one registration. A reservation whose payment window passes unpaid SHALL expire, freeing any capacity it held and leaving the fencer outside the substitute queue — **except where the registration also holds a substitute placement**, in which case it SHALL be demoted rather than expired, as fixed below.
- The **seating deadline** is a single date for the whole tournament, on which seating settles. A reservation still owing money when the seating deadline passes SHALL be moved to the substitute queue — it SHALL NOT expire, and it SHALL keep its place in registration order.

The seating deadline SHALL NOT be expressed as a payment window on individual registrations, so that the expiry of a payment window can never release a seat that the seating deadline would have queued.

**A registration holding a substitute placement SHALL NOT expire.** When its payment window passes unpaid, it SHALL be demoted instead: every seated placement becomes a substitute placement, every seated team is waitlisted, the payment window closes, and the registration stays reserved in its original registration order. It loses the seat it did not pay for and keeps the queue place it never owed for. A queue place SHALL NOT be forfeited for money owed on a different placement, for the same reason a lapsed promotion after seating settles returns to the queue rather than expiring out of it (`seating-queue`): the fencer's place in line was never what the money was for.

A registration holding no substitute placement SHALL expire on a lapsed payment window exactly as it does today.

**Both clocks SHALL be dormant while the tournament's payments feature is off.** Such a registration SHALL be seated on the same capacity terms as any other, SHALL carry no due date, SHALL open no payment window, and SHALL never expire for non-payment. Its total SHALL still be computed and presented, as a statement of what the tournament costs rather than a demand, and it SHALL be presented to the fencer as confirmed rather than as awaiting payment. No payment mode SHALL apply to it: the mode describes how money is collected, and no money is being collected.

A registration taken while payments were off SHALL NOT acquire a due date retroactively when the payments feature is turned on. It SHALL remain seated and SHALL NOT expire on account of a window that never opened; what becomes of it is the organizer's decision.

Per mode, on a tournament whose payments feature is on, a seated reservation SHALL be held as follows:

- **immediate** — the full amount is owed at registration and a payment window opens. Unpaid at the end of it, the reservation expires.
- **deposit** — the deposit is owed at registration and a payment window opens for it. Crediting the deposit SHALL close the payment window, leaving the balance owed by the seating deadline. Unpaid at the end of the payment window, the reservation expires; deposit paid but balance unpaid at the seating deadline, it is moved to the substitute queue.
- **reservation** — nothing is owed at registration and no payment window opens. The seat is held until the seating deadline, by which the full amount is owed.

A paid reservation SHALL become a confirmed registration in every mode.

An expired reservation SHALL NOT bar the fencer from the tournament. A fencer whose reservation has expired SHALL be able to register again on the same terms as a fencer who cancelled: the existing registration is reused in place, a fresh window opens where the mode calls for one, and a fresh VS is issued. Capacity SHALL be re-evaluated at that moment like any new registration, so a discipline that filled in the meantime places the returning fencer in the substitute queue rather than seating them. The number of such cycles SHALL NOT be limited.

#### Scenario: Reservation expires unpaid
- **WHEN** the payment window passes with no matched payment
- **THEN** the reservation expires automatically, its discipline capacity is freed, and the fencer is notified

#### Scenario: Mixed registration demoted rather than expired
- **WHEN** the payment window passes unpaid on a registration holding one seated placement and one queued placement
- **THEN** the seated placement becomes a substitute placement, its capacity is freed, the registration stays reserved, and its queue place is kept in its original registration order

#### Scenario: Queue place survives money owed elsewhere
- **WHEN** a fencer never pays for the discipline they were seated in
- **THEN** they remain in the queue for the discipline they were queued in, at the position their registration time gives them, owing nothing

#### Scenario: Payment arrives in time
- **WHEN** a matching payment is ingested before the payment window closes
- **THEN** the reservation becomes a confirmed registration

#### Scenario: Deposit closes the payment window
- **WHEN** a deposit-mode reservation is credited its deposit on day 3 of a 5-day payment window
- **THEN** the payment window closes, the reservation does not expire on day 5, and the balance is owed by the seating deadline

#### Scenario: Free reservation holds without a payment window
- **WHEN** a fencer registers in reservation mode
- **THEN** nothing is owed, no payment window opens, and the seat is held until the seating deadline

#### Scenario: Payments-off registration is seated outright
- **WHEN** a fencer registers for a tournament whose payments feature is off
- **THEN** the registration is seated with no due date and no payment window, its total is shown as information, and it is presented as confirmed

#### Scenario: Payments-off registration never expires
- **WHEN** the scheduler runs against a payments-off tournament long after any configured payment window would have closed
- **THEN** no registration expires, no capacity is freed, and no expiry notice is sent

#### Scenario: Turning payments on does not expire what came before
- **WHEN** a tournament that took registrations with payments off turns payments on and the scheduler runs
- **THEN** those registrations remain seated, none expires, and none is sent an expiry notice

#### Scenario: Re-registration after expiry with seats free
- **WHEN** a fencer whose reservation expired registers again while the selected disciplines have free places
- **THEN** the registration is accepted, reusing the existing row with a fresh window and a fresh VS, and a confirmation email with payment instructions is sent

#### Scenario: Re-registration after expiry into a full discipline
- **WHEN** a fencer whose reservation expired registers again for a discipline that has since filled
- **THEN** that discipline is entered as a substitute placement rather than seated, and no waiting substitute is displaced

#### Scenario: Repeated expiry not penalized
- **WHEN** a fencer's reservation expires unpaid for the second time and they register again
- **THEN** the registration is accepted on the same terms as the first time
