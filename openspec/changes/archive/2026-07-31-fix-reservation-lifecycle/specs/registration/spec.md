## MODIFIED Requirements

### Requirement: Reservation lifecycle
A reservation SHALL be valid for the tournament's configured number of days from registration. There SHALL be no global payment deadline — each reservation carries its own window. An unpaid reservation SHALL expire automatically at the end of its window, freeing any capacity it held. A paid reservation SHALL become a confirmed registration.

An expired reservation SHALL NOT bar the fencer from the tournament. A fencer whose reservation has expired SHALL be able to register again on the same terms as a fencer who cancelled: the existing registration is reused in place, a fresh validity window opens, and a fresh VS is issued. Capacity SHALL be re-evaluated at that moment like any new registration, so a discipline that filled in the meantime places the returning fencer in the substitute queue rather than seating them. The number of such cycles SHALL NOT be limited.

#### Scenario: Reservation expires unpaid
- **WHEN** the validity window passes with no matched payment
- **THEN** the reservation expires automatically, its discipline capacity is freed, and the fencer is notified

#### Scenario: Payment arrives in time
- **WHEN** a matching payment is ingested before expiry
- **THEN** the reservation becomes a confirmed registration

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

### Requirement: Registration amendment
A fencer SHALL be able to amend their own registration — changing disciplines, extra-service selections, quantities, option values, and the non-billable fields — without cancelling it. The amendment SHALL be validated exactly as an initial registration is, and the total SHALL be recomputed from the pricing rules in force, and the effect on the registration SHALL depend on its state:

- A **reserved** registration SHALL have its selection replaced and its total recomputed, while its VS and its expiry instant remain unchanged. Amending SHALL NOT extend the reservation window, and SHALL NOT issue a new VS. An updated confirmation carrying the new summary, the new amount, and the payment QR SHALL be sent.
- A **paid** registration whose new total exceeds the amount already paid SHALL remain paid, and the difference SHALL be recorded as outstanding against the same VS. Payment instructions for the difference SHALL be sent. The registration SHALL NOT revert to reserved.
- A **paid** registration whose new total is below the amount already paid SHALL record the excess as an overpayment and SHALL enter the tournament's refund tracking for manual settlement, consistent with the cancellation refund policy.

Adding a discipline that is at capacity SHALL place that discipline in the substitute queue rather than rejecting the amendment. Amendment SHALL be refused for a cancelled or expired registration, which returns through re-registration instead. Amendment SHALL be refused once the tournament's amendment window has closed.

#### Scenario: Reserved amendment keeps the VS and the window
- **WHEN** a fencer with an unpaid reservation adds an afterparty ticket
- **THEN** the total is recomputed, and the registration's VS and expiry instant are unchanged from before the amendment

#### Scenario: Reserved amendment reissues the confirmation
- **WHEN** a reserved registration is amended
- **THEN** an updated confirmation email is sent carrying the new item list, the new amount, and a QR code for that amount against the unchanged VS

#### Scenario: Paid amendment upward leaves the registration paid
- **WHEN** a fencer who has paid 1500 amends to a selection totalling 1800
- **THEN** the registration stays paid, 300 is recorded as outstanding against the same VS, and the fencer receives payment instructions for the difference

#### Scenario: Paid amendment downward records an overpayment
- **WHEN** a fencer who has paid 1800 amends to a selection totalling 1500
- **THEN** the excess is recorded against the registration and its refund state becomes pending for manual settlement

#### Scenario: Amendment adding a full discipline
- **WHEN** an amendment adds a discipline that is at capacity
- **THEN** the amendment is accepted and that discipline is recorded as a substitute placement

#### Scenario: Amendment refused after the window closes
- **WHEN** a fencer attempts to amend after the tournament's amendment window has closed
- **THEN** the amendment is rejected with a distinct reason naming the closed window

#### Scenario: Amendment refused on an expired registration
- **WHEN** a fencer attempts to amend a registration that has expired or been cancelled
- **THEN** the amendment is rejected and the fencer is directed to register again

### Requirement: Outstanding balance on a registration
A registration SHALL record the total amount credited to it, expressed in the tournament's primary currency. The amount still owed SHALL be derived from that record against the registration's current total rather than tracked as a second stored figure, so that a recomputed total is immediately reflected in what is owed. A payment recorded in a currency other than the primary one SHALL be recorded at the rate applied when it was matched, so that a later change to the tournament's exchange rate does not restate what a registration has already paid.

A fencer viewing their registration SHALL be shown the outstanding amount when it is non-zero, rather than being left to compute the difference from a total and a payment history.

#### Scenario: Balance follows a recomputed total
- **WHEN** a paid registration's total is raised by an amendment
- **THEN** the outstanding amount equals the new total less what was credited, with no separate figure to reconcile

#### Scenario: Credited amount survives a rate change
- **WHEN** a foreign-currency payment is credited and the tournament's exchange rate is later edited
- **THEN** the amount credited to that registration is unchanged

#### Scenario: Outstanding amount presented to the fencer
- **WHEN** a fencer whose registration carries an outstanding surcharge views it
- **THEN** the outstanding amount is presented with its currency alongside the total
