# fencer-home Specification

## Purpose
Provide the fencer-facing GUI: a post-login Fencer Home landing listing open tournaments, a tournament detail page with the registration flow and in-app payment instructions, and registration management.

## Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by three disjoint tabs: Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), and Proběhlé turnaje (Past — the fencer's own history). "Published" means the tournament carries a publication record, not that its setup happens to be complete. The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending and each card SHALL show: the tournament logo on the left when one is set, the tournament name, the subtitle beneath the name when one is set, organizer names, date, location, the offered disciplines with registered numbers as taken/capacity, and the registration status — open, opens on a date, or closed. Card content SHALL have 1 em of left and right padding inside the card. Date and place SHALL be presented as a responsive multi-column layout rather than one long line, collapsing to fewer columns on narrow screens. The card layout SHALL render correctly whether or not a logo, subtitle, or location is present. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. Each tab SHALL show its own empty-state message when it lists nothing.

A discipline on a card SHALL be labelled by its name, never by its slug (`discipline-identity`). Names are longer than the codes they replace and a tournament MAY offer several disciplines whose names differ only in a trailing qualifier, so the discipline row on a card SHALL wrap across lines rather than truncate, overflow, or force the card wider, and SHALL remain legible on the narrowest supported screen.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with two disciplines (18 of 25 taken, and 25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, organizers, date, location, each discipline named with its numbers, an "open" status, and a Register button

#### Scenario: Disciplines named, not coded
- **WHEN** a card lists a tournament's disciplines
- **THEN** each is labelled by its name, and no slug appears on the card

#### Scenario: Many long discipline names wrap
- **WHEN** a card lists six disciplines whose names include trailing qualifiers, on a narrow screen
- **THEN** the discipline row wraps across lines, every name stays legible and untruncated, and the card does not widen or overflow

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
- **WHEN** a tournament has not been published
- **THEN** it does not appear in any Fencer Home tab, even when its mandatory setup is complete

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
The Proběhlé turnaje tab SHALL list only published, non-cancelled tournaments dated before today in which the account participated — held a non-cancelled registration (paid, reserved, or substitute) — or which the account organized, ordered by date descending. Other past tournaments SHALL NOT be listed. Cards SHALL show the tournament name, organizer names, date, location, and per-discipline counts; a tournament where the account only organized SHALL be marked as organized instead of showing a registration state. Selecting a past tournament SHALL open its detail in read-only mode.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data and opens in read-only detail when selected

#### Scenario: Unrelated and cancelled-registration tournaments hidden
- **WHEN** a past tournament exists where the fencer had no registration or only a cancelled one, and the fencer is not its organizer
- **THEN** it does not appear in the Past tab

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

#### Scenario: Never-published past tournament hidden
- **WHEN** a past tournament was never published
- **THEN** it does not appear in the Past tab for anyone, including its organizer

### Requirement: Read-only past tournament detail
WHEN a tournament detail is opened from the Past tab, the page SHALL present the tournament information (name, date, location, organizers, disciplines with fees, extra services with prices) and, when the account had a registration, its summary — state, selected disciplines and extra services, and the computed total. The page SHALL NOT offer registration, payment instructions, or cancellation.

#### Scenario: Past detail shows history without actions
- **WHEN** a fencer opens a past tournament where they had a paid registration
- **THEN** the detail shows the tournament information and their paid registration summary, with no Register button, payment panel, or cancel action

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL show: name, subtitle when set, logo when set, date, location, organizer names, registration window, and three grouped sections. The disciplines section SHALL list each discipline by its name — never its slug (`discipline-identity`) — with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset shown as a short style name linking to the external ruleset document when a link is set. Several disciplines classified alike SHALL each be listed on their own line under their own name, with their own fee and their own count. A team discipline SHALL be listed in the same section, marked as a team event, with its per-team fee, its roster bounds, and its count stated in teams as entered/capacity (or waitlist length when full). When the tournament sets a team composition deadline and offers at least one team discipline, the deadline SHALL be stated in this section. The discounts section SHALL follow the disciplines section and SHALL list every discount the tournament configures, in configured order, each with its name, its condition stated as text, and its configured value — a fixed amount in each configured currency, or a percentage. The discounts section SHALL NOT show selection markers, since the information screen carries no selection, and SHALL be omitted entirely when the tournament configures no discounts. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, the screen SHALL offer a control that opens the separate Register screen.

Where a discipline or an action carries any of its optional when/where/ruleset/remark text, that text SHALL be presented as a subordinate line beneath the row, one size down and in faded ink, with its parts separated by the spaced middle dot used elsewhere. The line SHALL NOT be introduced by a leading dash or any other bullet character: its indentation and weight already mark it as subordinate.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they see the date, location, organizers, and each discipline under its name with its fee, registered/capacity count, and any when/where and ruleset link, on an information screen without the registration form

#### Scenario: Tiers listed separately
- **WHEN** a tournament offering two longsword disciplines with different capacities and fees is opened
- **THEN** both are listed on their own lines, each under its own name with its own fee and its own count

#### Scenario: Team discipline presented in teams
- **WHEN** a tournament offering a team discipline with capacity 8 and 5 teams entered is opened
- **THEN** that discipline is listed as a team event with its per-team fee, its roster bounds, and a count of 5/8 teams, alongside the composition deadline when one is set

#### Scenario: Detail line carries no leading dash
- **WHEN** a discipline with a when, a where and a ruleset is presented on the information screen
- **THEN** its subordinate line begins with the when value, with no dash, hyphen or bullet before it, and the three parts are separated by the spaced middle dot

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
The Register screen SHALL be a separate screen reached from the information screen, available only when the account has no active registration, registration is open, and at least one discipline or other purchasable item has an open slot. It SHALL present every purchasable item as one long list grouped into sections — tournament (disciplines), actions (seminars, afterparties, after-sparrings), gear lending (rentals), and merch & other — plus one non-billable field, a free-text note to the organizer. Each item SHALL offer selection or a quantity up to its limit. The displayed total SHALL be computed by the server pricing engine and refresh as the selection changes.

Below the purchasable items and above the total, the screen SHALL show a discounts section listing every discount the tournament configures, in configured order, each with its name, its configured value, and a read-only marker stating whether the current selection activates it. The marker states SHALL come from the server's pricing evaluation of the current selection, and the screen SHALL NOT evaluate discount conditions itself. The markers SHALL refresh with the total, from the same evaluation, so the section can never contradict the amount below it. WHEN no discount state is available for the current selection — nothing selected, or the price evaluation failed — every marker SHALL read as inactive rather than retain an earlier state. The section SHALL be omitted entirely when the tournament configures no discounts.

Submitting SHALL create the registration through the existing registration contract. WHEN a selected discipline is full, the screen SHALL surface the choice between trimming the selection and joining the substitute queue with the whole registration.

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

### Requirement: In-app payment instructions
WHEN the account holds an unpaid reservation for the tournament, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and an SPAYD QR code. The QR code and the full transfer details SHALL always be shown together.

#### Scenario: Payment panel after registering
- **WHEN** a fencer completes a registration
- **THEN** the page shows the QR code alongside IBAN, amount, VS, and the VS-in-message instruction, and states when the reservation expires

### Requirement: Registration management
WHEN the account has a registration for the tournament, the detail page SHALL show its state (reserved with expiry, paid, substitute with queue positions per discipline, cancelled), the selected disciplines and extra services with the computed total, and SHALL offer cancellation per the cancellation policy, stating whether the cancellation is refundable before the fencer confirms.

WHEN the registration carries teams, it SHALL additionally list them: each team's name, its discipline, its per-team fee, its waitlisted state where applicable, and its roster in order with each member's name and, where bound, their club. Each team SHALL offer a roster editor, which adds, removes, renames, rebinds, and reorders members through the nationality-filtered HEMA Ratings search, saving without recomputing the total or sending any email. The roster editor SHALL state the discipline's roster bounds, how many members the team still needs to reach its minimum, and the composition deadline when one is set. It SHALL remain available after the amendment window has closed and until the tournament date, and SHALL be absent on a cancelled or expired registration.

A member the search does not find SHALL be enterable as a plain name, and SHALL be presented as an ordinary member thereafter, never marked as incomplete or in error.

#### Scenario: Paid registration shown
- **WHEN** a fencer with a paid registration opens the tournament detail
- **THEN** the page shows the paid state and the selected items, and no payment instructions are shown

#### Scenario: Cancel before the refundable date
- **WHEN** the fencer cancels while the tournament's refundable-until date has not passed
- **THEN** the confirmation states the fee is refundable and the registration is cancelled on confirm

#### Scenario: Teams shown on the registration
- **WHEN** a fencer holding a registration with two teams opens the tournament detail
- **THEN** both teams are listed with their names, disciplines, fees, and ordered rosters, each with a roster editor

#### Scenario: Roster edited without touching money
- **WHEN** the fencer replaces a member and saves
- **THEN** the roster is updated and the registration's total, outstanding balance, and payment state are unchanged, with no email sent

#### Scenario: Shortfall stated
- **WHEN** a team holds two members against a minimum of three
- **THEN** the editor states that one more member is needed and shows the composition deadline when one is set

#### Scenario: Unknown name entered plainly
- **WHEN** the fencer types a name the HEMA Ratings search does not match and saves it
- **THEN** the member is stored by name alone and is presented like any other member

#### Scenario: Editor open after amendments close
- **WHEN** the fencer opens the roster editor after the amendment window has closed
- **THEN** it is available and saves normally, while the controls that add or remove a team are not offered

### Requirement: Navigation rewiring
Fencer Home SHALL be the post-login landing for every role. The tournament picker SHALL remain reachable only through the account menu's To Organizer entry and SHALL no longer contain the organizer plea section (the plea lives on the Profile page).

#### Scenario: Organizer lands on Fencer Home
- **WHEN** an organizer logs in
- **THEN** they land on Fencer Home and reach the tournament picker via the account menu

#### Scenario: Plea only on profile
- **WHEN** a plain fencer opens the tournament picker via the account menu
- **THEN** no plea section is shown there
