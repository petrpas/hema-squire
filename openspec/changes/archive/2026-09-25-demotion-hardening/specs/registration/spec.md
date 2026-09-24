## MODIFIED Requirements

### Requirement: Reservation lifecycle
A reservation's lifecycle SHALL depend on the tournament's payment mode, and SHALL be governed by two independent clocks that produce two different outcomes:

- The **payment window** is the interval between money being requested and money being due, configured per tournament in days. It belongs to one registration. A reservation whose payment window passes unpaid SHALL expire, freeing any capacity it held and leaving the fencer outside the substitute queue — **except where the registration also holds a substitute placement**, in which case it SHALL be demoted rather than expired, as fixed below. Where the window was opened by a promotion, what the lapse takes back is first the placements that promotion seated, as `seating-queue` fixes under **Organizer promotion from the queue**; a paid seat SHALL NOT be lost for an unpaid promotion.
- The **seating deadline** is a single date for the whole tournament, on which seating settles. A reservation still owing money when the seating deadline passes SHALL be moved to the substitute queue — it SHALL NOT expire, and the placements it is moved out of seats with SHALL join the end of the queue, as **Seating settlement at the deadline** fixes.

The seating deadline SHALL NOT be expressed as a payment window on individual registrations, so that the expiry of a payment window can never release a seat that the seating deadline would have queued.

**A registration holding a substitute placement SHALL NOT expire.** When its payment window passes unpaid, it SHALL be demoted instead: every seated placement becomes a substitute placement joining the end of its discipline's queue, every seated team is waitlisted at the end of its discipline's waitlist, the payment window closes, its stored totals are recomputed, the fencer is notified as **Demotion is announced** fixes, and the registration stays reserved. It loses the seat it did not pay for and keeps, in the queue moment it already held, the queue place it never owed for. A queue place SHALL NOT be forfeited for money owed on a different placement, for the same reason a lapsed promotion after seating settles returns to the queue rather than expiring out of it (`seating-queue`): the fencer's place in line was never what the money was for.

A registration holding no substitute placement SHALL expire on a lapsed payment window exactly as it does today.

**Both clocks SHALL be dormant while the tournament's payments feature is off**, and dormancy SHALL reach every lifecycle pass alike, as fixed by **One dormancy predicate governs the lifecycle passes**. Such a registration SHALL be seated on the same capacity terms as any other, SHALL carry no due date, SHALL open no payment window, SHALL never expire for non-payment, and **SHALL NOT be demoted to the substitute queue when the seating deadline passes**. A seat given without asking for money SHALL NOT be lost for money not paid. Its total SHALL still be computed and presented, as a statement of what the tournament costs rather than a demand, and it SHALL be presented to the fencer as confirmed rather than as awaiting payment. No payment mode SHALL apply to it: the mode describes how money is collected, and no money is being collected.

Dormancy SHALL suspend the demotion, never the closing of seating. A tournament whose registrations are all dormant SHALL still settle its seating on its deadline and SHALL still place subsequent registrations in the queue rather than in seats, because seats are finite whether or not they were paid for; settlement SHALL simply find no registration to move.

A registration issued for an imported or manually entered row SHALL have both clocks dormant **by virtue of its origin**, permanently, whatever the tournament's payments setting, payment mode or seating deadline says at any time. That origin SHALL be one of the causes the predicate above answers with, and it SHALL outlast every setting the others depend on: turning payments on, changing the payment mode or moving the seating deadline SHALL NOT wake it. It SHALL carry no due date, SHALL open no payment window, SHALL never expire for non-payment, SHALL never be demoted when seating settles, and SHALL never be sent a reminder or an expiry notice. Its total SHALL still be computed, stored and presented, and it SHALL still be matched and credited like any other registration: what its origin makes dormant is the passage of time, not the money. The row it came from stated who was competing and, often, that they had already paid; a clock started long afterwards would demand money from people who owe none and mail people who registered a season ago (`imported-registrations`).

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
- **THEN** the seated placement becomes a substitute placement at the end of its discipline's queue, its capacity is freed, the registration stays reserved, and the placement that was already queued keeps its place

#### Scenario: Queue place survives money owed elsewhere
- **WHEN** a fencer never pays for the discipline they were seated in
- **THEN** they remain in the queue for the discipline they were queued in, at the position their queue moment gives them, owing nothing

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

#### Scenario: Payments-off registration keeps its seat past the seating deadline
- **WHEN** the seating deadline passes on a payments-off tournament holding seated registrations
- **THEN** none of them is demoted, every seat is kept, and no capacity is freed

#### Scenario: Seating still closes on a payments-off tournament
- **WHEN** the seating deadline has passed on a payments-off tournament and a fencer registers afterwards
- **THEN** that registration is placed in the substitute queue rather than seated, exactly as it would be on a tournament that collects

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
- **WHEN** the payments setting is turned on, or the payment mode or the seating deadline is changed, after registrations have been issued
- **THEN** those registrations remain seated, acquire no due date, are not demoted when seating settles, and are sent nothing

### Requirement: Seating settlement at the deadline
Seating SHALL settle when the tournament's seating deadline passes, or earlier if the organizer settles it by hand. Settling SHALL do the same thing in both cases: every registration that is still reserved — that is, still owing money — and whose lifecycle clocks are not dormant SHALL have each of its seated discipline entries marked as a substitute placement and each of its non-waitlisted teams waitlisted, in place, freeing the capacity they held. The registration SHALL remain reserved, SHALL keep its VS, SHALL have no payment window, and SHALL have its stored totals recomputed, so that it no longer states the price of a seat it does not hold. Its fencer SHALL be notified as **Demotion is announced** fixes.

A dormant registration SHALL NOT be demoted, for whichever cause made it dormant, as fixed by **One dormancy predicate governs the lifecycle passes**. Being reserved is what identifies a debtor only where money was asked for; where none was, the state means nothing about what is owed and SHALL NOT be read as though it did.

Closing seating SHALL NOT depend on there being anything to demote. Settlement SHALL record the tournament as settled whether it moved every registration or none, so that seating closes on its deadline on every tournament alike and later registrations join the queue.

Each placement moved by settlement SHALL join the **end** of its discipline's queue: its queue moment SHALL be the moment of settlement, so that it ranks after every fencer already waiting, however early it registered. A fencer who held a seat and did not pay for it SHALL NOT take precedence over one who waited in the queue from the start. Registrations moved by one settlement SHALL rank among themselves by registration time. A placement the registration already held in the queue SHALL keep its queue moment. Teams SHALL join the end of their discipline's waitlist on the same terms.

Settlement SHALL be recorded per registration under a distinct audit event.

Settlement SHALL run at most once per tournament, whether triggered by the deadline or by the organizer. A tournament whose seating has settled SHALL NOT settle again, so that registrations the organizer subsequently promotes are never demoted by a later pass.

Settlement SHALL run before payment windows are expired in the same processing pass, so that a registration holding both an expiring payment window and an unmet seating deadline is queued rather than expired, regardless of processing timing.

In **immediate** mode settlement SHALL demote nobody, because no unpaid reservation survives its payment window; it SHALL still close seating, so that later registrations join the queue rather than taking seats.

Seating SHALL be treated as settled when it has been settled explicitly, and also once the seating deadline has passed but the settlement pass has not yet run — so that no registration is seated in the interval between the deadline and the next processing pass.

#### Scenario: Unpaid reservation moved below the line
- **WHEN** the seating deadline passes on a reservation-mode tournament and a seated registration has paid nothing
- **THEN** its entries become substitute placements, its capacity is freed, it stays reserved with its VS, and the demotion is recorded

#### Scenario: Paid registration untouched
- **WHEN** the seating deadline passes and a registration is fully paid
- **THEN** it keeps its seat and nothing about it changes

#### Scenario: Dormant registration untouched
- **WHEN** the seating deadline passes on a registration whose clocks are dormant
- **THEN** it keeps its seat, its capacity is not freed, and no demotion is recorded against it

#### Scenario: Deposit paid, balance not
- **WHEN** the seating deadline passes on a deposit-mode registration that paid its deposit but not its balance
- **THEN** it is moved to the substitute queue, the deposit stays recorded against it and is not refunded, and it does not read as paid

#### Scenario: Demoted registrations join the end of the queue
- **WHEN** two registrations are demoted at settlement and a third, registered between them, was already queued
- **THEN** the already-queued one ranks first, and the two demoted ones follow it in registration order

#### Scenario: Demotion reprices the registration
- **WHEN** a reservation-mode registration owing 1750 for its one seat is demoted at settlement
- **THEN** its stored total no longer includes the seat, and its balance does not state 1750 as owed

#### Scenario: Teams follow their registration
- **WHEN** a demoted registration carries a team that was not waitlisted
- **THEN** that team is waitlisted and its discipline's team capacity is freed

#### Scenario: Settlement does not repeat
- **WHEN** the organizer promotes a fencer off the queue after settlement and the next processing pass runs
- **THEN** the promoted fencer keeps their seat and is not demoted again

#### Scenario: Immediate mode demotes nobody but closes seating
- **WHEN** the seating deadline passes on an immediate-mode tournament
- **THEN** no registration is demoted, because every unpaid one already expired, and subsequent registrations join the queue

#### Scenario: Settlement with nothing to demote still closes seating
- **WHEN** the seating deadline passes on a tournament every one of whose registrations is dormant
- **THEN** no registration is demoted and the tournament is recorded as settled

#### Scenario: Deadline reached before the processing pass runs
- **WHEN** the seating deadline has passed but the settlement pass has not yet run
- **THEN** a registration submitted in that interval is placed in the queue rather than seated

### Requirement: Capacity and substitutes
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When an individual discipline is full, further registrations SHALL join a substitute queue, in the queue order `seating-queue` fixes — for a placement queued at registration, its registration time. When a team discipline is full, further teams SHALL join a team waitlist in entry order, counted in teams rather than fencers, as fixed by `team-disciplines`. When a spot frees through expiry or cancellation, the organizer SHALL be able to admit substitutes from the individual queue; admitting a waitlisted team is not offered.

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

## ADDED Requirements

### Requirement: Demotion is announced
A registration moved to the substitute queue for non-payment SHALL be notified, as an expired one is. This SHALL hold for every path by which non-payment demotes: seating settlement, whether reached by the deadline or triggered by the organizer; a promotion window lapsing after seating has settled; and a payment window lapsing on a registration that also holds a queued placement.

The notice SHALL name each discipline and each team the registration was moved out of a seat in, and the queue position it now holds in each. It SHALL state that nothing is owed while the registration waits, that no payment should be sent, and that a place is offered by the organizer promoting the fencer, at which point a new payment window opens. Where the registration holds credit — a deposit paid, or any partial payment — the notice SHALL state that the amount stays recorded against the registration and counts if the fencer is promoted, and SHALL NOT promise its refund.

A registration the organizer returns to the queue by hand SHALL NOT be sent this notice; the organizer's return is a correction they communicate themselves. A dormant registration is never demoted and so SHALL never be sent it. The notice SHALL be sent once per demotion, and a demotion that moves nothing SHALL send nothing.

The notice SHALL be recorded in the audit trail alongside the demotion it announces.

#### Scenario: Settlement announces the demotion
- **WHEN** a reservation-mode registration is demoted at seating settlement
- **THEN** its fencer is mailed that they were moved to the queue, in which disciplines and at which positions, and that nothing is owed now

#### Scenario: Deposit named in the notice
- **WHEN** a deposit-mode registration that paid its 500 deposit and not its balance is demoted at settlement
- **THEN** the notice states that the 500 stays recorded against the registration and counts on promotion, and does not promise a refund

#### Scenario: A lapsed promotion is announced
- **WHEN** a fencer promoted after settlement lets the promotion window lapse unpaid
- **THEN** they are returned to the queue and mailed that they were

#### Scenario: The organizer's return is not announced
- **WHEN** the organizer returns a seated registration to the queue by hand
- **THEN** no demotion notice is sent

#### Scenario: Nothing moved, nothing sent
- **WHEN** seating settles on a tournament where no registration owes money
- **THEN** no demotion notice is sent to anyone
