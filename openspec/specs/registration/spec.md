# registration Specification

## Purpose
Handle in-app registration: reservations with per-reservation payment windows, QR payment confirmation emails, capacity and substitute queues, the public participant list, and cancellation policy.

## Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit and an option value where the item declares an option label, plus one non-billable field: a free-text note to the organizer. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before and SHALL be presented as rows in the same checklist. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items with their quantities and option values. Registration is exposed through the API and through the fencer-facing tournament detail page (fencer-home capability).

The registration API SHALL continue to accept and store the after-sparring flag and the accommodation note, because the table-import path still parses both from legacy sources; a registration created in-app SHALL simply carry neither, and their absence SHALL NOT change any total, export, or email.

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

#### Scenario: Note retained
- **WHEN** a fencer writes a note to the organizer and registers
- **THEN** it is stored on the registration, appears wherever the registration is presented to the organizer, and does not change the computed total

#### Scenario: In-app registration carries no after-sparring or accommodation
- **WHEN** a fencer completes the in-app form
- **THEN** the created registration has no after-sparring flag set and no accommodation note, and every total, export and email is exactly what it would have been with those fields empty

#### Scenario: Imported registration keeps both
- **WHEN** a registration is created through the table-import path from a source row declaring after-sparring and an accommodation note
- **THEN** both are stored on the registration as before

### Requirement: The form offers only what the tournament configures
Every priced row on the registration form SHALL come from an item the tournament configures — a discipline or an extra service. The form SHALL NOT synthesize rows from the tournament's legacy fixed fees: no afterparty row and no weapon-rental row SHALL be rendered from `afterparty_fee` or `weapon_rental_fee`, whether or not the tournament configures any extra services. A tournament that configures none SHALL therefore show its disciplines and nothing else purchasable.

The legacy fee values SHALL remain stored, editable in Setup, and honored in existing registrations, exports, and imports that already carry them. This requirement governs what the form offers, not what the system remembers.

#### Scenario: New tournament offers no invented rows
- **WHEN** a fencer opens the registration form of a tournament that has disciplines and no extra services
- **THEN** the form shows the discipline rows, the note field and the total, and no afterparty row and no weapon-rental row

#### Scenario: Configured items are the only priced rows
- **WHEN** a tournament configures a seminar and a t-shirt as extra services while its legacy afterparty fee is still set to a non-zero amount
- **THEN** the form offers the seminar and the t-shirt and no row derived from the legacy fee

#### Scenario: Legacy values survive the form
- **WHEN** a registration recorded before this change carries a weapon rental and an afterparty
- **THEN** its stored selection, its total, and its exports are unchanged, and the amounts still appear on that registration wherever it is presented

#### Scenario: Preview matches the fencer's form
- **WHEN** an organizer opens the registration-form preview in the console for a tournament with no extra services
- **THEN** the preview shows the same rows the fencer would see, with no afterparty or weapon-rental row

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

A discipline row SHALL be labelled by the discipline's name alone. A discipline's slug SHALL NOT appear on the registration form or anywhere else a fencer reads, as fixed by `discipline-identity`; it is the identifier the form submits, never text the form shows. Where a tournament offers several disciplines classified alike, their names are what distinguish them, and the form SHALL present those names as the organizer wrote them without prefixing, suffixing, or otherwise decorating them to mark the distinction.

Sections SHALL be derived from item categories, not from a separate list: the tournament's individual disciplines; the tournament's team disciplines; the optional programme (`seminar`, `afterparty`, `other_action`); and optional items (`rental`, `merch`, `other_item`). A section with no rows SHALL be omitted entirely. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

A team-discipline row SHALL NOT be a checkbox. It SHALL state the discipline, its roster bounds, and its per-team price, and SHALL offer an action that adds a team, which requires a team name. Each team the fencer has added SHALL appear as its own line beneath the discipline, showing the team name and the per-team price, and SHALL be removable. Adding a second team to the same discipline SHALL be offered, and each added team SHALL be priced separately rather than as a quantity. The composition deadline, when the tournament sets one, SHALL be stated in the team section together with the statement that rosters may be filled in later.

The form SHALL set the registration instructions and the total apart from the checklist by a vertical space visibly larger than the space between sections, so neither reads as a continuation of the block above it. The total SHALL be aligned to the trailing edge of the price column it sums, so it reads as that column's sum rather than as a line of prose.

Below the total the form SHALL offer exactly one non-billable field: a free-text note to the organizer, under its own section heading. It SHALL NOT offer an after-sparring checkbox or an accommodation field.

#### Scenario: Sections rendered from categories
- **WHEN** a tournament offers two disciplines, one seminar, one afterparty, and one merch item and a fencer opens the registration form
- **THEN** the disciplines appear in the tournament section, the seminar and afterparty in the optional programme, the merch item in optional items, and each row shows its price

#### Scenario: Discipline rows carry names, not slugs
- **WHEN** a fencer opens the registration form of a tournament whose disciplines have slugs
- **THEN** every discipline row reads as its name alone, and no slug appears anywhere on the form

#### Scenario: Two tiers distinguished by name
- **WHEN** a tournament offers two longsword disciplines named for its top and open brackets and a fencer opens the registration form
- **THEN** two rows appear, each labelled by its own name, each separately selectable and separately priced

#### Scenario: Team section rendered
- **WHEN** a tournament offers one individual and one team discipline
- **THEN** the form shows a team section stating the team discipline's roster bounds and per-team price, with an action to add a named team, and the composition deadline when one is set

#### Scenario: Individual and team in one weapon both offered
- **WHEN** a tournament offers both an individual and a team longsword discipline
- **THEN** the individual one appears in the disciplines section and the team one in the team section, each under its own name

#### Scenario: Two teams added to one discipline
- **WHEN** a fencer adds two named teams to the same team discipline
- **THEN** both appear as separate lines with the per-team price each, and the running total counts the fee twice

#### Scenario: Team requires a name
- **WHEN** a fencer adds a team without giving it a name
- **THEN** the form refuses the addition and asks for a name

#### Scenario: No team section without team disciplines
- **WHEN** a tournament offers only individual disciplines
- **THEN** no team section is rendered

#### Scenario: Empty section omitted
- **WHEN** a tournament offers disciplines and no extra services of any programme category
- **THEN** the optional programme section is not rendered

#### Scenario: Descriptive lines shown per row
- **WHEN** an extra service carries when, where, and remark text
- **THEN** those lines appear indented under that item's row and nowhere else

#### Scenario: Quantity offered only above limit one
- **WHEN** one item has a per-registration limit of 1 and another a limit of 5
- **THEN** the first renders as a checkbox alone and the second offers a quantity that defaults to 1 on selection

#### Scenario: Instructions and subtitle carried
- **WHEN** the tournament has a subtitle and registration instructions
- **THEN** both appear above the first section, and a tournament with neither renders the form correctly without them

#### Scenario: Instructions and total set apart
- **WHEN** a fencer opens a form with registration instructions and at least one section
- **THEN** the gap above the instructions and the gap above the total are each visibly larger than the gap between two consecutive sections

#### Scenario: Total aligned over the price column
- **WHEN** a fencer reads the total on a form whose rows show prices in a shared right-hand column
- **THEN** the total's amount is aligned to that column's trailing edge

#### Scenario: Only the note remains below the total
- **WHEN** a fencer reaches the bottom of the form
- **THEN** they find one free-text note field under its own heading, and no after-sparring checkbox and no accommodation field anywhere on the form

### Requirement: Substitute registration chosen in place
When a discipline has no free place, its row SHALL state that it is full, with the taken and capacity numbers, and that selecting it registers the fencer as a substitute. Selecting such a row SHALL submit the registration directly as accepting substitute placement, without any intermediate confirmation step. If a discipline fills between form load and submission, the rejection SHALL be reported inline on the form, naming the affected disciplines, so the fencer can re-confirm their selection.

#### Scenario: Full discipline stated on its row
- **WHEN** a discipline has 25 registrations against a capacity of 20
- **THEN** its row states it is full at 25/20 and that selection means substitute placement

#### Scenario: Substitute registration submitted without a dialog
- **WHEN** a fencer selects a full discipline and submits
- **THEN** the registration is created with that discipline in the substitute queue and no confirmation dialog is shown

#### Scenario: Discipline fills during the session
- **WHEN** a discipline shown as open has filled by the time the fencer submits
- **THEN** the form reports inline which disciplines are now full and the fencer can re-confirm the selection

### Requirement: Extra-service option answered per selection
When a selected extra service declares an option label, the registration SHALL carry exactly one option value for that selection. The value MUST be one of the item's configured choices when choices exist, and MUST be non-empty trimmed text within the length limit when they do not. Selecting an item that declares an option without supplying a value SHALL be rejected with a validation error. Supplying a value for an item that declares no option SHALL be rejected. The stored option value SHALL appear in the registration summary, the confirmation email, and the exports beside its item.

Option validation SHALL apply to registration submission only. The price preview SHALL NOT require an option value, since options never affect price and refusing to price an unanswered row would misreport the running total while the form is still being filled in.

#### Scenario: Preset choice selected
- **WHEN** a fencer selects a t-shirt with quantity 2 and size M
- **THEN** the registration records two t-shirts with option value M, and the summary, email, and export show the size beside the item

#### Scenario: Missing required option rejected
- **WHEN** a fencer selects an item that declares an option label and submits without a value
- **THEN** the registration is rejected with a validation error naming that item

#### Scenario: Value outside the configured choices rejected
- **WHEN** a submitted option value is not among the item's configured choices
- **THEN** the registration is rejected with a validation error

#### Scenario: Option supplied for an option-less item rejected
- **WHEN** a submitted selection carries an option value for an item that declares no option label
- **THEN** the registration is rejected with a validation error

#### Scenario: Preview prices an unanswered option
- **WHEN** a price preview is requested for an item that declares an option label with no value supplied
- **THEN** the preview returns the full total for that selection instead of an error

#### Scenario: Pre-existing selections tolerate a newly added option
- **WHEN** an organizer adds an option label to an item that already has selections recorded without one
- **THEN** those selections remain valid and render with no option value

### Requirement: Amounts presented in the tournament's currency
Every amount presented to a fencer — row prices, the running total, the registration total, and payment instructions — SHALL be rendered from a stored price or a stored total together with the currency it is denominated in. When the tournament prices in EUR as a second currency, each presented figure SHALL additionally show the EUR figure, taken from the EUR price or the EUR total. No presented amount SHALL be produced by converting another amount at an exchange ratio. No EUR figure SHALL be presented when the tournament does not price in EUR, and no second figure SHALL be presented when the local currency is already EUR. No user-facing string SHALL contain a hardcoded currency unit.

A registration SHALL store a total per configured currency, computed when the registration is created. A subsequent change to any configured price or to the recorded exchange ratio SHALL NOT alter a stored total.

#### Scenario: Both figures shown from stored prices
- **WHEN** a CZK + EUR tournament presents a registration totalling 1500 Kč and 60 €
- **THEN** both figures are presented from the stored totals and neither is computed from the other

#### Scenario: No EUR figure in single-currency mode
- **WHEN** a tournament prices in CZK only
- **THEN** every amount is presented in CZK only

#### Scenario: EUR-priced tournament shows one figure
- **WHEN** a tournament's local currency is EUR
- **THEN** amounts are presented in EUR once, with no second currency figure

#### Scenario: Ratio change moves nothing
- **WHEN** the organizer changes the recorded exchange ratio after a reservation exists
- **THEN** that reservation's presented totals in both currencies are unchanged

#### Scenario: Price change does not move an existing registration
- **WHEN** the organizer raises a discipline price after a reservation exists
- **THEN** that reservation's stored totals are unchanged in both currencies

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

### Requirement: Outstanding balance on a registration
A registration SHALL record the amount credited to it **per currency** — local and, when the tournament prices in EUR, EUR — never converted between them and never summed across them. The amount still owed in a currency SHALL be derived from that currency's own credited amount against the registration's total in that same currency, rather than tracked as a second stored figure, so that a recomputed total is immediately reflected in what is owed. A registration is settled when either currency's credited amount covers that currency's own total within tolerance; a registration part-paid in each currency SHALL be flagged for the organizer rather than aggregated.

A fencer viewing their registration SHALL be shown the outstanding amount in each configured currency when it is non-zero, rather than being left to compute the difference from a total and a payment history.

#### Scenario: Balance follows a recomputed total
- **WHEN** a paid registration's total is raised by an amendment
- **THEN** the outstanding amount in that currency equals the new total less what was credited in it, with no separate figure to reconcile

#### Scenario: Credited amount survives a rate change
- **WHEN** a EUR payment is credited and the tournament's recorded exchange ratio is later edited
- **THEN** the amount credited to that registration in EUR is unchanged, because no conversion is ever performed and the ratio is not read by matching

#### Scenario: Outstanding amount presented to the fencer
- **WHEN** a fencer whose registration carries an outstanding surcharge views it
- **THEN** the outstanding amount is presented with its currency alongside the total

### Requirement: Confirmation email with QR payment
On registration the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

Each discipline entered SHALL be summarized by its name alone. The email SHALL NOT carry discipline slugs, which are not fencer-facing text (`discipline-identity`); where a tournament offers several disciplines classified alike, the name is what tells the fencer which one they entered.

Each QR code SHALL encode the stored total of its own currency, with the SPAYD currency field taken from that currency. No amount in either QR code SHALL be produced by conversion.

The account SHALL be stated in the same form as the in-app instructions: a Czech account as its domestic form together with its IBAN, any other account as its IBAN alone. The two surfaces SHALL NOT differ in how they present one account, because a fencer comparing the email against the page must not have to work out whether they are looking at the same thing. The QR code SHALL continue to encode the IBAN whatever form the email states, since the payment descriptor admits no other.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

#### Scenario: Czech account stated in both forms
- **WHEN** a confirmation email goes out for a tournament whose account is Czech
- **THEN** it states the domestic form and the IBAN, while the QR code encodes the IBAN

#### Scenario: Email and page agree
- **WHEN** a fencer compares their confirmation email against the in-app payment instructions
- **THEN** the account is presented identically in both

#### Scenario: Disciplines summarized by name
- **WHEN** a fencer registers for two disciplines
- **THEN** the email lists each by its name alone, with no slug alongside it

#### Scenario: Tiers legible in the summary
- **WHEN** a fencer registers for one of two longsword disciplines that differ only by name
- **THEN** the email names the one they entered, and it is distinguishable from the one they did not

#### Scenario: EUR QR carries the stored EUR total
- **WHEN** a CZK + EUR tournament confirms a reservation totalling 1500 Kč and 60 €
- **THEN** the email carries a CZK QR for 1500 and a EUR QR for 60, each with its own currency in the SPAYD currency field

#### Scenario: No EUR block in single-currency mode
- **WHEN** a tournament prices in one currency
- **THEN** the email carries exactly one amount and one QR code

#### Scenario: Emailed amounts stable against configuration changes
- **WHEN** the organizer changes prices or the recorded ratio after a confirmation email was sent
- **THEN** the reminder and the in-app instructions for that reservation state the same amounts and carry the same QR codes as the original confirmation

### Requirement: Capacity and substitutes
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When an individual discipline is full, further registrations SHALL join a substitute queue in registration order. When a team discipline is full, further teams SHALL join a team waitlist in entry order, counted in teams rather than fencers, as fixed by `team-disciplines`. When a spot frees through expiry or cancellation, the organizer SHALL be able to admit substitutes from the individual queue; admitting a waitlisted team is not offered.

#### Scenario: Discipline full
- **WHEN** a fencer registers for a discipline at capacity
- **THEN** the registration enters the substitute queue and the fencer is informed of their position

#### Scenario: Team discipline full
- **WHEN** a fencer enters a team into a team discipline holding teams to capacity
- **THEN** the team is waitlisted in entry order, its fee is not charged, and the fencer is informed

### Requirement: Public participant list
The public participant list SHALL show confirmed (paid) registrations only. Unpaid reservations SHALL be either hidden or shown greyed as unconfirmed, according to the tournament setting; the default for a new tournament is greyed.

#### Scenario: Unpaid fencer not presented as confirmed
- **WHEN** a visitor views the public participant list
- **THEN** unpaid reservations never appear as confirmed participants

### Requirement: Registration availability
The system SHALL accept a registration only when the tournament has been published and the current date is within the registration window: on or after the registration-opens date when set, and on or before the registration-closes date when set (otherwise up to the tournament date). When registration is unavailable, the rejection SHALL carry a distinct reason — not yet published, not yet open, or closed — so clients can present it (with the opening date where applicable). The gate SHALL NOT re-check mandatory setup completeness: publication already guarantees it, and a published tournament cannot be edited into incompleteness.

#### Scenario: Not published
- **WHEN** a fencer attempts to register for a tournament that has not been published
- **THEN** the registration is rejected with the not-yet-published reason, whether or not its mandatory setup is complete

#### Scenario: After close
- **WHEN** a fencer attempts to register after the registration-closes date
- **THEN** the registration is rejected with the closed reason

### Requirement: Cancellation and refund policy
A fencer SHALL be able to cancel a registration. The freed spot SHALL be offered to substitutes, whatever the cancellation's refund standing.

Refund standing SHALL be settled only where there is money to return, that is on a registration that was paid at the moment it was cancelled. Such a cancellation on or before the tournament's refundable-until date SHALL be marked refundable and SHALL enter refund tracking as pending; after that date, or on a tournament carrying no such date, it SHALL be marked not refundable. A registration cancelled while unpaid SHALL carry no refund standing at all rather than being marked not refundable. Refund execution is manual; the system SHALL track refund state on the registration.

Because the refundable-until date is no longer offered to the organizer (see `tournament-admin`), a tournament configured after that field was withdrawn carries none, and every paid cancellation on it is therefore marked not refundable. That marking SHALL be read as *the system makes no refund commitment*, not as a refusal: refunds on such a tournament are settled between the fencer and the organizer outside the system. Nothing in the fencer-facing cancellation flow SHALL present the marking as either a promise of a refund or a denial of one, as fixed by `fencer-home`. A tournament that already carries a stored refundable-until date SHALL continue to be evaluated against it, so the rule can be offered again without a migration.

#### Scenario: Cancellation after the refundable date
- **WHEN** a paid fencer cancels after the refundable-until date
- **THEN** the registration is cancelled without refund and the spot is offered to the substitute queue

#### Scenario: Cancellation on a tournament with no refundable date
- **WHEN** a paid fencer cancels a registration on a tournament carrying no refundable-until date
- **THEN** the registration is cancelled, marked not refundable, and the spot is offered to the substitute queue, and the fencer is told only that any refund is arranged with the organizer

#### Scenario: Stored refundable date still honoured
- **WHEN** a paid fencer cancels before a refundable-until date already stored on the tournament
- **THEN** the cancellation is marked refundable and enters refund tracking as pending, even though the date can no longer be set

#### Scenario: Unpaid cancellation carries no refund standing
- **WHEN** a fencer cancels a registration that has not been paid
- **THEN** the registration is cancelled with no refund standing recorded, and it is not marked not-refundable

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

#### Scenario: Preview carries both totals
- **WHEN** a price preview is requested on a CZK + EUR tournament
- **THEN** the response carries the CZK total and the EUR total, each summed from its own prices

#### Scenario: Preview in single-currency mode
- **WHEN** a price preview is requested on a tournament pricing in one currency
- **THEN** the response carries exactly one total

#### Scenario: Breakdown reports applied and unapplied discounts
- **WHEN** a tournament configures a discount for exactly 2 disciplines and one for exactly 3, and a preview is requested for a 2-discipline selection
- **THEN** the breakdown carries both discounts, the 2-discipline one marked as applied and the 3-discipline one marked as not applied

#### Scenario: Applied fixed discount reports its deduction per currency
- **WHEN** a preview on a CZK + EUR tournament activates a fixed discount of 500 Kč / 20 € that is fully absorbed by its scoped subtotal
- **THEN** its breakdown entry reports 500 deducted in CZK and 20 deducted in EUR, each read from that currency's own computation

#### Scenario: Applied percentage discount reports one figure
- **WHEN** a preview activates a −10 % discount
- **THEN** its breakdown entry reports the percentage effect without a second, EUR-denominated value

#### Scenario: Deduction floored at the scoped subtotal is reported as taken
- **WHEN** a fixed discount of 500 activates against a scoped subtotal of 300
- **THEN** the entry is marked as applied and reports 300 deducted, matching what the total reflects

#### Scenario: Early-bird applicability judged by the server date
- **WHEN** a preview is requested on a tournament whose early-bird date has passed
- **THEN** the early-bird entry is marked as not applied, and the total carries no early-bird reduction

#### Scenario: Tournament without discounts
- **WHEN** a price preview is requested on a legacy tournament, or on any tournament with no configured discounts
- **THEN** the response carries its totals and an empty discount breakdown

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, the bank account, variable symbol, payment message, reservation expiry, and the SPAYD QR code — plus the EUR total and a EUR-denominated QR code when the tournament prices in EUR as a second currency. Every amount SHALL be a stored total and every QR code SHALL encode the stored total of its own currency. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

The account SHALL be presented in the form the payer can use. Where the tournament's account is Czech, both its domestic form and its IBAN SHALL be presented, because a Czech payer enters the domestic form in their banking application and a foreign payer needs the IBAN. Where it is not Czech, the IBAN alone SHALL be presented and no domestic form SHALL be invented. The domestic form SHALL be derived from the stored account rather than stored a second time, and SHALL be carried as its own field rather than requiring the presenting surface to take an IBAN apart. No label SHALL name the account as an IBAN where a domestic form may be shown beside it.

Whether anything is owed SHALL be decided in one place, by the system that holds the registration, and SHALL NOT be decided a second time by the surface that displays the answer. A registration owes nothing exactly when every individual entry it carries is queued as a substitute **and** every team it carries is waitlisted; a registration carrying nothing on one of those axes SHALL be judged on the other alone, so that a team-only registration is judged on its teams. No presentation SHALL predict this answer before requesting the instructions.

A fencer holding a reservation SHALL be told either how to pay or why they cannot yet. Where instructions cannot be produced, the reason SHALL be shown in terms the fencer can act on, and the absence of instructions SHALL NOT be presented as an empty space. Three reasons SHALL be distinguished: that nothing is owed because every place requested is queued; that the tournament has recorded no bank account to pay into; and that the reservation is no longer awaiting payment. A reason the fencer cannot resolve SHALL say who will resolve it rather than instructing the fencer to act.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount with its currency, the account, VS, message, expiry, and QR code are returned

#### Scenario: Czech account presented in both forms
- **WHEN** payment instructions are retrieved for a tournament whose account is Czech
- **THEN** both the domestic form and the IBAN are returned, each as its own field

#### Scenario: Foreign account presented as IBAN alone
- **WHEN** payment instructions are retrieved for a tournament banking outside Czechia
- **THEN** the IBAN is returned and no domestic form is

#### Scenario: Domestic form is derived, not stored
- **WHEN** the organizer saves the account as an IBAN and a fencer then retrieves payment instructions
- **THEN** the domestic form is present just as it would be had the organizer typed it, without having been stored

#### Scenario: EUR pair present only when applicable
- **WHEN** payment instructions are requested on a CZK + EUR tournament and again on a CZK-only one
- **THEN** the first response carries the EUR total and EUR QR and the second omits both fields entirely

#### Scenario: Instructions match the original email after a configuration change
- **WHEN** prices or the recorded ratio change and the fencer then retrieves their payment instructions
- **THEN** the amounts and QR codes returned are the ones from their confirmation email

#### Scenario: Other accounts denied
- **WHEN** a different account requests those payment instructions
- **THEN** the request is rejected

#### Scenario: Team-only registration is judged on its teams
- **WHEN** a fencer holds a reservation carrying one team and no individual entries, and that team is not waitlisted
- **THEN** payment instructions are produced for it, and it is not treated as owing nothing

#### Scenario: Team-only waitlisted registration owes nothing
- **WHEN** a fencer holds a reservation carrying only teams and every one of them is waitlisted
- **THEN** the fencer is told nothing is owed yet, and no payment instructions and no empty space are shown

#### Scenario: Queued entries do not hide an owed team
- **WHEN** a reservation's individual entries are all queued as substitutes while one of its teams is not waitlisted
- **THEN** payment instructions are shown for the amount owed, and the fencer is not told that everything is queued

#### Scenario: Missing bank account explained, not blank
- **WHEN** a fencer holds a reservation on a tournament that has recorded no bank account
- **THEN** the fencer is told that payment details are not available and that the organizer will supply them, rather than being shown nothing

#### Scenario: Reservation settled while its instructions were open
- **WHEN** the fencer's reservation is matched to a payment between the page being opened and the instructions being requested
- **THEN** the fencer is told the reservation is no longer awaiting payment rather than being shown an empty panel

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published, non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set, and its local currency — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

The list SHALL be served in three scopes, carrying the same entry shape so one presentation serves all three:

- **upcoming** — tournaments dated today or later, ordered by date ascending;
- **held** — tournaments dated before today, ordered by date descending, listed for every requesting account whether or not it was involved with them;
- **own** — tournaments in either direction of today where the requesting account holds or held a registration in any state, including cancelled, or is the tournament's owner or a member of its console team, ordered by date descending.

Every entry SHALL carry the requesting account's own relationship to that tournament: its registration state when it holds or held one, and an organizer mark when the account is its owner or console team member. An entry SHALL be able to carry both facts, and a consumer SHALL be able to tell a registration from an organizer relationship without a second request.

A per-discipline count SHALL be stated in the unit its discipline is entered in: fencers for an individual discipline, teams for a team discipline. No scope SHALL apply the fencer-counting rule to a team discipline.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Held scope is public
- **WHEN** an account with no registration and no organizer role requests the held scope
- **THEN** every published, non-cancelled tournament dated before today is returned, each with no registration state and no organizer mark for that account

#### Scenario: Own scope spans both directions
- **WHEN** an account holding a reservation for a tournament next month and a paid registration for one last year requests the own scope
- **THEN** both are returned, newest first, each carrying its registration state

#### Scenario: Organizer relationship reported
- **WHEN** an account that organizes a tournament but never registered for it requests the own scope
- **THEN** that tournament is returned carrying the organizer mark and no registration state

#### Scenario: Own scope excludes the unrelated
- **WHEN** a published tournament exists that the account neither registered for nor organizes
- **THEN** it is absent from the own scope while remaining present in the scope its date puts it in

#### Scenario: Team discipline counted in teams
- **WHEN** any scope lists a tournament offering a team discipline
- **THEN** that discipline's count states entered teams against its capacity in teams, and the request succeeds

#### Scenario: Subtitle and logo carried when set
- **WHEN** a listed tournament has a subtitle and a logo
- **THEN** its list entry carries the subtitle and a reference to its logo, and entries without them omit those fields

#### Scenario: Currency carried
- **WHEN** a fencer requests the list
- **THEN** each entry carries the tournament's local currency so amounts render without a hardcoded unit

#### Scenario: Unpublished excluded
- **WHEN** a tournament has not been published, or it is cancelled
- **THEN** it is absent from the fencer-facing list, in every scope

#### Scenario: Setup-complete draft still excluded
- **WHEN** a tournament's mandatory setup is complete but nobody has published it
- **THEN** it is absent from the fencer-facing list
