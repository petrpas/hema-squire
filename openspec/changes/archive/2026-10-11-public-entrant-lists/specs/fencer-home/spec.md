## MODIFIED Requirements

### Requirement: Tournament detail — page shell
The tournament detail page SHALL carry a header holding the tournament's display name, a tab control, and a close control, in that order across the header.

Below 768px that header SHALL be laid out on two rows instead: the display name on its own row with the close control at its right, and the tab control below it as one full-width scrolling band. The close control SHALL remain level with the display name.

The tab control SHALL offer a `Tournament` tab, always present, holding the information screen, and after it an `Entrants` tab, always present on a published tournament, holding the tournament's rosters (`public-entrants`). It SHALL offer a registration tab after these whenever the account holds a registration for that tournament or registration is available to it: labelled `Registered` when a registration is held — active, substituted, or cancelled — and `Register` when none is held and registration is available. When neither condition holds, the tab control SHALL offer the `Tournament` and `Entrants` tabs alone, and the reason registration is unavailable SHALL be stated on the information screen as it is today.

The tab control SHALL offer a further tab, `Teams`, exactly when the account holds an active registration for that tournament carrying at least one team and the tournament has not yet been held. It SHALL NOT be offered to an account with no registration, with a cancelled or expired registration, or with a registration holding no team, nor on a tournament dated before today, whose rosters are no longer editable. It SHALL stand last in the tab control, after the registration tab. WHEN the `Teams` tab is offered, the registration tab reads `Registered`, since a team is held only through a held registration.

The page SHALL open on the `Tournament` tab from every entry point, including a URL followed directly, except the Entrants address (`routing`), which SHALL open on the `Entrants` tab at the discipline it names, or at the first discipline where it names none. The `Entrants` tab and each discipline within it SHALL be links to their own addresses, so that a roster can be linked to and Back returns from it. Leaving the `Entrants` tab for another tab SHALL return the URL to the tournament's own address. No other tab SHALL be carried in the URL, and selecting one SHALL NOT push a browser history entry. WHEN a tab in the control ceases to be offered while it is selected, the page SHALL fall back to the `Tournament` tab rather than show a tab that no longer exists.

Amending an existing registration SHALL open the amendment form on the `Registered` tab, in place of the registration it amends, and SHALL return to that registration when it is submitted or abandoned. No further tab SHALL be introduced for it, and leaving the `Registered` tab — for the `Tournament` tab or the `Teams` tab alike — SHALL abandon an amendment in progress as it does today.

The close control SHALL return to the list the page was opened from — the Fencer Home list whose filter tab was selected when the tournament was opened — and SHALL replace the page's back links: no "back to tournaments" link and no "back to information" link SHALL be rendered. WHEN the page was reached by URL rather than from a list, the close control SHALL lead to Fencer Home on its default Open tab. The close control SHALL carry an accessible name naming the action, so it is not announced as an unlabelled glyph.

The page body SHALL scroll to its end whenever its content is taller than the space available, on every tab. No part of the content SHALL be reachable only by resizing the window.

Sections on any tab SHALL be separated from one another by vertical space, so that no two bordered sections share or abut an edge.

The tournament's logo, where set, SHALL be presented at twice the size it is given on a list card and without a frame around it.

Organizer-authored prose on any tab SHALL wrap rather than overflow its column, including an unbroken string such as a bare URL, at every viewport width.

#### Scenario: Detail opens on the tournament tab
- **WHEN** a fencer opens a tournament from Fencer Home
- **THEN** the page shows the tournament name, a tab control resting on `Tournament` with `Entrants` beside it, and a close control, with the information screen below

#### Scenario: Detail header on a narrow phone
- **WHEN** a fencer opens a tournament on a 390px-wide viewport
- **THEN** the tournament name occupies its own row with the close control at its right, the tab control sits below it as a full-width scrolling band, and the page does not scroll sideways

#### Scenario: Register tab offered while registration is available
- **WHEN** a fencer without a registration opens a tournament whose registration is open and has an open slot
- **THEN** the tab control offers `Tournament`, `Entrants` and `Register`, and selecting `Register` shows the registration form in place

#### Scenario: Tab reads Registered once a registration is held
- **WHEN** a fencer holding a reservation opens the same tournament
- **THEN** the second tab reads `Registered` and holds the registration, its state, and its actions

#### Scenario: Teams tab offered for a registration holding a team
- **WHEN** a fencer holding a reservation that includes one team opens the tournament
- **THEN** the tab control offers `Tournament`, `Entrants`, `Registered`, and `Teams` in that order, and selecting `Teams` shows that team's roster editor

#### Scenario: Teams tab withheld from an individual registration
- **WHEN** a fencer holding a registration for individual disciplines only opens the tournament
- **THEN** the tab control offers `Tournament`, `Entrants` and `Registered` alone, with no `Teams` tab

#### Scenario: Teams tab withdrawn when the last team is dropped
- **WHEN** a fencer standing on the `Teams` tab amends their registration to remove its only team
- **THEN** the `Teams` tab is no longer offered and the page falls back to the `Tournament` tab

#### Scenario: Single tab when registration is impossible
- **WHEN** a fencer without a registration opens a tournament whose registration has closed
- **THEN** only the `Tournament` and `Entrants` tabs are offered and the information screen states that registration is closed

#### Scenario: Past tournament with a registration
- **WHEN** a fencer opens a past tournament from the Past tab where they held a paid registration
- **THEN** the `Registered` tab holds the read-only summary, and no register, payment, or cancel action is offered on either tab

#### Scenario: Teams tab withheld on a past tournament
- **WHEN** a fencer opens a tournament dated before today where they held a registration carrying a team
- **THEN** no `Teams` tab is offered, and the team and its members remain readable on the read-only summary

#### Scenario: Returning to the information screen
- **WHEN** the fencer is on the `Entrants`, `Register`, `Registered`, or `Teams` tab
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

#### Scenario: A bare URL in the organizer's description
- **WHEN** an organizer's description contains a long URL with no spaces and the page renders at 360px
- **THEN** the URL wraps within the column and the page does not scroll sideways

#### Scenario: The Entrants address opens its tab
- **WHEN** a visitor follows a link to `/t/spring-open-2026/entrants/sabre-open`
- **THEN** the detail page opens on the `Entrants` tab showing the Sabre Open roster

#### Scenario: Leaving the Entrants tab
- **WHEN** a visitor on `/t/spring-open-2026/entrants/sabre-open` selects the `Tournament` tab
- **THEN** the information screen is shown and the address bar reads `/t/spring-open-2026`

#### Scenario: Other tabs stay unaddressed
- **WHEN** a fencer selects the `Register` tab
- **THEN** the address bar is left as it was and no history entry is pushed

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL open with the tournament's identity stated as consecutive lines in this order: the title; the subtitle when set; the date, the city and the qualification statement on one line; the address on its own line when set; the registration opening moment and closing date on one line; the titular organizers; and the description. Parts sharing a line SHALL be separated by the spaced middle dot, and a line whose every part is absent SHALL be omitted rather than left blank. The logo, when set, stands beside these lines.

The opening moment SHALL be stated with its time of day whenever the tournament sets one, and with the zone that time is stated in. Where the tournament sets no opening time, the opening SHALL be stated as a date alone exactly as before, with no invented hour and no zone.

Below them the screen SHALL show three grouped sections. The disciplines section SHALL list each discipline by its name — never its slug (`discipline-identity`) — with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset rendered as an inline markdown field (`organizer-prose`), so that a ruleset naming versions in more than one language presents each version as its own link. Several disciplines classified alike SHALL each be listed on their own line under their own name, with their own fee and their own count. A team discipline SHALL be listed in the same section, marked as a team event, with its per-team fee, its roster bounds, and its count stated in teams as entered/capacity (or waitlist length when full); the team-event marker SHALL be set off from the discipline's name by horizontal space rather than sitting flush against it. When the tournament sets a team composition deadline and offers at least one team discipline, the deadline SHALL be stated in this section. Each discipline's count SHALL be a link to that discipline's roster on the `Entrants` tab (`public-entrants`). In the console's Setup preview, where the tournament may be a draft holding no roster, the count SHALL be stated without a link. The discounts section SHALL follow the disciplines section and SHALL list every discount the tournament configures, in configured order, each with its name, its condition stated as text, and its configured value — a fixed amount in each configured currency, or a percentage. The discounts section SHALL NOT show selection markers, since the information screen carries no selection, and SHALL be omitted entirely when the tournament configures no discounts. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, it SHALL be reached through the page's `Register` tab rather than through a control on the information screen itself.

Where a discipline or an action carries any of its optional when/where/ruleset/remark text, that text SHALL be presented as a subordinate line beneath the row, one size down and in faded ink, with its parts separated by the spaced middle dot used elsewhere. The line SHALL NOT be introduced by a leading dash or any other bullet character: its indentation and weight already mark it as subordinate.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they read the title, the subtitle, the date · place · qualification line, the address line, the registration window line, the organizers and the description in that order, followed by each discipline under its name with its fee, registered/capacity count, and any when/where and ruleset

#### Scenario: Absent parts collapse
- **WHEN** a tournament has no subtitle, no city, no address and no registration dates
- **THEN** those lines are omitted and no blank line, stray dot, or empty gap is left behind

#### Scenario: Opening moment states its hour
- **WHEN** a fencer opens the detail of a tournament whose registration opens at 18:00 on 1 September
- **THEN** the registration window line states that opening date together with 18:00 and the zone it is stated in

#### Scenario: Date-only opening states no hour
- **WHEN** a fencer opens the detail of a tournament whose registration-opens date carries no time
- **THEN** the line states the date alone, with no time and no zone

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

#### Scenario: Rules in two languages
- **WHEN** a discipline's ruleset reads `[Barbasetti Right of Way](https://example.com/cz.pdf) (CZ) · [EN](https://example.com/en.pdf)`
- **THEN** the subordinate line presents the ruleset label followed by both names as separate links to their own documents, with no markup characters visible, and the label itself is not a link

#### Scenario: Ruleset without a link
- **WHEN** a discipline's ruleset reads `Right of Way` with no link syntax
- **THEN** it is presented as plain text after the ruleset label, exactly as it was before the field accepted markdown

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

#### Scenario: A count leads to its roster
- **WHEN** a visitor selects the 24/32 count beside Longsword Open
- **THEN** the `Entrants` tab opens on the Longsword Open roster, at its own address

#### Scenario: The preview's counts are not links
- **WHEN** an organizer reads the information screen in the Setup preview of a draft
- **THEN** each discipline's count is stated as text and leads nowhere
