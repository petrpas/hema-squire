## MODIFIED Requirements

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL show: name, subtitle when set, logo when set, date, location, organizer names, registration window, and two grouped sections. The disciplines section SHALL list each discipline with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset shown as a short style name linking to the external ruleset document when a link is set. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, the screen SHALL offer a control that opens the separate Register screen.

Where a discipline or an action carries any of its optional when/where/ruleset/remark text, that text SHALL be presented as a subordinate line beneath the row, one size down and in faded ink, with its parts separated by the spaced middle dot used elsewhere. The line SHALL NOT be introduced by a leading dash or any other bullet character: its indentation and weight already mark it as subordinate.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they see the date, location, organizers, and each discipline with its fee, registered/capacity count, and any when/where and ruleset link, on an information screen without the registration form

#### Scenario: Detail line carries no leading dash
- **WHEN** a discipline with a when, a where and a ruleset is presented on the information screen
- **THEN** its subordinate line begins with the when value, with no dash, hyphen or bullet before it, and the three parts are separated by the spaced middle dot

#### Scenario: Actions grouped without gear or merch
- **WHEN** the tournament offers a seminar and an afterparty alongside gear lending and merch items
- **THEN** the information screen lists the seminar and afterparty under other actions with their when/where and remark, and does not show gear lending, merch, prices, or quantity selectors

#### Scenario: Open Register from information
- **WHEN** the fencer views the information screen while registration is available
- **THEN** a control is offered that opens the separate Register screen

### Requirement: Registration with live total
The Register screen SHALL be a separate screen reached from the information screen, available only when the account has no active registration, registration is open, and at least one discipline or other purchasable item has an open slot. It SHALL present every purchasable item as one long list grouped into sections — tournament (disciplines), actions (seminars, afterparties, after-sparrings), gear lending (rentals), and merch & other — plus one non-billable field, a free-text note to the organizer. Each item SHALL offer selection or a quantity up to its limit. The displayed total SHALL be computed by the server pricing engine and refresh as the selection changes. Submitting SHALL create the registration through the existing registration contract. WHEN a selected discipline is full, the screen SHALL surface the choice between trimming the selection and joining the substitute queue with the whole registration.

#### Scenario: Register screen grouped by section
- **WHEN** the fencer opens the Register screen for a tournament with disciplines, a seminar, weapon rental, and a t-shirt
- **THEN** the items appear as one long list grouped into tournament, actions, gear lending, and merch & other sections, each selectable with a quantity up to its limit

#### Scenario: One non-billable field
- **WHEN** the fencer reaches the bottom of the Register screen
- **THEN** the only non-billable field offered is the free-text note, with no accommodation field and no after-sparring checkbox

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
