# registration Specification

## Purpose
Handle in-app registration: reservations with per-reservation payment windows, QR payment confirmation emails, capacity and substitute queues, the public participant list, and cancellation policy.

## Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit, plus the non-billable fields: after-sparring, accommodation note, and free-text notes. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items. Registration is exposed through the API; a fencer-facing registration UI is a separate capability (deferred to a follow-up change).

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

### Requirement: Reservation lifecycle
A reservation SHALL be valid for the tournament's configured number of days from registration. There SHALL be no global payment deadline — each reservation carries its own window. An unpaid reservation SHALL expire automatically at the end of its window, freeing any capacity it held. A paid reservation SHALL become a confirmed registration.

#### Scenario: Reservation expires unpaid
- **WHEN** the validity window passes with no matched payment
- **THEN** the reservation expires automatically, its discipline capacity is freed, and the fencer is notified

#### Scenario: Payment arrives in time
- **WHEN** a matching payment is ingested before expiry
- **THEN** the reservation becomes a confirmed registration

### Requirement: Confirmation email with QR payment
On registration the system SHALL send a localized confirmation email containing the registration summary, total amount, bank account, VS, and an SPAYD-format QR code encoding amount, account, VS, and message.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, account, and VS needed for automatic matching

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
