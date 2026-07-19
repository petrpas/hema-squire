## ADDED Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL list all published (setup-complete), non-cancelled tournaments whose date is today or later, ordered by date, each showing: tournament name, organizer names, date, location, the offered disciplines with registered numbers as taken/capacity (e.g. LS 18/25), and a registration status — open, opens on a date, or closed. Each tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with disciplines LS (18 of 25 taken) and SA (25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears with its name, organizers, date, location, per-discipline numbers, an "open" status, and a Register button

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament's mandatory setup is incomplete
- **THEN** it does not appear on Fencer Home

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed tournament
- **THEN** that tournament shows Manage registration instead of Register

### Requirement: Tournament detail — information
The tournament detail page SHALL present the tournament's full public information: name, date, location, organizer names, registration window, disciplines with entry fees and free places (or substitute-queue length when full), and the configured extra services with prices and per-registration limits.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they see the date, location, organizers, each discipline with its fee and free places, and each extra service with its price

### Requirement: Registration with live total
WHEN the account has no active registration and registration is open, the detail page SHALL offer a registration section: selecting at least one discipline, extra services with quantities up to their limits, and the non-billable fields (after-sparring, accommodation note, notes). The displayed total SHALL be computed by the server pricing engine and refresh as the selection changes. Submitting SHALL create the registration through the existing registration contract. WHEN a selected discipline is full, the page SHALL surface the choice between trimming the selection and joining the substitute queue with the whole registration.

#### Scenario: Total updates while selecting
- **WHEN** the fencer adds a second discipline that triggers a multi-discipline discount
- **THEN** the displayed total updates to the discounted amount computed by the server

#### Scenario: Successful registration from the page
- **WHEN** the fencer submits a valid selection
- **THEN** a reservation is created and the page switches to the registration view with payment instructions

#### Scenario: Full discipline choice
- **WHEN** the fencer submits a selection containing a full discipline
- **THEN** the page presents the full disciplines and offers joining the substitute queue or removing them before resubmitting

### Requirement: In-app payment instructions
WHEN the account holds an unpaid reservation for the tournament, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and an SPAYD QR code. The QR code and the full transfer details SHALL always be shown together.

#### Scenario: Payment panel after registering
- **WHEN** a fencer completes a registration
- **THEN** the page shows the QR code alongside IBAN, amount, VS, and the VS-in-message instruction, and states when the reservation expires

### Requirement: Registration management
WHEN the account has a registration for the tournament, the detail page SHALL show its state (reserved with expiry, paid, substitute with queue positions per discipline, cancelled), the selected disciplines and extra services with the computed total, and SHALL offer cancellation per the cancellation policy, stating whether the cancellation is refundable before the fencer confirms.

#### Scenario: Paid registration shown
- **WHEN** a fencer with a paid registration opens the tournament detail
- **THEN** the page shows the paid state and the selected items, and no payment instructions are shown

#### Scenario: Cancel before the refundable date
- **WHEN** the fencer cancels while the tournament's refundable-until date has not passed
- **THEN** the confirmation states the fee is refundable and the registration is cancelled on confirm

### Requirement: Navigation rewiring
Fencer Home SHALL be the post-login landing for every role. The tournament picker SHALL remain reachable only through the account menu's To Organizer entry and SHALL no longer contain the organizer plea section (the plea lives on the Profile page).

#### Scenario: Organizer lands on Fencer Home
- **WHEN** an organizer logs in
- **THEN** they land on Fencer Home and reach the tournament picker via the account menu

#### Scenario: Plea only on profile
- **WHEN** a plain fencer opens the tournament picker via the account menu
- **THEN** no plea section is shown there
