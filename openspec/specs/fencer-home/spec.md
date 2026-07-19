# fencer-home Specification

## Purpose
Provide the fencer-facing GUI: a post-login Fencer Home landing listing open tournaments, a tournament detail page with the registration flow and in-app payment instructions, and registration management.

## Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by three disjoint tabs: Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), and Proběhlé turnaje (Past — the fencer's own history). The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending and each card SHALL show: tournament name, organizer names, date, location, the offered disciplines with registered numbers as taken/capacity (e.g. LS 18/25), and the registration status — open, opens on a date, or closed. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. Each tab SHALL show its own empty-state message when it lists nothing.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with disciplines LS (18 of 25 taken) and SA (25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, organizers, date, location, per-discipline numbers, an "open" status, and a Register button

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status badge and not in the Open tab

#### Scenario: Login lands on the Open tab
- **WHEN** any account logs in
- **THEN** Fencer Home opens with the Open tab selected

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament's mandatory setup is incomplete
- **THEN** it does not appear in any Fencer Home tab

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed upcoming tournament
- **THEN** that tournament shows Manage registration instead of Register

### Requirement: Fencer identity header
The Fencer Home top bar SHALL show, left to right: the Hema Squire logo, the three tournament filter tabs, the fencer's display name with their hemaratings identity, and the account menu (⋯). WHEN the account has a bound hemaratings profile, the identity SHALL read "HRID: <id>" and link to the fighter's hemaratings.com profile page in a new browser tab. WHEN no hemaratings profile is bound, the identity SHALL read "no hemaratings" and navigate to the Profile page, where binding is offered.

#### Scenario: Bound fencer sees HRID link
- **WHEN** a fencer whose account is bound to hemaratings fighter 1234 opens Fencer Home
- **THEN** the header shows their name and "HRID: 1234" linking to the hemaratings fighter page

#### Scenario: Unbound fencer is pointed to binding
- **WHEN** a fencer without a bound hemaratings profile clicks "no hemaratings" in the header
- **THEN** the Profile page opens

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list only non-cancelled tournaments dated before today in which the account participated — held a non-cancelled registration (paid, reserved, or substitute) — or which the account organized, ordered by date descending. Other past tournaments SHALL NOT be listed. Cards SHALL show the tournament name, organizer names, date, location, and per-discipline counts; a tournament where the account only organized SHALL be marked as organized instead of showing a registration state. Selecting a past tournament SHALL open its detail in read-only mode.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data and opens in read-only detail when selected

#### Scenario: Unrelated and cancelled-registration tournaments hidden
- **WHEN** a past tournament exists where the fencer had no registration or only a cancelled one, and the fencer is not its organizer
- **THEN** it does not appear in the Past tab

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

### Requirement: Read-only past tournament detail
WHEN a tournament detail is opened from the Past tab, the page SHALL present the tournament information (name, date, location, organizers, disciplines with fees, extra services with prices) and, when the account had a registration, its summary — state, selected disciplines and extra services, and the computed total. The page SHALL NOT offer registration, payment instructions, or cancellation.

#### Scenario: Past detail shows history without actions
- **WHEN** a fencer opens a past tournament where they had a paid registration
- **THEN** the detail shows the tournament information and their paid registration summary, with no Register button, payment panel, or cancel action

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
