## MODIFIED Requirements

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

Sections SHALL be derived from item categories, not from a separate list: the tournament's individual disciplines; the tournament's team disciplines; the optional programme (`seminar`, `afterparty`, `other_action`); and optional items (`rental`, `merch`, `other_item`). A section with no rows SHALL be omitted entirely. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

A team-discipline row SHALL NOT be a checkbox. It SHALL state the discipline, its roster bounds, and its per-team price, and SHALL offer an action that adds a team, which requires a team name. Each team the fencer has added SHALL appear as its own line beneath the discipline, showing the team name and the per-team price, and SHALL be removable. Adding a second team to the same discipline SHALL be offered, and each added team SHALL be priced separately rather than as a quantity. The composition deadline, when the tournament sets one, SHALL be stated in the team section together with the statement that rosters may be filled in later.

#### Scenario: Sections rendered from categories
- **WHEN** a tournament offers two disciplines, one seminar, one afterparty, and one merch item and a fencer opens the registration form
- **THEN** the disciplines appear in the tournament section, the seminar and afterparty in the optional programme, the merch item in optional items, and each row shows its price

#### Scenario: Team section rendered
- **WHEN** a tournament offers one individual and one team discipline
- **THEN** the form shows a team section stating the team discipline's roster bounds and per-team price, with an action to add a named team, and the composition deadline when one is set

#### Scenario: Two teams added to one discipline
- **WHEN** a fencer adds two named teams to the same team discipline
- **THEN** both appear as separate lines with the per-team price each, and the running total counts the fee twice

#### Scenario: Team requires a name
- **WHEN** a fencer adds a team without giving it a name
- **THEN** the form refuses the addition and asks for a name

#### Scenario: Empty section omitted
- **WHEN** a tournament offers disciplines and no extra services of any programme category
- **THEN** the optional programme section is not rendered

#### Scenario: No team section without team disciplines
- **WHEN** a tournament offers only individual disciplines
- **THEN** no team section is rendered

#### Scenario: Descriptive lines shown per row
- **WHEN** an extra service carries when, where, and remark text
- **THEN** those lines appear indented under that item's row and nowhere else

#### Scenario: Quantity offered only above limit one
- **WHEN** one item has a per-registration limit of 1 and another a limit of 5
- **THEN** the first renders as a checkbox alone and the second offers a quantity that defaults to 1 on selection

#### Scenario: Instructions and subtitle carried
- **WHEN** the tournament has a subtitle and registration instructions
- **THEN** both appear above the first section, and a tournament with neither renders the form correctly without them

### Requirement: Capacity and substitutes
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When an individual discipline is full, further registrations SHALL join a substitute queue in registration order. When a team discipline is full, further teams SHALL join a team waitlist in entry order, counted in teams rather than fencers, as fixed by `team-disciplines`. When a spot frees through expiry or cancellation, the organizer SHALL be able to admit substitutes from the individual queue; admitting a waitlisted team is not offered.

#### Scenario: Discipline full
- **WHEN** a fencer registers for a discipline at capacity
- **THEN** the registration enters the substitute queue and the fencer is informed of their position

#### Scenario: Team discipline full
- **WHEN** a fencer enters a team into a team discipline holding teams to capacity
- **THEN** the team is waitlisted in entry order, its fee is not charged, and the fencer is informed

### Requirement: Registration amendment
A fencer SHALL be able to amend their own registration — changing disciplines, team entries, extra-service selections, quantities, option values, and the non-billable fields — without cancelling it. The amendment SHALL be validated exactly as an initial registration is, and the total SHALL be recomputed from the pricing rules in force, and the effect on the registration SHALL depend on its state:

- A **reserved** registration SHALL have its selection replaced and its total recomputed, while its VS and its expiry instant remain unchanged. Amending SHALL NOT extend the reservation window, and SHALL NOT issue a new VS. An updated confirmation carrying the new summary, the new amount, and the payment QR SHALL be sent.
- A **paid** registration whose new total exceeds the amount already paid SHALL remain paid, and the difference SHALL be recorded as outstanding against the same VS. Payment instructions for the difference SHALL be sent. The registration SHALL NOT revert to reserved.
- A **paid** registration whose new total is below the amount already paid SHALL record the excess as an overpayment and SHALL enter the tournament's refund tracking for manual settlement, consistent with the cancellation refund policy.

Adding an individual discipline that is at capacity SHALL place that discipline in the substitute queue rather than rejecting the amendment; adding a team to a full team discipline SHALL waitlist that team. Removing a team SHALL remove its roster with it. Amendment SHALL be refused for a cancelled or expired registration, which returns through re-registration instead. Amendment SHALL be refused once the tournament's amendment window has closed.

Editing the members of a team already entered is **not** an amendment: it changes no total, is governed solely by `team-disciplines`, and SHALL remain available after the amendment window has closed.

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

### Requirement: Price preview
The system SHALL compute the total price for a hypothetical selection (individual disciplines, team entries, and extra services with quantities and option values) for a tournament without creating a registration, using the same pricing engine — itemized pricing with discounts, or the legacy fee fields for legacy tournaments — that applies at registration time, evaluated as of the current date. The preview SHALL return a total per configured currency, each summed from that currency's prices by the same computation the registration will use.

A previewed team entry SHALL contribute its discipline's per-team price once, regardless of how many members the hypothetical roster names, and SHALL be identified by its team discipline alone: a team's name and roster are not pricing inputs and SHALL NOT be required by the preview.

The preview SHALL additionally return a discount breakdown: one entry for every discount the tournament configures, in configured order, each carrying the discount's name, its effect, and whether that discount applied to the previewed selection. An entry that applied SHALL also carry the amount the discount deducted, per configured currency for a fixed effect and as a single figure for a currency-neutral percentage effect. Applicability SHALL be reported once for the whole entry, since a discount's condition is evaluated from discipline counts and dates and never from money, and therefore cannot differ between currencies. The breakdown SHALL report the discounts the priced computation actually applied and SHALL NOT be evaluated separately from it. A tournament with no configured discounts SHALL return an empty breakdown.

#### Scenario: Preview matches registration
- **WHEN** a price preview is requested for a selection and the same selection is then submitted as a registration at the same date
- **THEN** the previewed totals equal the registration's computed totals in every configured currency

#### Scenario: Team previewed without a roster
- **WHEN** a preview is requested for one team entry with no team name and no members
- **THEN** the preview returns the total including that discipline's per-team price once

#### Scenario: Two teams previewed
- **WHEN** a preview is requested for two team entries in the same team discipline
- **THEN** the per-team price is counted twice
