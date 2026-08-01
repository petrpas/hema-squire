## MODIFIED Requirements

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL show: name, subtitle when set, logo when set, date, location, organizer names, registration window, and three grouped sections. The disciplines section SHALL list each discipline with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset shown as a short style name linking to the external ruleset document when a link is set. The discounts section SHALL follow the disciplines section and SHALL list every discount the tournament configures, in configured order, each with its name, its condition stated as text, and its configured value — a fixed amount in each configured currency, or a percentage. The discounts section SHALL NOT show selection markers, since the information screen carries no selection, and SHALL be omitted entirely when the tournament configures no discounts. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, the screen SHALL offer a control that opens the separate Register screen.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they see the date, location, organizers, and each discipline with its fee, registered/capacity count, and any when/where and ruleset link, on an information screen without the registration form

#### Scenario: Discounts listed below the disciplines
- **WHEN** a fencer opens the information screen of a tournament offering −500 Kč for 2 disciplines and −10 % for early registration
- **THEN** a discounts section appears below the disciplines listing both, each with its name, the condition under which it applies, and its value, with no selection markers

#### Scenario: Discount values shown per configured currency
- **WHEN** the information screen of a CZK + EUR tournament lists a fixed discount configured as 500 Kč / 20 €
- **THEN** the row states both amounts, exactly as discipline and item prices are stated on the same screen

#### Scenario: No discounts, no section
- **WHEN** a fencer opens the information screen of a tournament that configures no discounts
- **THEN** no discounts section and no empty-state text appear

#### Scenario: Actions grouped without gear or merch
- **WHEN** the tournament offers a seminar and an afterparty alongside gear lending and merch items
- **THEN** the information screen lists the seminar and afterparty under other actions with their when/where and remark, and does not show gear lending, merch, prices, or quantity selectors

#### Scenario: Open Register from information
- **WHEN** the fencer views the information screen while registration is available
- **THEN** a control is offered that opens the separate Register screen

### Requirement: Registration with live total
The Register screen SHALL be a separate screen reached from the information screen, available only when the account has no active registration, registration is open, and at least one discipline or other purchasable item has an open slot. It SHALL present every purchasable item as one long list grouped into sections — tournament (disciplines), actions (seminars, afterparties, after-sparrings), gear lending (rentals), and merch & other — plus the non-billable fields (accommodation note, notes). Each item SHALL offer selection or a quantity up to its limit. The displayed total SHALL be computed by the server pricing engine and refresh as the selection changes.

Below the purchasable items and above the total, the screen SHALL show a discounts section listing every discount the tournament configures, in configured order, each with its name, its configured value, and a read-only marker stating whether the current selection activates it. The marker states SHALL come from the server's pricing evaluation of the current selection, and the screen SHALL NOT evaluate discount conditions itself. The markers SHALL refresh with the total, from the same evaluation, so the section can never contradict the amount below it. WHEN no discount state is available for the current selection — nothing selected, or the price evaluation failed — every marker SHALL read as inactive rather than retain an earlier state. The section SHALL be omitted entirely when the tournament configures no discounts.

Submitting SHALL create the registration through the existing registration contract. WHEN a selected discipline is full, the screen SHALL surface the choice between trimming the selection and joining the substitute queue with the whole registration.

#### Scenario: Register screen grouped by section
- **WHEN** the fencer opens the Register screen for a tournament with disciplines, a seminar, weapon rental, and a t-shirt
- **THEN** the items appear as one long list grouped into tournament, actions, gear lending, and merch & other sections, each selectable with a quantity up to its limit

#### Scenario: Register unavailable when nothing is open
- **WHEN** registration is closed, not yet open, or every discipline and item is full
- **THEN** the Register screen is not offered from the information screen

#### Scenario: Total updates while selecting
- **WHEN** the fencer adds a second discipline that triggers a multi-discipline discount
- **THEN** the displayed total updates to the discounted amount computed by the server

#### Scenario: Markers follow the selection
- **WHEN** the fencer holds one discipline on a tournament offering −500 Kč for 2 disciplines and −200 Kč for 3, and then ticks a second discipline
- **THEN** the 2-discipline row becomes marked active, the 3-discipline row stays inactive, and the total drops by the discount in the same refresh

#### Scenario: Missed discount stays visible
- **WHEN** the fencer's selection activates no discount at all
- **THEN** every configured discount is still listed, all markers inactive, so the fencer can see what is on offer

#### Scenario: Markers cannot be operated
- **WHEN** the fencer clicks a discount row's marker
- **THEN** nothing changes: the marker reports the consequence of the selection above it and is not itself selectable

#### Scenario: Nothing selected
- **WHEN** the fencer has selected no discipline
- **THEN** the discounts section lists every discount with all markers inactive, beside a zero total

#### Scenario: Price evaluation unavailable
- **WHEN** the price evaluation for the current selection fails
- **THEN** the markers clear along with the total rather than leaving a previous selection's discounts marked active

#### Scenario: Successful registration from the screen
- **WHEN** the fencer submits a valid selection
- **THEN** a reservation is created and the flow switches to the registration view with payment instructions

#### Scenario: Full discipline choice
- **WHEN** the fencer submits a selection containing a full discipline
- **THEN** the screen presents the full disciplines and offers joining the substitute queue or removing them before resubmitting
