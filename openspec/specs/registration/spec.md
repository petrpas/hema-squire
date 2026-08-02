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

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

Sections SHALL be derived from item categories, not from a separate list: the tournament's disciplines; the optional programme (`seminar`, `afterparty`, `other_action`); and optional items (`rental`, `merch`, `other_item`). A section with no rows SHALL be omitted entirely. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

The form SHALL set the registration instructions and the total apart from the checklist by a vertical space visibly larger than the space between sections, so neither reads as a continuation of the block above it. The total SHALL be aligned to the trailing edge of the price column it sums, so it reads as that column's sum rather than as a line of prose.

Below the total the form SHALL offer exactly one non-billable field: a free-text note to the organizer, under its own section heading. It SHALL NOT offer an after-sparring checkbox or an accommodation field.

#### Scenario: Sections rendered from categories
- **WHEN** a tournament offers two disciplines, one seminar, one afterparty, and one merch item and a fencer opens the registration form
- **THEN** the disciplines appear in the tournament section, the seminar and afterparty in the optional programme, the merch item in optional items, and each row shows its price

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

Each QR code SHALL encode the stored total of its own currency, with the SPAYD currency field taken from that currency. No amount in either QR code SHALL be produced by conversion.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

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
Discipline capacity SHALL be consumed by confirmed registrations and by reservations within their validity window. When a discipline is full, further registrations SHALL join a substitute queue in registration order. When a spot frees through expiry or cancellation, the organizer SHALL be able to admit substitutes from the queue.

#### Scenario: Discipline full
- **WHEN** a fencer registers for a discipline at capacity
- **THEN** the registration enters the substitute queue and the fencer is informed of their position

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
A fencer SHALL be able to cancel a registration. A cancellation before the tournament's refundable-until date SHALL be marked refundable; after that date the fee is not refundable and the freed spot is offered to substitutes. Refund execution is manual; the system SHALL track refund state on the registration.

#### Scenario: Cancellation after the refundable date
- **WHEN** a paid fencer cancels after the refundable-until date
- **THEN** the registration is cancelled without refund and the spot is offered to the substitute queue

### Requirement: Price preview
The system SHALL compute the total price for a hypothetical selection (disciplines and extra services with quantities and option values) for a tournament without creating a registration, using the same pricing engine — itemized pricing with discounts, or the legacy fee fields for legacy tournaments — that applies at registration time, evaluated as of the current date. The preview SHALL return a total per configured currency, each summed from that currency's prices by the same computation the registration will use.

The preview SHALL additionally return a discount breakdown: one entry for every discount the tournament configures, in configured order, each carrying the discount's name, its effect, and whether that discount applied to the previewed selection. An entry that applied SHALL also carry the amount the discount deducted, per configured currency for a fixed effect and as a single figure for a currency-neutral percentage effect. Applicability SHALL be reported once for the whole entry, since a discount's condition is evaluated from discipline counts and dates and never from money, and therefore cannot differ between currencies. The breakdown SHALL report the discounts the priced computation actually applied and SHALL NOT be evaluated separately from it. A tournament with no configured discounts SHALL return an empty breakdown.

#### Scenario: Preview matches registration
- **WHEN** a price preview is requested for a selection and the same selection is then submitted as a registration at the same date
- **THEN** the previewed totals equal the registration's computed totals in every configured currency

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
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, bank account (IBAN), variable symbol, payment message, reservation expiry, and the SPAYD QR code — plus the EUR total and a EUR-denominated QR code when the tournament prices in EUR as a second currency. Every amount SHALL be a stored total and every QR code SHALL encode the stored total of its own currency. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount with its currency, IBAN, VS, message, expiry, and QR code are returned

#### Scenario: EUR pair present only when applicable
- **WHEN** payment instructions are requested on a CZK + EUR tournament and again on a CZK-only one
- **THEN** the first response carries the EUR total and EUR QR and the second omits both fields entirely

#### Scenario: Instructions match the original email after a configuration change
- **WHEN** prices or the recorded ratio change and the fencer then retrieves their payment instructions
- **THEN** the amounts and QR codes returned are the ones from their confirmation email

#### Scenario: Other accounts denied
- **WHEN** a different account requests those payment instructions
- **THEN** the request is rejected

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published, non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set, and its local currency — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Subtitle and logo carried when set
- **WHEN** a listed tournament has a subtitle and a logo
- **THEN** its list entry carries the subtitle and a reference to its logo, and entries without them omit those fields

#### Scenario: Currency carried
- **WHEN** a fencer requests the list
- **THEN** each entry carries the tournament's local currency so amounts render without a hardcoded unit

#### Scenario: Unpublished excluded
- **WHEN** a tournament has not been published, or it is cancelled
- **THEN** it is absent from the fencer-facing list

#### Scenario: Setup-complete draft still excluded
- **WHEN** a tournament's mandatory setup is complete but nobody has published it
- **THEN** it is absent from the fencer-facing list
