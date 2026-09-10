## MODIFIED Requirements

### Requirement: Outstanding balance on a registration
A registration's credited amount **per currency** — local and, when the tournament prices in EUR, EUR — SHALL be the sum of the credits recorded against it in that currency, never converted between the two and never summed across them. It SHALL NOT be stored as a figure of its own; a registration holds credits, and what it has been credited is read from them.

The amount still owed in a currency SHALL be derived from that currency's credited sum against the registration's total in that same currency, rather than tracked as a second stored figure, so that a recomputed total is immediately reflected in what is owed. A registration reads as settled when either currency's credited sum covers that currency's own total within tolerance; a registration part-paid in each currency SHALL be flagged for the organizer rather than aggregated.

Because both figures are derived, a credit that ceases to count — reversed, or belonging to a link the organizer withdrew — SHALL be reflected by the next reading with no figure adjusted anywhere.

A fencer viewing their registration SHALL be shown the outstanding amount in each configured currency when it is non-zero, rather than being left to compute the difference from a total and a payment history.

#### Scenario: Balance follows a recomputed total
- **WHEN** a paid registration's total is raised by an amendment
- **THEN** the outstanding amount in that currency equals the new total less what was credited in it, with no separate figure to reconcile

#### Scenario: Balance follows a reversed credit
- **WHEN** a credit against a registration is reversed
- **THEN** the outstanding amount in that currency equals the total less what the remaining credits sum to, with no separate figure to reconcile

#### Scenario: Credited amount survives a rate change
- **WHEN** a EUR payment is credited and the tournament's recorded exchange ratio is later edited
- **THEN** the amount credited to that registration in EUR is unchanged, because no conversion is ever performed and the ratio is not read by matching

#### Scenario: Outstanding amount presented to the fencer
- **WHEN** a fencer whose registration carries an outstanding surcharge views it
- **THEN** the outstanding amount is presented with its currency alongside the total

### Requirement: Registration amendment
A fencer SHALL be able to amend their own registration — changing disciplines, team entries, extra-service selections, quantities, option values, and the non-billable fields — without cancelling it. The amendment SHALL be validated exactly as an initial registration is, and the total SHALL be recomputed from the pricing rules in force, and the effect on the registration SHALL depend on what it has been credited:

- A registration **owing money** SHALL have its selection replaced and its total recomputed, while its VS and its expiry instant remain unchanged. Amending SHALL NOT extend the reservation window, and SHALL NOT issue a new VS. An updated confirmation carrying the new summary, the new amount, and the payment QR SHALL be sent.
- A **settled** registration whose new total exceeds its credits by more than the tolerance SHALL owe the difference against the same VS, and SHALL be read from that moment as owing it: whether a registration is paid for is derived from its credits against its total, and there is no state held over to say otherwise. Payment instructions for the difference SHALL be sent. Because money is being asked for, a **fresh payment window SHALL open**, on the same terms as the window a promotion out of the queue opens — the configured window or the remainder of the time until the tournament, whichever is shorter, and none at all where the tournament's clocks do not run for that registration. Without it the registration would carry the deadline it registered under, which has usually long passed, and the next expiry pass would take a seat from a fencer who had paid.
- A **settled** registration whose new total its credits still cover within tolerance SHALL stay settled, and its expiry instant SHALL be unchanged: nothing was asked for, so no hold is renewed.
- A **settled** registration whose new total is below what it has been credited SHALL record the excess as an overpayment and SHALL enter the tournament's refund tracking for manual settlement, consistent with the cancellation refund policy. It SHALL continue to read as paid, its balance stating the overpayment.

Adding an individual discipline that is at capacity SHALL place that discipline in the substitute queue rather than rejecting the amendment; adding a team to a full team discipline SHALL waitlist that team. Removing a team SHALL remove its roster with it. Amendment SHALL be refused for a cancelled or expired registration, which returns through re-registration instead. Amendment SHALL be refused once the tournament's amendment window has closed.

Editing the members of a team already entered is **not** an amendment: it changes no total, is governed solely by `team-disciplines`, and SHALL remain available after the amendment window has closed.

#### Scenario: Reserved amendment keeps the VS and the window
- **WHEN** a fencer with an unpaid reservation adds an afterparty ticket
- **THEN** the total is recomputed, and the registration's VS and expiry instant are unchanged from before the amendment

#### Scenario: Reserved amendment reissues the confirmation
- **WHEN** a reserved registration is amended
- **THEN** an updated confirmation email is sent carrying the new item list, the new amount, and a QR code for that amount against the unchanged VS

#### Scenario: Paid amendment upward owes the difference and opens a window for it
- **WHEN** a fencer who has paid 1500 amends to a selection totalling 1800
- **THEN** 300 is owed against the same VS, the registration reads as owing it, the fencer receives payment instructions for the difference, and a fresh payment window opens for it

#### Scenario: A surcharge is not expired on the old deadline
- **WHEN** the expiry pass runs against a registration that paid in full and was then amended upward, whose original window has long passed
- **THEN** it is not expired, because the amendment opened a window for the money it newly owes

#### Scenario: An amendment the tolerance absorbs renews no hold
- **WHEN** a settled registration is amended upward by less than the tolerance allows
- **THEN** it stays paid and its expiry instant is unchanged

#### Scenario: Paid amendment downward records an overpayment
- **WHEN** a fencer who has paid 1800 amends to a selection totalling 1500
- **THEN** the excess is recorded against the registration, it still reads as paid, and its refund state becomes pending for manual settlement

#### Scenario: Amendment adding a full discipline
- **WHEN** an amendment adds a discipline that is at capacity
- **THEN** the amendment is accepted and that discipline is recorded as a substitute placement

#### Scenario: Removing a team drops its roster
- **WHEN** an amendment removes a team that carried four members
- **THEN** the team and its members are gone and the total no longer carries that team's fee

#### Scenario: Roster edit is not an amendment
- **WHEN** a fencer changes two members of an entered team after the amendment window has closed
- **THEN** the change is accepted and the registration's total, VS, and payment state are untouched

#### Scenario: Amendment refused after the window closes
- **WHEN** a fencer attempts to amend after the tournament's amendment window has closed
- **THEN** the amendment is rejected with a distinct reason naming the closed window

#### Scenario: Amendment refused on an expired registration
- **WHEN** a fencer attempts to amend a registration that has expired or been cancelled
- **THEN** the amendment is rejected and the fencer is directed to register again
