## MODIFIED Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by three disjoint tabs: Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), and Proběhlé turnaje (Past — the fencer's own history). The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending and each card SHALL show: the tournament logo on the left when one is set, the tournament name, the subtitle beneath the name when one is set, organizer names, date, location, the offered disciplines with registered numbers as taken/capacity (e.g. LS 18/25), and the registration status — open, opens on a date, or closed. Card content SHALL have 1 em of left and right padding inside the card. Date and place SHALL be presented as a responsive multi-column layout rather than one long line, collapsing to fewer columns on narrow screens. The card layout SHALL render correctly whether or not a logo, subtitle, or location is present. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. Each tab SHALL show its own empty-state message when it lists nothing.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with disciplines LS (18 of 25 taken) and SA (25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, organizers, date, location, per-discipline numbers, an "open" status, and a Register button

#### Scenario: Card shows logo and subtitle when set
- **WHEN** a listed tournament has a logo and a subtitle
- **THEN** its card shows the logo on the left and the subtitle beneath the name, with date and place in the responsive column layout

#### Scenario: Card degrades without logo, subtitle, or location
- **WHEN** a listed tournament has no logo, no subtitle, and no location
- **THEN** its card renders correctly without empty gaps for the missing logo, subtitle, or location line

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

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL show: name, subtitle when set, logo when set, date, location, organizer names, registration window, and two grouped sections. The disciplines section SHALL list each discipline with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset shown as a short style name linking to the external ruleset document when a link is set. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, the screen SHALL offer a control that opens the separate Register screen.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they see the date, location, organizers, and each discipline with its fee, registered/capacity count, and any when/where and ruleset link, on an information screen without the registration form

#### Scenario: Actions grouped without gear or merch
- **WHEN** the tournament offers a seminar and an afterparty alongside gear lending and merch items
- **THEN** the information screen lists the seminar and afterparty under other actions with their when/where and remark, and does not show gear lending, merch, prices, or quantity selectors

#### Scenario: Open Register from information
- **WHEN** the fencer views the information screen while registration is available
- **THEN** a control is offered that opens the separate Register screen

### Requirement: Registration with live total
The Register screen SHALL be a separate screen reached from the information screen, available only when the account has no active registration, registration is open, and at least one discipline or other purchasable item has an open slot. It SHALL present every purchasable item as one long list grouped into sections — tournament (disciplines), actions (seminars, afterparties, after-sparrings), gear lending (rentals), and merch & other — plus the non-billable fields (accommodation note, notes). Each item SHALL offer selection or a quantity up to its limit. The displayed total SHALL be computed by the server pricing engine and refresh as the selection changes. Submitting SHALL create the registration through the existing registration contract. WHEN a selected discipline is full, the screen SHALL surface the choice between trimming the selection and joining the substitute queue with the whole registration.

#### Scenario: Register screen grouped by section
- **WHEN** the fencer opens the Register screen for a tournament with disciplines, a seminar, weapon rental, and a t-shirt
- **THEN** the items appear as one long list grouped into tournament, actions, gear lending, and merch & other sections, each selectable with a quantity up to its limit

#### Scenario: Register unavailable when nothing is open
- **WHEN** registration is closed, not yet open, or every discipline and item is full
- **THEN** the Register screen is not offered from the information screen

#### Scenario: Total updates while selecting
- **WHEN** the fencer adds a second discipline that triggers a multi-discipline discount
- **THEN** the displayed total updates to the discounted amount computed by the server

#### Scenario: Successful registration from the screen
- **WHEN** the fencer submits a valid selection
- **THEN** a reservation is created and the flow switches to the registration view with payment instructions

#### Scenario: Full discipline choice
- **WHEN** the fencer submits a selection containing a full discipline
- **THEN** the screen presents the full disciplines and offers joining the substitute queue or removing them before resubmitting
