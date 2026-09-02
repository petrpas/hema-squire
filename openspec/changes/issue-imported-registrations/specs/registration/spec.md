## MODIFIED Requirements

### Requirement: Reservation lifecycle
A reservation's lifecycle SHALL depend on the tournament's payment mode, and SHALL be governed by two independent clocks that produce two different outcomes:

- The **payment window** is the interval between money being requested and money being due, configured per tournament in days. It belongs to one registration. A reservation whose payment window passes unpaid SHALL expire, freeing any capacity it held and leaving the fencer outside the substitute queue — **except where the registration also holds a substitute placement**, in which case it SHALL be demoted rather than expired, as fixed below.
- The **seating deadline** is a single date for the whole tournament, on which seating settles. A reservation still owing money when the seating deadline passes SHALL be moved to the substitute queue — it SHALL NOT expire, and it SHALL keep its place in registration order.

The seating deadline SHALL NOT be expressed as a payment window on individual registrations, so that the expiry of a payment window can never release a seat that the seating deadline would have queued.

**A registration holding a substitute placement SHALL NOT expire.** When its payment window passes unpaid, it SHALL be demoted instead: every seated placement becomes a substitute placement, every seated team is waitlisted, the payment window closes, and the registration stays reserved in its original registration order. It loses the seat it did not pay for and keeps the queue place it never owed for. A queue place SHALL NOT be forfeited for money owed on a different placement, for the same reason a lapsed promotion after seating settles returns to the queue rather than expiring out of it (`seating-queue`): the fencer's place in line was never what the money was for.

A registration holding no substitute placement SHALL expire on a lapsed payment window exactly as it does today.

**Both clocks SHALL be dormant while the tournament's payments feature is off.** Such a registration SHALL be seated on the same capacity terms as any other, SHALL carry no due date, SHALL open no payment window, and SHALL never expire for non-payment. Its total SHALL still be computed and presented, as a statement of what the tournament costs rather than a demand, and it SHALL be presented to the fencer as confirmed rather than as awaiting payment. No payment mode SHALL apply to it: the mode describes how money is collected, and no money is being collected.

A registration issued for an imported or manually entered row SHALL have both clocks dormant by virtue of its origin, permanently, whatever the tournament's payments feature, payment mode or seating deadline says at any time. It SHALL carry no due date, SHALL open no payment window, SHALL never expire for non-payment, and SHALL never be sent a reminder or an expiry notice. Its total SHALL still be computed, stored and presented, and it SHALL still be matched and credited like any other registration: what its origin makes dormant is the passage of time, not the money. The row it came from stated who was competing and, often, that they had already paid; a clock started long afterwards would demand money from people who owe none and mail people who registered a season ago (`imported-registrations`).

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

#### Scenario: An issued registration never expires
- **WHEN** the lifecycle passes run against a tournament holding issued registrations, long after any configured payment window would have closed
- **THEN** none of them expires, no capacity is freed, and none is sent an expiry notice or a reminder

#### Scenario: Configuration cannot wake an issued registration's clocks
- **WHEN** the payments feature is turned on, or the payment mode or the seating deadline is changed, after registrations have been issued
- **THEN** those registrations remain seated, acquire no due date, and are sent nothing
