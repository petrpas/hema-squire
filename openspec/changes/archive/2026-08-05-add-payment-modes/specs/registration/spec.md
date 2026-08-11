## MODIFIED Requirements

### Requirement: Reservation lifecycle
A reservation's lifecycle SHALL depend on the tournament's payment mode, and SHALL be governed by two independent clocks that produce two different outcomes:

- The **payment window** is the interval between money being requested and money being due, configured per tournament in days. It belongs to one registration. A reservation whose payment window passes unpaid SHALL expire, freeing any capacity it held and leaving the fencer outside the substitute queue.
- The **seating deadline** is a single date for the whole tournament, on which seating settles. A reservation still owing money when the seating deadline passes SHALL be moved to the substitute queue — it SHALL NOT expire, and it SHALL keep its place in registration order.

The seating deadline SHALL NOT be expressed as a payment window on individual registrations, so that the expiry of a payment window can never release a seat that the seating deadline would have queued.

Per mode, a seated reservation SHALL be held as follows:

- **immediate** — the full amount is owed at registration and a payment window opens. Unpaid at the end of it, the reservation expires.
- **deposit** — the deposit is owed at registration and a payment window opens for it. Crediting the deposit SHALL close the payment window, leaving the balance owed by the seating deadline. Unpaid at the end of the payment window, the reservation expires; deposit paid but balance unpaid at the seating deadline, it is moved to the substitute queue.
- **reservation** — nothing is owed at registration and no payment window opens. The seat is held until the seating deadline, by which the full amount is owed.

A paid reservation SHALL become a confirmed registration in every mode.

An expired reservation SHALL NOT bar the fencer from the tournament. A fencer whose reservation has expired SHALL be able to register again on the same terms as a fencer who cancelled: the existing registration is reused in place, a fresh window opens where the mode calls for one, and a fresh VS is issued. Capacity SHALL be re-evaluated at that moment like any new registration, so a discipline that filled in the meantime places the returning fencer in the substitute queue rather than seating them. The number of such cycles SHALL NOT be limited.

#### Scenario: Reservation expires unpaid
- **WHEN** the payment window passes with no matched payment
- **THEN** the reservation expires automatically, its discipline capacity is freed, and the fencer is notified

#### Scenario: Payment arrives in time
- **WHEN** a matching payment is ingested before the payment window closes
- **THEN** the reservation becomes a confirmed registration

#### Scenario: Deposit closes the payment window
- **WHEN** a deposit-mode reservation is credited its deposit on day 3 of a 5-day payment window
- **THEN** the payment window closes, the reservation does not expire on day 5, and the balance is owed by the seating deadline

#### Scenario: Free reservation holds without a payment window
- **WHEN** a fencer registers in reservation mode
- **THEN** nothing is owed, no payment window opens, and the seat is held until the seating deadline

#### Scenario: Re-registration after expiry with seats free
- **WHEN** a fencer whose reservation expired registers again while the selected disciplines have free places
- **THEN** the registration is accepted, reusing the existing row with a fresh window and a fresh VS, and a confirmation email with payment instructions is sent

#### Scenario: Re-registration after expiry into a full discipline
- **WHEN** a fencer whose reservation expired registers again for a discipline that has since filled
- **THEN** that discipline is entered as a substitute placement rather than seated, and no waiting substitute is displaced

#### Scenario: Repeated expiry not penalized
- **WHEN** a fencer's reservation expires unpaid for the second time and they register again
- **THEN** the registration is accepted on the same terms as the first time

## ADDED Requirements

### Requirement: Seating settlement at the deadline
Seating SHALL settle when the tournament's seating deadline passes, or earlier if the organizer settles it by hand. Settling SHALL do the same thing in both cases: every registration that is still reserved — that is, still owing money — SHALL have each of its seated discipline entries marked as a substitute placement and each of its non-waitlisted teams waitlisted, in place, freeing the capacity they held. The registration SHALL remain reserved, SHALL keep its VS, and SHALL have no payment window.

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

#### Scenario: Deadline reached before the processing pass runs
- **WHEN** the seating deadline has passed but the settlement pass has not yet run
- **THEN** a registration submitted in that interval is placed in the queue rather than seated

### Requirement: Registration after seating has settled
Registration SHALL remain open after seating has settled until registration closes, but SHALL NOT grant a seat. A registration submitted after seating has settled SHALL be placed entirely in the substitute queue regardless of available capacity, and SHALL owe nothing until the organizer promotes it.

The fencer SHALL be told at submission that they are joining the queue rather than the tournament.

#### Scenario: Late registration is queued despite free seats
- **WHEN** a fencer registers after the seating deadline for a discipline with free places
- **THEN** the registration is accepted as a substitute placement, no seat is taken, and nothing is owed

#### Scenario: Queued after an early manual settlement
- **WHEN** the organizer settles seating a week before the seating deadline and a fencer then registers for a discipline with free places
- **THEN** the registration joins the queue, because seating has settled even though the deadline has not arrived

#### Scenario: Late registrant informed
- **WHEN** a fencer submits a registration after seating has settled
- **THEN** the confirmation states that they are in the substitute queue and that the organizer decides on promotion

#### Scenario: Registration close still applies
- **WHEN** a fencer attempts to register after registration has closed
- **THEN** the submission is refused, as it is today, regardless of the seating deadline
