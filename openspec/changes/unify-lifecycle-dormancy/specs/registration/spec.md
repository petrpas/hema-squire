## ADDED Requirements

### Requirement: One dormancy predicate governs the lifecycle passes
Whether Squire runs its lifecycle clocks against a registration SHALL be settled by a single predicate over the tournament and the registration, and every lifecycle pass SHALL consult that predicate and no other condition of its own. The passes so governed are the reminder pass, the expiry pass, the demotion carried out at seating settlement, and the count of pending demotions the console states before the organizer confirms one.

The predicate SHALL yield the **cause** of dormancy rather than a bare yes or no, drawn from a closed set of reasons, so that why a registration is not moving is readable rather than inferred. The causes SHALL be:

- the tournament's **payments feature is off**, so no money was ever requested;
- the registration was **issued from an imported row**, so its clocks are dormant by origin.

A cause SHALL be read from the tournament wherever it is a live setting, so that changing that setting takes effect at once and no stale copy governs a pass. A cause SHALL be stored only where it records an origin that cannot be recomputed from the registration's present contents.

Adding a further reason to leave a registration alone SHALL be an addition to this predicate and SHALL NOT be a condition placed in any pass.

#### Scenario: Every pass agrees
- **WHEN** a registration is dormant for any cause and the lifecycle runs
- **THEN** it receives no reminder, does not expire, is not demoted at settlement, and is not counted among the pending demotions

#### Scenario: The count and the settlement select alike
- **WHEN** the console states how many registrations settling seating would demote, and the organizer then settles
- **THEN** the registrations demoted are exactly those counted, with no registration counted that settlement leaves alone

#### Scenario: A live cause is read live
- **WHEN** a tournament's payments feature is turned on
- **THEN** its registrations cease to be dormant for that cause from that moment, without any registration being rewritten

#### Scenario: The cause is stated
- **WHEN** a registration is dormant
- **THEN** which of the reasons made it dormant is available, rather than only the fact that it is

## MODIFIED Requirements

### Requirement: Reservation lifecycle
A reservation's lifecycle SHALL depend on the tournament's payment mode, and SHALL be governed by two independent clocks that produce two different outcomes:

- The **payment window** is the interval between money being requested and money being due, configured per tournament in days. It belongs to one registration. A reservation whose payment window passes unpaid SHALL expire, freeing any capacity it held and leaving the fencer outside the substitute queue — **except where the registration also holds a substitute placement**, in which case it SHALL be demoted rather than expired, as fixed below.
- The **seating deadline** is a single date for the whole tournament, on which seating settles. A reservation still owing money when the seating deadline passes SHALL be moved to the substitute queue — it SHALL NOT expire, and it SHALL keep its place in registration order.

The seating deadline SHALL NOT be expressed as a payment window on individual registrations, so that the expiry of a payment window can never release a seat that the seating deadline would have queued.

**A registration holding a substitute placement SHALL NOT expire.** When its payment window passes unpaid, it SHALL be demoted instead: every seated placement becomes a substitute placement, every seated team is waitlisted, the payment window closes, and the registration stays reserved in its original registration order. It loses the seat it did not pay for and keeps the queue place it never owed for. A queue place SHALL NOT be forfeited for money owed on a different placement, for the same reason a lapsed promotion after seating settles returns to the queue rather than expiring out of it (`seating-queue`): the fencer's place in line was never what the money was for.

A registration holding no substitute placement SHALL expire on a lapsed payment window exactly as it does today.

**Both clocks SHALL be dormant while the tournament's payments feature is off**, and dormancy SHALL reach every lifecycle pass alike, as fixed by **One dormancy predicate governs the lifecycle passes**. Such a registration SHALL be seated on the same capacity terms as any other, SHALL carry no due date, SHALL open no payment window, SHALL never expire for non-payment, and **SHALL NOT be demoted to the substitute queue when the seating deadline passes**. A seat given without asking for money SHALL NOT be lost for money not paid. Its total SHALL still be computed and presented, as a statement of what the tournament costs rather than a demand, and it SHALL be presented to the fencer as confirmed rather than as awaiting payment. No payment mode SHALL apply to it: the mode describes how money is collected, and no money is being collected.

Dormancy SHALL suspend the demotion, never the closing of seating. A tournament whose registrations are all dormant SHALL still settle its seating on its deadline and SHALL still place subsequent registrations in the queue rather than in seats, because seats are finite whether or not they were paid for; settlement SHALL simply find no registration to move.

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

### Requirement: Seating settlement at the deadline
Seating SHALL settle when the tournament's seating deadline passes, or earlier if the organizer settles it by hand. Settling SHALL do the same thing in both cases: every registration that is still reserved — that is, still owing money — and whose lifecycle clocks are not dormant SHALL have each of its seated discipline entries marked as a substitute placement and each of its non-waitlisted teams waitlisted, in place, freeing the capacity they held. The registration SHALL remain reserved, SHALL keep its VS, and SHALL have no payment window.

A dormant registration SHALL NOT be demoted, for whichever cause made it dormant, as fixed by **One dormancy predicate governs the lifecycle passes**. Being reserved is what identifies a debtor only where money was asked for; where none was, the state means nothing about what is owed and SHALL NOT be read as though it did.

Closing seating SHALL NOT depend on there being anything to demote. Settlement SHALL record the tournament as settled whether it moved every registration or none, so that seating closes on its deadline on every tournament alike and later registrations join the queue.

Settled registrations SHALL take their position in the substitute queue by registration time, ranked among existing substitutes as though they had been queued from the start, so that a fencer who registered early keeps that advantage over one who registered late.

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
- **THEN** it is moved to the substitute queue and the deposit is not refunded

#### Scenario: Registration order preserved across demotion
- **WHEN** two registrations are demoted at settlement and a third was already queued between them by registration time
- **THEN** all three sit in the queue in registration order

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
