# tournament-admin Specification

## Purpose
Define and configure tournaments in a multi-tournament deployment: disciplines, pricing, payment and reservation parameters, and organizer authorization.

## Requirements

### Requirement: Multiple tournaments in one deployment
The system SHALL host multiple tournaments concurrently in a single deployment. Registrations, rules, operation parameters, pricing, and exports SHALL be tournament-scoped; fencer accounts SHALL be shared globally.

#### Scenario: Two tournaments run in parallel
- **WHEN** organizers administer two tournaments at the same time
- **THEN** the data, rules, and parameters of one tournament are invisible to and unaffected by the other

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, date, communication language, and a set of disciplines. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, and a fee.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW, each with a capacity and a fee
- **THEN** registration offers exactly those disciplines under those constraints

### Requirement: Pricing configuration
The system SHALL compute registration totals from configurable billable items: per-discipline fee, weapon rental, and afterparty. An optional early-bird window with reduced prices SHALL be supported.

#### Scenario: Early bird active
- **WHEN** a fencer registers within the early-bird window
- **THEN** the total is computed from early-bird prices and frozen for that reservation

### Requirement: Payment and reservation parameters
Per tournament, the organizer SHALL configure: reservation validity in days, reminder day, amount-matching tolerance in percent, refundable-until date, the bank account used in payment instructions, and the public-list treatment of unpaid registrations.

#### Scenario: Parameters applied
- **WHEN** the organizer sets reservation validity to 10 days and the reminder to day 5
- **THEN** new reservations expire after 10 unpaid days and reminder emails go out on day 5

### Requirement: Organizer authorization
Administration of a tournament SHALL be restricted to its authorized organizers.

#### Scenario: Unauthorized user
- **WHEN** a signed-in user without organizer rights for the tournament opens its console
- **THEN** access is denied
