# fencer-home Specification

## Purpose
Provide the fencer-facing GUI: a post-login Fencer Home landing listing open tournaments, a tournament detail page with the registration flow and in-app payment instructions, and registration management.

## Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by four tabs: Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Proběhlé turnaje (Past — every published, non-cancelled tournament dated before today, whoever was involved), and Moje turnaje (Mine — the account's own, per its own requirement). The first three SHALL be disjoint and SHALL together hold every published, non-cancelled tournament; Mine overlaps them by design. "Published" means the tournament carries a publication record, not that its setup happens to be complete. The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending, tournaments already held by date descending.

Each card SHALL present, in this order: the tournament logo at the left when one is set, then the tournament name, the subtitle beneath it when one is set, then the date and the location together on their own line in bold, then the organizer names, then the offered disciplines with registered numbers as taken/capacity, and the registration status — open, opens on a date, or closed. The date and place line SHALL separate its parts with the spaced middle dot and SHALL wrap rather than overflow on a narrow screen. The logo SHALL be drawn at twice the size a card gave it before this change. Card content SHALL have 1 em of left and right padding inside the card. The card layout SHALL render correctly whether or not a logo, subtitle, location, or organizer is present. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. Each tab SHALL show its own empty-state message when it lists nothing.

A discipline on a card SHALL be labelled by its name, never by its slug (`discipline-identity`). Names are longer than the codes they replace and a tournament MAY offer several disciplines whose names differ only in a trailing qualifier, so the discipline row on a card SHALL wrap across lines rather than truncate, overflow, or force the card wider, and SHALL remain legible on the narrowest supported screen.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with two disciplines (18 of 25 taken, and 25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, date and place in bold on their own line, organizers on the line below, each discipline named with its numbers, an "open" status, and a Register button

#### Scenario: Card lines in order
- **WHEN** a card renders a tournament with a subtitle, a location and two organizers
- **THEN** the name, the subtitle, the bold date and place line, and the organizers line appear in that order, with the logo at the left

#### Scenario: Disciplines named, not coded
- **WHEN** a card lists a tournament's disciplines
- **THEN** each is labelled by its name, and no slug appears on the card

#### Scenario: Many long discipline names wrap
- **WHEN** a card lists six disciplines whose names include trailing qualifiers, on a narrow screen
- **THEN** the discipline row wraps across lines, every name stays legible and untruncated, and the card does not widen or overflow

#### Scenario: Card shows logo and subtitle when set
- **WHEN** a listed tournament has a logo and a subtitle
- **THEN** its card shows the logo at the left at the enlarged size and the subtitle beneath the name

#### Scenario: Card degrades without logo, subtitle, or location
- **WHEN** a listed tournament has no logo, no subtitle, and no location
- **THEN** its card renders correctly without empty gaps for the missing logo, subtitle, or location line

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status badge and not in the Open tab

#### Scenario: Held tournament leaves the upcoming tabs
- **WHEN** a published tournament's date passes
- **THEN** it appears in the Past tab and in neither Announced nor Open

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
The Fencer Home top bar SHALL show, left to right: the Hema Squire logo, the four tournament filter tabs, the fencer's display name with their hemaratings identity, and the account menu (⋯). WHEN the account has a bound hemaratings profile, the identity SHALL read "HRID: <id>" and link to the fighter's hemaratings.com profile page in a new browser tab. WHEN no hemaratings profile is bound, the identity SHALL read "no hemaratings" and navigate to the Profile page, where binding is offered.

#### Scenario: Bound fencer sees HRID link
- **WHEN** a fencer whose account is bound to hemaratings fighter 1234 opens Fencer Home
- **THEN** the header shows their name and "HRID: 1234" linking to the hemaratings fighter page

#### Scenario: Unbound fencer is pointed to binding
- **WHEN** a fencer without a bound hemaratings profile clicks "no hemaratings" in the header
- **THEN** the Profile page opens

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list every published, non-cancelled tournament dated before today, ordered by date descending, whether or not the account was involved with it. Cards SHALL carry the same lines as an upcoming card — name, subtitle, bold date and place, organizers, per-discipline counts — and SHALL state the account's own registration state when it held one, or an organizer mark when it only organized. Selecting a past tournament SHALL open its detail in read-only mode.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data and its paid state, and opens in read-only detail when selected

#### Scenario: Unrelated past tournament listed too
- **WHEN** a past tournament exists where the fencer had no registration and is not its organizer
- **THEN** it is listed in the Past tab, with no registration state and no organizer mark

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

#### Scenario: Never-published past tournament hidden
- **WHEN** a past tournament was never published
- **THEN** it does not appear in the Past tab for anyone, including its organizer

### Requirement: Mine tab
The Mine tab SHALL list every published, non-cancelled tournament the account is bound to: one it holds or held a registration for — in any state, including cancelled and substitute — and one it organizes or organized, as tournament owner or console team member. It SHALL span both directions of today: upcoming tournaments and tournaments already held, ordered by date descending so the nearest events lead.

Each entry SHALL state which bond it stands on: its registration state when the account holds or held one, and an organizer mark when the account is only its organizer. An entry standing on both SHALL state the registration state, the stronger claim.

An upcoming entry SHALL open the tournament detail as any other list entry does; an entry already held SHALL open it read-only.

#### Scenario: Registration and organized tournaments together
- **WHEN** a fencer who registered for one upcoming tournament and organizes another opens the Mine tab
- **THEN** both are listed, the first marked with its registration state and the second marked as organized

#### Scenario: Cancelled registration still mine
- **WHEN** the account cancelled its registration for a tournament
- **THEN** that tournament is still listed under Mine, marked as cancelled

#### Scenario: Past and upcoming in one list
- **WHEN** the account holds a reservation for a tournament next month and held a paid registration for one last year
- **THEN** both appear in Mine, newest first, and the past one opens read-only

#### Scenario: Unrelated tournament absent
- **WHEN** a published tournament exists that the account neither registered for nor organizes
- **THEN** it does not appear in Mine

### Requirement: Fencer Home addressed by URL, filter tab included
Fencer Home SHALL be addressed by `/`, and the selected filter tab SHALL be carried in the
URL as the query parameter `tab`, whose values are `announced`, `open`, `past`, and `mine`.
An absent, empty, or unrecognised `tab` SHALL resolve to the Open tab, so that `/` remains
the landing URL and the rule that the Open tab is selected after login is unchanged.
Selecting a filter tab SHALL change the URL and push a browser history entry; a reload SHALL
reopen the tab named by the URL.

A tournament's detail page SHALL be addressed by `/t/:slug`.

#### Scenario: Tab named in the URL
- **WHEN** a fencer selects the Past tab
- **THEN** the address bar reads `/?tab=past` and the Past list is shown

#### Scenario: Landing URL selects Open
- **WHEN** a fencer opens `/` with no query string
- **THEN** the Open tab is selected

#### Scenario: Unrecognised tab value
- **WHEN** a visitor opens `/?tab=archive`
- **THEN** the Open tab is shown rather than an error or an empty list

#### Scenario: Tab survives a reload
- **WHEN** a fencer on `/?tab=mine` reloads the browser
- **THEN** the Mine tab is shown again

#### Scenario: Back steps between tabs
- **WHEN** a fencer selects Announced and then Mine, and presses Back
- **THEN** the Announced list is shown again

### Requirement: Tournament entries and filter tabs are links
Each tournament card in any of the four lists SHALL be a link to that tournament's `/t/:slug`
URL, and each filter tab SHALL be a link to its own `?tab=` URL, so that middle-click and
modifier-click open them in a new browser tab and the browser offers to copy their addresses.
Both SHALL keep the appearance they have as controls today: no default-blue text, no default
underline, and the same card and tab treatment as before.

#### Scenario: Card links to the tournament
- **WHEN** a fencer middle-clicks a tournament card
- **THEN** that tournament's detail page opens in a new browser tab at `/t/<slug>`

#### Scenario: Filter tab links to its list
- **WHEN** a fencer copies the address of the Mine tab
- **THEN** the copied address is `/?tab=mine`

#### Scenario: Appearance unchanged
- **WHEN** the lists and the tab bar render
- **THEN** cards and tabs look exactly as they did as buttons, with no link colour or underline introduced

### Requirement: Read-only past tournament detail
WHEN a tournament detail is shown for a tournament dated before today, the page SHALL present the tournament information (name, date, location, organizers, disciplines with fees, extra services with prices) and, when the account had a registration, its summary — state, selected disciplines and extra services, and the computed total. The page SHALL NOT offer registration, payment instructions, or cancellation.

Read-only-ness SHALL be a property of the tournament's date rather than of the way the page was reached, so that it holds for a detail opened from the Past tab, from the Mine tab, and from a `/t/:slug` link followed directly.

#### Scenario: Past detail shows history without actions
- **WHEN** a fencer opens a past tournament where they had a paid registration
- **THEN** the detail shows the tournament information and their paid registration summary, with no Register button, payment panel, or cancel action

#### Scenario: Past tournament reached by link
- **WHEN** a fencer follows a `/t/<slug>` link to a tournament dated before today
- **THEN** the detail is read-only, exactly as it is when opened from the Past tab

#### Scenario: Past tournament reached from Mine
- **WHEN** a fencer opens a tournament dated before today from the Mine tab
- **THEN** the detail is read-only

### Requirement: Tournament detail — page shell
The tournament detail page SHALL carry a header holding the tournament's display name, a tab control, and a close control, in that order across the header.

The tab control SHALL offer a `Tournament` tab, always present, holding the information screen. It SHALL offer a second tab whenever the account holds a registration for that tournament or registration is available to it: labelled `Registered` when a registration is held — active, substituted, or cancelled — and `Register` when none is held and registration is available. When neither condition holds, the tab control SHALL offer the `Tournament` tab alone, and the reason registration is unavailable SHALL be stated on the information screen as it is today.

The tab control SHALL offer a third tab, `Teams`, exactly when the account holds an active registration for that tournament carrying at least one team and the tournament has not yet been held. It SHALL NOT be offered to an account with no registration, with a cancelled or expired registration, or with a registration holding no team, nor on a tournament dated before today, whose rosters are no longer editable. It SHALL stand last in the tab control, after the second tab. WHEN the third tab is offered, the second tab reads `Registered`, since a team is held only through a held registration.

The page SHALL open on the `Tournament` tab from every entry point, including a URL followed directly. The selected tab SHALL NOT be carried in the URL and SHALL NOT push a browser history entry. WHEN a tab in the control ceases to be offered while it is selected, the page SHALL fall back to the `Tournament` tab rather than show a tab that no longer exists.

Amending an existing registration SHALL open the amendment form on the `Registered` tab, in place of the registration it amends, and SHALL return to that registration when it is submitted or abandoned. No further tab SHALL be introduced for it, and leaving the `Registered` tab — for the `Tournament` tab or the `Teams` tab alike — SHALL abandon an amendment in progress as it does today.

The close control SHALL return to the list the page was opened from — the Fencer Home list whose filter tab was selected when the tournament was opened — and SHALL replace the page's back links: no "back to tournaments" link and no "back to information" link SHALL be rendered. WHEN the page was reached by URL rather than from a list, the close control SHALL lead to Fencer Home on its default Open tab. The close control SHALL carry an accessible name naming the action, so it is not announced as an unlabelled glyph.

The page body SHALL scroll to its end whenever its content is taller than the space available, on every tab. No part of the content SHALL be reachable only by resizing the window.

Sections on any tab SHALL be separated from one another by vertical space, so that no two bordered sections share or abut an edge.

The tournament's logo, where set, SHALL be presented at twice the size it is given on a list card and without a frame around it.

#### Scenario: Detail opens on the tournament tab
- **WHEN** a fencer opens a tournament from Fencer Home
- **THEN** the page shows the tournament name, a tab control resting on `Tournament`, and a close control, with the information screen below

#### Scenario: Register tab offered while registration is available
- **WHEN** a fencer without a registration opens a tournament whose registration is open and has an open slot
- **THEN** the tab control offers `Tournament` and `Register`, and selecting `Register` shows the registration form in place

#### Scenario: Tab reads Registered once a registration is held
- **WHEN** a fencer holding a reservation opens the same tournament
- **THEN** the second tab reads `Registered` and holds the registration, its state, and its actions

#### Scenario: Teams tab offered for a registration holding a team
- **WHEN** a fencer holding a reservation that includes one team opens the tournament
- **THEN** the tab control offers `Tournament`, `Registered`, and `Teams` in that order, and selecting `Teams` shows that team's roster editor

#### Scenario: Teams tab withheld from an individual registration
- **WHEN** a fencer holding a registration for individual disciplines only opens the tournament
- **THEN** the tab control offers `Tournament` and `Registered` alone, with no `Teams` tab

#### Scenario: Teams tab withdrawn when the last team is dropped
- **WHEN** a fencer standing on the `Teams` tab amends their registration to remove its only team
- **THEN** the `Teams` tab is no longer offered and the page falls back to the `Tournament` tab

#### Scenario: Single tab when registration is impossible
- **WHEN** a fencer without a registration opens a tournament whose registration has closed
- **THEN** only the `Tournament` tab is offered and the information screen states that registration is closed

#### Scenario: Past tournament with a registration
- **WHEN** a fencer opens a past tournament from the Past tab where they held a paid registration
- **THEN** the `Registered` tab holds the read-only summary, and no register, payment, or cancel action is offered on either tab

#### Scenario: Teams tab withheld on a past tournament
- **WHEN** a fencer opens a tournament dated before today where they held a registration carrying a team
- **THEN** no `Teams` tab is offered, and the team and its members remain readable on the read-only summary

#### Scenario: Returning to the information screen
- **WHEN** the fencer is on the `Register`, `Registered`, or `Teams` tab
- **THEN** the `Tournament` tab returns them to the information screen without leaving the page

#### Scenario: Amending stays on the registered tab
- **WHEN** a fencer holding a reservation starts an amendment
- **THEN** the amendment form opens on the `Registered` tab, the tab control shows the same tabs as before, and submitting returns to the amended registration on that same tab

#### Scenario: Closing the page
- **WHEN** the fencer activates the close control
- **THEN** they return to the list the detail was opened from, on that list's filter tab

#### Scenario: Closing a page reached by link
- **WHEN** a fencer who followed a `/t/<slug>` link activates the close control
- **THEN** Fencer Home is shown on the Open tab

#### Scenario: Long tournament read to the end
- **WHEN** a fencer opens a tournament whose information is taller than the window
- **THEN** the page scrolls and the last section is reachable

#### Scenario: Sections stand apart
- **WHEN** the information screen renders the header, disciplines, discounts, and other-actions sections
- **THEN** vertical space separates each from the next, with no two section borders touching

### Requirement: Tournament detail shares the home heading
The tournament detail page SHALL carry the Fencer Home heading unchanged — the same title, the same tournament filter tabs, the same identity block and account menu, in the same order — so that opening a tournament reads as the same page rather than a different one. Selecting a filter tab from the detail page SHALL leave the detail and show that list.

The detail page's own controls — the tournament's display name, its tab control, and its close control — SHALL occupy a second row beneath that heading, and SHALL NOT be mixed into it.

#### Scenario: Heading survives opening a tournament
- **WHEN** a fencer opens a tournament from any list
- **THEN** the top row still shows the title, the four filter tabs, the identity block and the account menu, exactly as the list showed them

#### Scenario: Detail controls sit below
- **WHEN** the detail page is open
- **THEN** the tournament's name, its tab control, and its close control are on a second row under the heading

#### Scenario: Filter tab leaves the detail
- **WHEN** the fencer selects the Open tab while a tournament's detail is open
- **THEN** the detail closes and the Open list is shown

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL open with the tournament's identity stated as consecutive lines in this order: the title; the subtitle when set; the date, the location and the qualification statement on one line; the registration opening and closing dates on one line; the titular organizers; and the description. Parts sharing a line SHALL be separated by the spaced middle dot, and a line whose every part is absent SHALL be omitted rather than left blank. The logo, when set, stands beside these lines.

Below them the screen SHALL show three grouped sections. The disciplines section SHALL list each discipline by its name — never its slug (`discipline-identity`) — with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset shown as a short style name linking to the external ruleset document when a link is set. Several disciplines classified alike SHALL each be listed on their own line under their own name, with their own fee and their own count. A team discipline SHALL be listed in the same section, marked as a team event, with its per-team fee, its roster bounds, and its count stated in teams as entered/capacity (or waitlist length when full); the team-event marker SHALL be set off from the discipline's name by horizontal space rather than sitting flush against it. When the tournament sets a team composition deadline and offers at least one team discipline, the deadline SHALL be stated in this section. The discounts section SHALL follow the disciplines section and SHALL list every discount the tournament configures, in configured order, each with its name, its condition stated as text, and its configured value — a fixed amount in each configured currency, or a percentage. The discounts section SHALL NOT show selection markers, since the information screen carries no selection, and SHALL be omitted entirely when the tournament configures no discounts. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, it SHALL be reached through the page's `Register` tab rather than through a control on the information screen itself.

Where a discipline or an action carries any of its optional when/where/ruleset/remark text, that text SHALL be presented as a subordinate line beneath the row, one size down and in faded ink, with its parts separated by the spaced middle dot used elsewhere. The line SHALL NOT be introduced by a leading dash or any other bullet character: its indentation and weight already mark it as subordinate.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they read the title, the subtitle, the date · place · qualification line, the registration window line, the organizers and the description in that order, followed by each discipline under its name with its fee, registered/capacity count, and any when/where and ruleset link

#### Scenario: Absent parts collapse
- **WHEN** a tournament has no subtitle, no location and no registration dates
- **THEN** those lines are omitted and no blank line, stray dot, or empty gap is left behind

#### Scenario: Team marker set off from the name
- **WHEN** a team discipline is listed
- **THEN** its team-event marker is separated from the discipline's name by horizontal space, not placed flush against it

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
- **THEN** the page's `Register` tab is offered and opens the registration form, and the information screen itself carries no register button

### Requirement: Registration with live total
The Register screen SHALL be reached through the detail page's `Register` tab, offered only when the account has no active registration, registration is open, and at least one discipline or other purchasable item has an open slot. It SHALL present every purchasable item as one long list grouped into sections — tournament (disciplines), actions (seminars, afterparties, after-sparrings), gear lending (rentals), and merch & other — plus one non-billable field, a free-text note to the organizer. Each item SHALL offer selection or a quantity up to its limit. The displayed total SHALL be computed by the server pricing engine and refresh as the selection changes.

Below the purchasable items and above the total, the screen SHALL show a discounts section listing every discount the tournament configures, in configured order, each with its name, its configured value, and a read-only marker stating whether the current selection activates it. The marker states SHALL come from the server's pricing evaluation of the current selection, and the screen SHALL NOT evaluate discount conditions itself. The markers SHALL refresh with the total, from the same evaluation, so the section can never contradict the amount below it. WHEN no discount state is available for the current selection — nothing selected, or the price evaluation failed — every marker SHALL read as inactive rather than retain an earlier state. The section SHALL be omitted entirely when the tournament configures no discounts.

Submitting SHALL create the registration through the existing registration contract. WHEN a selected discipline is full, the screen SHALL surface the choice between trimming the selection and joining the substitute queue with the whole registration. On success the page SHALL move to the `Registered` tab, which thereafter holds the registration in place of the form.

#### Scenario: Register screen grouped by section
- **WHEN** the fencer opens the Register screen for a tournament with disciplines, a seminar, weapon rental, and a t-shirt
- **THEN** the items appear as one long list grouped into tournament, actions, gear lending, and merch & other sections, each selectable with a quantity up to its limit

#### Scenario: One non-billable field
- **WHEN** the fencer reaches the bottom of the Register screen
- **THEN** the only non-billable field offered is the free-text note, with no accommodation field and no after-sparring checkbox

#### Scenario: Register unavailable when nothing is open
- **WHEN** registration is closed, not yet open, or every discipline and item is full
- **THEN** no `Register` tab is offered on the detail page

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
- **THEN** a reservation is created and the page moves to the `Registered` tab, showing the registration with its payment instructions

#### Scenario: Full discipline choice
- **WHEN** the fencer submits a selection containing a full discipline
- **THEN** the screen presents the full disciplines and offers joining the substitute queue or removing them before resubmitting

### Requirement: In-app payment instructions
WHEN the account holds an unpaid reservation for the tournament, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and an SPAYD QR code. The QR code and the full transfer details SHALL always be shown together.

#### Scenario: Payment panel after registering
- **WHEN** a fencer completes a registration
- **THEN** the page shows the QR code alongside IBAN, amount, VS, and the VS-in-message instruction, and states when the reservation expires

### Requirement: Registration management
WHEN the account has a registration for the tournament, the detail page SHALL show its state (reserved with expiry, paid, substitute with queue positions per discipline, cancelled), the selected disciplines and extra services with the computed total, and SHALL offer cancellation per the cancellation policy.

The cancellation confirmation SHALL NOT assert that the fee is refundable, and SHALL NOT assert that it is not. Refundability is settled by the organizer outside the system, and the date it would be derived from is no longer configurable, so a promise in either direction would be one the system cannot keep. WHERE the registration is paid, the confirmation SHALL instead state that any refund is arranged with the organizer; WHERE nothing has been paid, it SHALL ask for confirmation alone, with no mention of money.

Every amount on the registration — each discipline, each team, each extra service, the total, and any outstanding balance — SHALL be aligned on one right-hand column, so the amounts read as a column that the total closes rather than as prices embedded in running text. A team's line SHALL name its discipline and its team together, in that order, against its per-team fee in that column.

The controls that amend and that cancel the registration SHALL be presented together as a spaced, centered pair, styled as destructive actions and each asking for confirmation before acting, per `design-system`.

WHEN the registration carries teams, it SHALL additionally list them: each team's name, its discipline, its per-team fee, its waitlisted state where applicable, and its roster in order with each member's name and, where bound, their club. Each team SHALL offer a roster editor, which adds, removes, renames, rebinds, and reorders members through the nationality-filtered HEMA Ratings search, saving without recomputing the total or sending any email. The roster editor SHALL state the discipline's roster bounds, how many members the team still needs to reach its minimum, and the composition deadline when one is set. It SHALL remain available after the amendment window has closed and until the tournament date, and SHALL be absent on a cancelled or expired registration.

A member SHALL occupy exactly one line of the roster, carrying that member's name and its row actions; the member's club, where bound, SHALL be stated on that same line and never on a second one. Adding a member SHALL be offered as a single control that opens a dialog: the dialog SHALL ask for the name once, offer the HEMA Ratings search on that one name, and add the member on confirmation — the roster itself SHALL carry no inline name field and no inline search block. Rebinding an existing member SHALL open that same dialog on that member. Cancelling the dialog SHALL leave the roster untouched.

A member the search does not find SHALL be enterable as a plain name, and SHALL be presented as an ordinary member thereafter, never marked as incomplete or in error.

#### Scenario: Paid registration shown
- **WHEN** a fencer with a paid registration opens the tournament detail
- **THEN** the page shows the paid state and the selected items, and no payment instructions are shown

#### Scenario: Amounts aligned in one column
- **WHEN** a registration holds two disciplines, a team, and an extra service
- **THEN** every amount, including the total, is aligned on the same right-hand column

#### Scenario: Team line names discipline and team
- **WHEN** a registration holds the team "Draci" in the discipline "Team Sabre Open" at 3 000 Kč
- **THEN** its line reads the discipline and the team name together, with 3 000 Kč aligned in the amount column

#### Scenario: Destructive pair presented together
- **WHEN** a fencer with an amendable registration reaches the bottom of it
- **THEN** the amend and cancel controls stand side by side, centered, with space between them, both styled as destructive

#### Scenario: Paid cancellation promises nothing either way
- **WHEN** a fencer with a paid registration activates the cancel control
- **THEN** the confirmation states that any refund of the fee is arranged with the organizer, and neither promises a refund nor rules one out

#### Scenario: Unpaid cancellation mentions no money
- **WHEN** a fencer whose registration has not been paid activates the cancel control
- **THEN** the confirmation asks only whether to cancel the registration, saying nothing about refunds

#### Scenario: Amend asks first
- **WHEN** the fencer activates the amend control
- **THEN** a confirmation is asked before the amendment form opens

#### Scenario: Teams shown on the registration
- **WHEN** a fencer holding a registration with two teams opens the tournament detail
- **THEN** both teams are listed with their names, disciplines, fees, and ordered rosters, each with a roster editor

#### Scenario: One line per member
- **WHEN** a roster holds a member bound to a HEMA Ratings profile carrying a club
- **THEN** that member occupies one line showing their name, their club, and their row actions, and no second line for the same member appears

#### Scenario: Member added through the dialog
- **WHEN** the fencer activates Add member, types a name, searches, and confirms a result
- **THEN** the dialog closes and the member appears on the roster bound to that profile, with no name field or search block left on the roster itself

#### Scenario: Dialog cancelled changes nothing
- **WHEN** the fencer opens the add-member dialog, types a name, and cancels
- **THEN** the roster is unchanged and reports no unsaved edit

#### Scenario: Roster edited without touching money
- **WHEN** the fencer replaces a member and saves
- **THEN** the roster is updated and the registration's total, outstanding balance, and payment state are unchanged, with no email sent

#### Scenario: Shortfall stated
- **WHEN** a team holds two members against a minimum of three
- **THEN** the editor states that one more member is needed and shows the composition deadline when one is set

#### Scenario: Unknown name entered plainly
- **WHEN** the fencer types a name the HEMA Ratings search does not match and confirms it
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
