## MODIFIED Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit, plus the non-billable fields: after-sparring, accommodation note, and free-text notes. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items. Registration is exposed through the API; a fencer-facing registration UI is a separate capability (deferred to a follow-up change).

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

## ADDED Requirements

### Requirement: Registration availability
The system SHALL accept a registration only when the tournament's mandatory setup is complete and the current date is within the registration window: on or after the registration-opens date when set, and on or before the registration-closes date when set (otherwise up to the tournament date). When registration is unavailable, the rejection SHALL carry a distinct reason — not yet published, not yet open, or closed — so clients can present it (with the opening date where applicable).

#### Scenario: Setup incomplete
- **WHEN** a fencer attempts to register for a tournament whose mandatory setup is incomplete
- **THEN** the registration is rejected with the not-yet-published reason

#### Scenario: After close
- **WHEN** a fencer attempts to register after the registration-closes date
- **THEN** the registration is rejected with the closed reason