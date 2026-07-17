## ADDED Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and extras: weapon rental per weapon, afterparty, after-sparring, accommodation note, and free-text notes. The system SHALL record the registration time, compute the total from the tournament pricing, and create a reservation with a unique VS.

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, one weapon rental, and afterparty
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's price list
- **AND** a confirmation email with payment instructions is sent

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

### Requirement: Cancellation and refund policy
A fencer SHALL be able to cancel a registration. A cancellation before the tournament's refundable-until date SHALL be marked refundable; after that date the fee is not refundable and the freed spot is offered to substitutes. Refund execution is manual; the system SHALL track refund state on the registration.

#### Scenario: Cancellation after the refundable date
- **WHEN** a paid fencer cancels after the refundable-until date
- **THEN** the registration is cancelled without refund and the spot is offered to the substitute queue
