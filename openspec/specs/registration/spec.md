# registration Specification

## Purpose
Handle in-app registration: reservations with per-reservation payment windows, QR payment confirmation emails, capacity and substitute queues, the public participant list, and cancellation policy.

## Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit and an option value where the item declares an option label, plus the non-billable fields: after-sparring, accommodation note, and free-text remarks. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before and SHALL be presented as rows in the same checklist. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items with their quantities and option values. Registration is exposed through the API and through the fencer-facing tournament detail page (fencer-home capability).

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

#### Scenario: Non-billable fields retained
- **WHEN** a fencer fills after-sparring, an accommodation note, and remarks
- **THEN** all three are stored on the registration and none of them changes the computed total

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

Sections SHALL be derived from item categories, not from a separate list: the tournament's disciplines; the optional programme (`seminar`, `afterparty`, `other_action`); and optional items (`rental`, `merch`, `other_item`). A section with no rows SHALL be omitted entirely. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

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
Every amount presented to a fencer — row prices, the running total, the registration total, and payment instructions — SHALL be rendered from the amount together with the tournament's primary currency. When the tournament has EUR payments enabled and its primary currency is not EUR, each presented total SHALL additionally show the EUR equivalent, converted at the tournament's stored rate and rounded half-up to two decimals. No EUR figure SHALL be presented when EUR payments are disabled or when the primary currency is already EUR. No user-facing string SHALL contain a hardcoded currency unit.

#### Scenario: EUR equivalent shown alongside the primary total
- **WHEN** a CZK tournament with EUR payments enabled at 25.5 presents a total of 1750
- **THEN** the total is presented as 1750 CZK with the EUR equivalent 68.63 beside it

#### Scenario: No EUR figure without EUR payments
- **WHEN** a CZK tournament has EUR payments disabled
- **THEN** every amount is presented in CZK only

#### Scenario: EUR-priced tournament shows one figure
- **WHEN** a tournament's primary currency is EUR
- **THEN** amounts are presented in EUR once, with no second currency figure

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

### Requirement: Confirmation email with QR payment
On registration the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament has EUR payments enabled and its primary currency is not EUR, the email SHALL additionally carry the EUR amount and a second QR code denominated in EUR against the same account.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

#### Scenario: EUR QR included
- **WHEN** a CZK tournament has EUR payments enabled and a reservation is created
- **THEN** the email carries both the CZK amount with its QR and the EUR amount with a QR denominated in EUR

#### Scenario: No EUR block without EUR payments
- **WHEN** a tournament has EUR payments disabled
- **THEN** the email carries exactly one amount and one QR code

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
The system SHALL accept a registration only when the tournament's mandatory setup is complete and the current date is within the registration window: on or after the registration-opens date when set, and on or before the registration-closes date when set (otherwise up to the tournament date). When registration is unavailable, the rejection SHALL carry a distinct reason — not yet published, not yet open, or closed — so clients can present it (with the opening date where applicable).

#### Scenario: Setup incomplete
- **WHEN** a fencer attempts to register for a tournament whose mandatory setup is incomplete
- **THEN** the registration is rejected with the not-yet-published reason

#### Scenario: After close
- **WHEN** a fencer attempts to register after the registration-closes date
- **THEN** the registration is rejected with the closed reason

### Requirement: Cancellation and refund policy
A fencer SHALL be able to cancel a registration. A cancellation before the tournament's refundable-until date SHALL be marked refundable; after that date the fee is not refundable and the freed spot is offered to substitutes. Refund execution is manual; the system SHALL track refund state on the registration.

#### Scenario: Cancellation after the refundable date
- **WHEN** a paid fencer cancels after the refundable-until date
- **THEN** the registration is cancelled without refund and the spot is offered to the substitute queue

### Requirement: Price preview
The system SHALL compute the total price for a hypothetical selection (disciplines and extra services with quantities and option values) for a tournament without creating a registration, using the same pricing engine — itemized pricing with discounts, or the legacy fee fields for legacy tournaments — that applies at registration time, evaluated as of the current date. The preview SHALL return the total in the tournament's primary currency, and its EUR equivalent when EUR payments are enabled on a non-EUR tournament.

#### Scenario: Preview matches registration
- **WHEN** a price preview is requested for a selection and the same selection is then submitted as a registration at the same date
- **THEN** the previewed total equals the registration's computed total

#### Scenario: Preview carries the EUR equivalent
- **WHEN** a price preview is requested on a CZK tournament with EUR payments enabled
- **THEN** the response carries the CZK total and its EUR equivalent at the tournament's stored rate

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, bank account (IBAN), variable symbol, payment message, reservation expiry, and the SPAYD QR code — plus the EUR amount and a EUR-denominated QR code when the tournament has EUR payments enabled and its primary currency is not EUR. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount with its currency, IBAN, VS, message, expiry, and QR code are returned

#### Scenario: EUR pair present only when applicable
- **WHEN** payment instructions are requested on a CZK tournament with EUR payments enabled and again on one with them disabled
- **THEN** the first response carries the EUR amount and EUR QR and the second omits both fields entirely

#### Scenario: Other accounts denied
- **WHEN** a different account requests those payment instructions
- **THEN** the request is rejected

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published (setup-complete), non-cancelled tournaments, each with its public information — including its subtitle and a reference to its logo when set, and its primary currency — its per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration. The subtitle and logo reference SHALL be omitted (null/absent) when not set, and their absence SHALL NOT change the rest of the payload.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Subtitle and logo carried when set
- **WHEN** a listed tournament has a subtitle and a logo
- **THEN** its list entry carries the subtitle and a reference to its logo, and entries without them omit those fields

#### Scenario: Currency carried
- **WHEN** a fencer requests the list
- **THEN** each entry carries the tournament's primary currency so amounts render without a hardcoded unit

#### Scenario: Unpublished excluded
- **WHEN** a tournament's mandatory setup is incomplete or it is cancelled
- **THEN** it is absent from the fencer-facing list
