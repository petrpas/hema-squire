## MODIFIED Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit, plus the non-billable fields: after-sparring, accommodation note, and free-text notes. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items. Registration is exposed through the API and through the fencer-facing tournament detail page (fencer-home capability).

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

## ADDED Requirements

### Requirement: Price preview
The system SHALL compute the total price for a hypothetical selection (disciplines and extra services with quantities) for a tournament without creating a registration, using the same pricing engine — itemized pricing with discounts, or the legacy fee fields for legacy tournaments — that applies at registration time, evaluated as of the current date.

#### Scenario: Preview matches registration
- **WHEN** a price preview is requested for a selection and the same selection is then submitted as a registration at the same date
- **THEN** the previewed total equals the registration's computed total

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount, bank account (IBAN), variable symbol, payment message, reservation expiry, and the SPAYD QR code, identical in content to the confirmation email.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount, IBAN, VS, message, expiry, and QR code are returned

#### Scenario: Other accounts denied
- **WHEN** a different account requests those payment instructions
- **THEN** the request is rejected

### Requirement: Fencer-facing tournament list
The system SHALL expose a tournament list for fencers containing only published (setup-complete), non-cancelled tournaments, each with its public information, per-discipline registered numbers (seats taken per capacity, counting confirmed registrations and unexpired reservations), the registration availability status (open, not yet open with the opening date, or closed), and whether the requesting account has an active registration.

#### Scenario: Counts and own status included
- **WHEN** a logged-in fencer requests the fencer-facing tournament list
- **THEN** each tournament carries taken/capacity numbers per discipline, its registration status, and a flag for the fencer's own active registration

#### Scenario: Unpublished excluded
- **WHEN** a tournament's mandatory setup is incomplete or it is cancelled
- **THEN** it is absent from the fencer-facing list
