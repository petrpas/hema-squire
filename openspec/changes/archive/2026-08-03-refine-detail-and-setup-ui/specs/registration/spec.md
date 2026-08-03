## ADDED Requirements

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
