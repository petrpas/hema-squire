## ADDED Requirements

### Requirement: A paid registration is under no payment window
A reserved registration that reads as settled SHALL carry no payment window. Whatever settled it — a credit, a waiver, a tolerance widened over money already received, a discount code, an amendment downward — the window it was registered or promoted under SHALL be closed, as the deposit threshold already closes it in `deposit` mode. The scheduler SHALL close the window of every reserved, settled registration on each pass of the tournament's tick, so that no route to settlement needs to remember to do it.

A registration that is no longer reserved SHALL keep the window it had. An expired registration's window is what the grace period of **Payments arriving after expiry** is measured from.

#### Scenario: Paying closes the window
- **WHEN** a reservation whose window closes on the 10th is credited its full total on the 5th and the tick then runs
- **THEN** it reads as paid and carries no payment window

#### Scenario: A waiver closes the window
- **WHEN** the organizer waives a reservation still under its window and the tick then runs
- **THEN** it reads as paid and carries no payment window

#### Scenario: An expired registration keeps its window
- **WHEN** an expired registration is credited money and the tick runs
- **THEN** its window is unchanged, and a later payment's grace is still measured from it

### Requirement: Losing the paid reading opens a fresh payment window
A registration that read as settled and no longer does SHALL be put under a fresh payment window, measured from the moment it lost the reading and clamped to the tournament as a promotion's window is (`seating-queue`). It SHALL NOT be judged by the window it was registered under, which has usually passed: a fencer who paid SHALL NOT lose their place within one tick over something an organizer did.

This SHALL hold for every action that can take the reading away, and one rule SHALL decide the window for all of them: an amendment raising the total beyond tolerance, the reversal of a credited transaction, the removal of a payment link, the removal of a recorded payment, the revocation of a waiver, and a change to the tournament's settings — the amount tolerance among them — after which a registration no longer reads as settled. No window SHALL open where the registration's clocks do not run, where the payments feature is off, or where the registration sits entirely in the substitute queue.

Losing the reading SHALL NOT send the fencer a message of its own. Where the action has a message of its own — an amendment's surcharge notice — that message is sent as it is today. The registration's reminder SHALL be re-armed, so that the ordinary reminder is sent before the fresh window closes even where one was sent under the old window.

#### Scenario: A credit reversed after the window
- **WHEN** the organizer reverses the transaction that settled a registration whose original window closed a week ago, and the tick then runs
- **THEN** the registration reads as reserved under a fresh payment window and does not expire

#### Scenario: Correcting a recorded payment
- **WHEN** the organizer removes the recorded payment that settled a registration after its window, the tick runs, and the organizer then records the corrected amount
- **THEN** the registration is reserved between the two steps, the second record is accepted, and the registration reads as paid again

#### Scenario: Revoking a waiver after the window
- **WHEN** the organizer revokes the waiver of a registration whose original window has passed, and the tick then runs
- **THEN** the registration reads as reserved under a fresh payment window and does not expire

#### Scenario: Removing a payment link after the window
- **WHEN** the organizer removes the payment link whose credit settled a registration after its window, and the tick then runs
- **THEN** the registration reads as reserved under a fresh payment window and does not expire

#### Scenario: Tightening the tolerance
- **WHEN** a registration owing 1000 Kč was credited 970 Kč under a 5 % tolerance after its window, and the organizer sets the tolerance to 2 %
- **THEN** the change is saved, the registration owes 30 Kč under a fresh payment window, and the tick does not expire it

#### Scenario: No mail when the reading is lost
- **WHEN** a registration loses its paid reading by any of these actions other than an amendment
- **THEN** the fencer is sent nothing at that moment, and is reminded before the fresh window closes

#### Scenario: A dormant registration gets no window
- **WHEN** a registration whose clocks do not run loses its paid reading
- **THEN** no payment window opens on it

### Requirement: EUR payments cannot be withdrawn from under EUR money
A tournament update after which a registration holding live EUR credit would have no EUR lane — EUR payments switched off on a tournament pricing in another local currency — SHALL be refused, stating how many registrations hold such credit, and nothing in the update SHALL be saved. EUR credit outside any lane would leave a fencer who paid in euros owing in full, with nothing to settle against the money they sent.

The organizer SHALL be able to switch EUR off once no registration holds live EUR credit — once that credit has been reversed or removed.

#### Scenario: Switching EUR off with euro payers
- **WHEN** the organizer of a CZK tournament with EUR payments on switches EUR off while two registrations hold live EUR credit
- **THEN** the update is refused stating that two registrations hold EUR payments, EUR payments stay on, and both registrations still read as paid

#### Scenario: Switching EUR off with no euro money
- **WHEN** the organizer switches EUR off on a tournament where no registration holds live EUR credit
- **THEN** the update is saved
