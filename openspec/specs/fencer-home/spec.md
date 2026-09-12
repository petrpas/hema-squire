# fencer-home Specification

## Purpose
Provide the fencer-facing GUI: a post-login Fencer Home landing listing open tournaments, a tournament detail page with the registration flow and in-app payment instructions, and registration management.
## Requirements
### Requirement: Fencer Home landing
Every visitor SHALL land on the tournament list, whether or not they hold an account and whatever role they hold. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by four tabs: Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Proběhlé turnaje (Past — every published, non-cancelled tournament dated before today, whoever was involved), and Moje turnaje (Mine — the account's own, per its own requirement). The first three SHALL be disjoint and SHALL together hold every published, non-cancelled tournament; Mine overlaps them by design. "Published" means the tournament carries a publication record, not that its setup happens to be complete. Upcoming tournaments SHALL be ordered by date ascending, tournaments already held by date descending.

**The list SHALL hold the same tournaments for every visitor.** No role, and no absence of one, SHALL add or remove an entry. An organizer's extra power over a tournament they may manage SHALL be a control on that tournament's card and nothing more (see `Managing a tournament from its card`). Drafts and cancelled tournaments SHALL remain absent from every tab, for their own organizer too; the tournament picker remains the one place those are listed.

**Mine SHALL be offered only to an account.** An anonymous visitor SHALL be shown the three public tabs; the fourth is an account's own list and there is no account to list.

The filter tabs SHALL stand at the top of the main field, centred above the list, and SHALL NOT stand in the top bar (see `Fencer identity header`).

Each card SHALL present, in this order: the tournament logo at the left when one is set, then the tournament name, the subtitle beneath it when one is set, then the date and the city together on their own line in bold, then the organizer names, then the offered disciplines with registered numbers as taken/capacity, and the registration status — open, opens on a date, or closed. The date and city line SHALL separate its parts with the spaced middle dot and SHALL wrap rather than overflow on a narrow screen. The logo SHALL be drawn at twice the size a card gave it before `add-home-card-lines`. Card content SHALL have 1 em of left and right padding inside the card. The card layout SHALL render correctly whether or not a logo, subtitle, city, or organizer is present. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page, and for an anonymous visitor the Register action leads to sign-in (`public-browsing`). **A tournament in manual mode SHALL state on its card, in that action's place, that its registration is held elsewhere** (`tournament-mode`, `external-registration`), and SHALL offer no Register action. The way out itself SHALL be offered on the tournament detail page the card opens, where the registration form would otherwise be: the card is one link already, and a second inside it would be a link within a link. The card SHALL NOT state that registration is closed, which would be untrue of a window that never existed here. Each tab SHALL show its own empty-state message when it lists nothing.

A discipline on a card SHALL be labelled by its name, never by its slug (`discipline-identity`). Names are longer than the codes they replace and a tournament MAY offer several disciplines whose names differ only in a trailing qualifier, so the discipline row on a card SHALL wrap across lines rather than truncate, overflow, or force the card wider, and SHALL remain legible on the narrowest supported screen.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens the tournament list while a published upcoming tournament with two disciplines (18 of 25 taken, and 25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, date and place in bold on their own line, organizers on the line below, each discipline named with its numbers, an "open" status, and a Register button

#### Scenario: Card lines in order
- **WHEN** a card renders a tournament with a subtitle, a city and two organizers
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

#### Scenario: Card degrades without logo, subtitle, or city
- **WHEN** a listed tournament has no logo, no subtitle, and no city
- **THEN** its card renders correctly without empty gaps for the missing logo, subtitle, or city line

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status badge and not in the Open tab

#### Scenario: Held tournament leaves the upcoming tabs
- **WHEN** a published tournament's date passes
- **THEN** it appears in the Past tab and in neither Announced nor Open

#### Scenario: Login lands on the Open tab
- **WHEN** an account with no tournament of its own logs in while registration is open somewhere
- **THEN** the tournament list opens with the Open tab selected, as the default-tab rule resolves it

#### Scenario: One list for every role
- **WHEN** an organizer, a plain fencer and an anonymous visitor each open the Open tab at the same moment
- **THEN** all three see the same tournaments, in the same order, with the same cards

#### Scenario: Tabs above the list, not in the bar
- **WHEN** the tournament list renders
- **THEN** the filter tabs stand centred at the top of the main field and the top bar carries none of them

#### Scenario: Anonymous visitor has three tabs
- **WHEN** a visitor with no account opens the tournament list
- **THEN** Announced, Open and Past are offered and Mine is not

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament has not been published
- **THEN** it does not appear in any tab of the tournament list, even when its mandatory setup is complete, and even for the organizer who owns it

#### Scenario: An organizer-kept tournament points outward
- **WHEN** a fencer opens the tournament list while a published upcoming tournament whose registrations the organizer keeps is listed
- **THEN** its card offers a way out to where registration is held, offers no Register action, and does not describe registration as closed

#### Scenario: An organizer-kept tournament with no address recorded
- **WHEN** such a tournament records no external registration address
- **THEN** the card states that registration is held elsewhere and offers no action

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed upcoming tournament
- **THEN** that tournament shows Manage registration instead of Register

### Requirement: Where a tournament is, said in two fields
Where a tournament is held SHALL be carried as two fields: the **city**, the town it is in, and the **address**, where in that town. They are read by different screens and written to different rules.

The city SHALL be plain text — no markdown, no link. It is what a listing has room for, and everyone already knows where Berlin is. It SHALL be part of mandatory setup, as the single location field was before it.

The address SHALL be an inline markdown field (`organizer-prose`), a link among its honored constructs, so a venue can carry a map link. It SHALL be optional: a tournament that names its town has said where it is, and where in town can follow.

A Fencer Home card SHALL present the city, on the bold date-and-place line, and SHALL NOT present the address. The card is itself a link, and a second link inside it would be a link within a link.

The tournament information screen SHALL present the city on the `date · place · qualification` line and the address on its own line beneath it, rendered with its links live. Its own line rather than a fourth dot-joined part: an address runs longer than the short facts that line is made of.

Neither field SHALL introduce a block, a line break, or a heading of its own, both SHALL wrap rather than overflow on a narrow screen, and an absent field SHALL leave no stray middle dot and no empty line.

#### Scenario: City and address on the information screen
- **WHEN** a tournament in Brno whose address is `[ZŠ Bílá](https://osm.org/go/0J0ajlLg8?m=)` is opened
- **THEN** the identity line reads date · Brno · qualification and the line beneath it reads `ZŠ Bílá` as a link opening in a new tab, with no markup characters visible

#### Scenario: The same tournament on a home card
- **WHEN** that tournament is listed on Fencer Home
- **THEN** the bold date-and-place line reads date · Brno, the address appears nowhere on the card, and selecting anywhere on the card opens the tournament

#### Scenario: A tournament with no address yet
- **WHEN** a tournament names its city and no address
- **THEN** the information screen shows the city with no empty line beneath it, and setup does not report the address as missing

#### Scenario: Absent city leaves no separator
- **WHEN** a listed tournament has no city
- **THEN** the date stands alone on its line with no middle dot before or after it, on the card and on the information screen alike

### Requirement: Fencer identity header
The top bar SHALL show three things across it: the application's own name, Hema Squire, at the left; the page's title at the **centre**; and at the right the visitor's display name with their hemaratings identity, followed by the account menu (⋯).

The centre title SHALL read "Šermířské turnaje a akce" in Czech and "HEMA Tournaments and Events" in English — one line, in the UI language, drawn from the locale resources like every other string. It SHALL NOT carry both languages at once. The application's name at the left is not a translated string and SHALL read the same in every locale.

The title SHALL sit at the bar's true centre — equidistant from its edges — rather than at the centre of the space the two sides happen to leave. The two sides therefore take equal width, and a long identity SHALL shrink rather than push the title off centre.

The four tournament filter tabs SHALL NOT stand in the bar. They belong to the main field, above the list, which is what leaves the bar room for the title.

WHEN the account has a bound hemaratings profile, the identity SHALL read "HRID: <id>" and link to the fighter's hemaratings.com profile page in a new browser tab. WHEN no hemaratings profile is bound, the identity SHALL read "no hemaratings" and navigate to the Profile page, where binding is offered. WHEN there is no account at all, the identity's place SHALL offer sign-in and the account menu SHALL be absent (`public-browsing`). That sign-in control SHALL remain in the bar at every width: unlike the identity, it has no account menu to fold into, and a signed-out visitor on a phone would otherwise be left with no way in.

Below 768px the three do not fit across, and the bar SHALL be laid out as two rows instead. The first row SHALL carry the application's name at its left and the account menu at its right; the second SHALL carry the page title, still centred, across the full width. The identity — display name and hemaratings identity alike — SHALL fold into the account menu, shown when the menu is opened rather than standing permanently in the bar, and SHALL keep the same link and navigation behaviour there. The title SHALL wrap rather than overflow or push anything off the screen.

The bar SHALL stay at the top of the content as the page scrolls, positioned `sticky`, and SHALL add the device's top safe-area inset to its padding.

#### Scenario: Title in the bar
- **WHEN** the top bar renders with the UI language set to Czech
- **THEN** its centre reads "Šermířské turnaje a akce", and reads "HEMA Tournaments and Events" with the UI language set to English

#### Scenario: The application's name keeps its place at the left
- **WHEN** the top bar renders in any locale
- **THEN** "Hema Squire" stands at its left, untranslated, with the page title centred to its right

#### Scenario: Bound fencer sees HRID link
- **WHEN** a fencer whose account is bound to hemaratings fighter 1234 opens the tournament list
- **THEN** the header shows their name and "HRID: 1234" linking to the hemaratings fighter page

#### Scenario: Unbound fencer is pointed to binding
- **WHEN** a fencer without a bound hemaratings profile clicks "no hemaratings" in the header
- **THEN** the Profile page opens

#### Scenario: Top bar on a narrow phone
- **WHEN** a fencer opens the tournament list on a 390px-wide viewport
- **THEN** the first row shows the application's name and the account menu alone, the page title sits centred on a second row, the filter tabs stand above the list in the main field, and no part of the bar overflows the screen

#### Scenario: Sign-in survives the narrow layout
- **WHEN** a visitor with no account opens the tournament list on a 390px-wide viewport
- **THEN** the sign-in control is still in the bar, the identity's fold-away not applying to it

#### Scenario: Identity reachable from the menu on a phone
- **WHEN** that fencer opens the account menu
- **THEN** their display name and hemaratings identity are shown in it, the identity linking to the hemaratings fighter page when bound and to the Profile page when not

#### Scenario: Scrolling the list under the bar
- **WHEN** a fencer scrolls a long tournament list on a mobile browser
- **THEN** the top bar remains at the top of the content without detaching or overlapping the list

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list every published, non-cancelled tournament dated before today, ordered by date descending, whether or not the account was involved with it. Cards SHALL carry the same lines as an upcoming card — name, subtitle, bold date and place, organizers, per-discipline counts — and SHALL state the account's own registration state when it held one, or an organizer mark when it only organized. Selecting a past tournament SHALL open its detail in read-only mode.

The "today" that splits upcoming from held SHALL be **one global boundary, the UTC day**, and SHALL NOT be evaluated per tournament in that tournament's own zone. This list mixes tournaments from many zones and is answered by one comparison over all of them; the cost of an honest per-row boundary is a worse query, and its only effect is that a tournament held today stays under the upcoming tabs for the first hours of a morning east of UTC. This is a decision, not an oversight, and it is stated here so it is not read as one.

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

#### Scenario: The split is the same for every tournament
- **WHEN** two published tournaments held in different timezones share a date, and that date is yesterday in UTC
- **THEN** both appear in the Past tab, neither having waited for its own local midnight

#### Scenario: The split does not follow the deployment
- **WHEN** the Past tab is listed on a deployment whose process timezone is not UTC
- **THEN** the same tournaments are listed as on any other deployment
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
The tournament list SHALL be addressed by `/`, and the selected filter tab SHALL be carried in the
URL as the query parameter `tab`, whose values are `announced`, `open`, `past`, and `mine`.
An absent, empty, or unrecognised `tab` SHALL resolve to the **default tab**, which is chosen
from what there is to show rather than fixed (see `The default filter tab follows what there is
to show`). `/` SHALL remain the landing URL and SHALL NOT be rewritten once the default is
resolved: the bare URL means "the default tab", and a visitor who bookmarks it gets that
meaning again rather than the tab that happened to be chosen the first time.
Selecting a filter tab SHALL change the URL and push a browser history entry; a reload SHALL
reopen the tab named by the URL. **Every tab SHALL name itself**, Open included: while `/`
meant Open, an Open link could drop its `tab=` and still be right, and now that `/` means
"whatever the default resolves to", such a link would land wherever that resolution went.

A tournament's detail page SHALL be addressed by `/t/:slug`.

#### Scenario: Tab named in the URL
- **WHEN** a fencer selects the Past tab
- **THEN** the address bar reads `/?tab=past` and the Past list is shown

#### Scenario: Landing URL selects the default
- **WHEN** a fencer opens `/` with no query string
- **THEN** the default tab is selected and the address bar still reads `/`

#### Scenario: Landing URL selects Open
- **WHEN** a fencer with no tournament of their own opens `/` with no query string while registration is open somewhere
- **THEN** the Open tab is selected

#### Scenario: Unrecognised tab value
- **WHEN** a visitor opens `/?tab=archive`
- **THEN** the default tab is shown rather than an error or an empty list

#### Scenario: Mine named in the URL without an account
- **WHEN** an anonymous visitor opens `/?tab=mine`
- **THEN** the sign-in screen is shown at that URL, and after signing in the Mine tab is displayed

#### Scenario: Open names itself
- **WHEN** an account whose Mine list is non-empty lands on the resolved Mine tab and selects Open
- **THEN** the address bar reads `/?tab=open` and the Open list is shown, rather than `/` resolving back to Mine

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
WHEN a tournament detail is shown for a tournament dated before today, the page SHALL present the tournament information (name, date, city and address, organizers, disciplines with fees, extra services with prices) and, when the account had a registration, its summary — state, selected disciplines and extra services, and the computed total. The page SHALL NOT offer registration, payment instructions, or cancellation.

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

Below 768px that header SHALL be laid out on two rows instead: the display name on its own row with the close control at its right, and the tab control below it as one full-width scrolling band. The close control SHALL remain level with the display name.

The tab control SHALL offer a `Tournament` tab, always present, holding the information screen. It SHALL offer a second tab whenever the account holds a registration for that tournament or registration is available to it: labelled `Registered` when a registration is held — active, substituted, or cancelled — and `Register` when none is held and registration is available. When neither condition holds, the tab control SHALL offer the `Tournament` tab alone, and the reason registration is unavailable SHALL be stated on the information screen as it is today.

The tab control SHALL offer a third tab, `Teams`, exactly when the account holds an active registration for that tournament carrying at least one team and the tournament has not yet been held. It SHALL NOT be offered to an account with no registration, with a cancelled or expired registration, or with a registration holding no team, nor on a tournament dated before today, whose rosters are no longer editable. It SHALL stand last in the tab control, after the second tab. WHEN the third tab is offered, the second tab reads `Registered`, since a team is held only through a held registration.

The page SHALL open on the `Tournament` tab from every entry point, including a URL followed directly. The selected tab SHALL NOT be carried in the URL and SHALL NOT push a browser history entry. WHEN a tab in the control ceases to be offered while it is selected, the page SHALL fall back to the `Tournament` tab rather than show a tab that no longer exists.

Amending an existing registration SHALL open the amendment form on the `Registered` tab, in place of the registration it amends, and SHALL return to that registration when it is submitted or abandoned. No further tab SHALL be introduced for it, and leaving the `Registered` tab — for the `Tournament` tab or the `Teams` tab alike — SHALL abandon an amendment in progress as it does today.

The close control SHALL return to the list the page was opened from — the Fencer Home list whose filter tab was selected when the tournament was opened — and SHALL replace the page's back links: no "back to tournaments" link and no "back to information" link SHALL be rendered. WHEN the page was reached by URL rather than from a list, the close control SHALL lead to Fencer Home on its default Open tab. The close control SHALL carry an accessible name naming the action, so it is not announced as an unlabelled glyph.

The page body SHALL scroll to its end whenever its content is taller than the space available, on every tab. No part of the content SHALL be reachable only by resizing the window.

Sections on any tab SHALL be separated from one another by vertical space, so that no two bordered sections share or abut an edge.

The tournament's logo, where set, SHALL be presented at twice the size it is given on a list card and without a frame around it.

Organizer-authored prose on any tab SHALL wrap rather than overflow its column, including an unbroken string such as a bare URL, at every viewport width.

#### Scenario: Detail opens on the tournament tab
- **WHEN** a fencer opens a tournament from Fencer Home
- **THEN** the page shows the tournament name, a tab control resting on `Tournament`, and a close control, with the information screen below

#### Scenario: Detail header on a narrow phone
- **WHEN** a fencer opens a tournament on a 390px-wide viewport
- **THEN** the tournament name occupies its own row with the close control at its right, the tab control sits below it as a full-width scrolling band, and the page does not scroll sideways

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

#### Scenario: A bare URL in the organizer's description
- **WHEN** an organizer's description contains a long URL with no spaces and the page renders at 360px
- **THEN** the URL wraps within the column and the page does not scroll sideways

### Requirement: Tournament detail shares the home heading
The tournament detail page SHALL carry the top bar unchanged — the same title, the same identity block and account menu, in the same order — so that opening a tournament reads as the same page rather than a different one.

The filter tabs belong to the list's main field and SHALL NOT be shown while a tournament's detail is open. The way back to the list is the detail's close control, which SHALL return to the tab the tournament was opened from.

The detail page's own controls — the tournament's display name, its tab control, and its close control — SHALL occupy a second row beneath the bar, and SHALL NOT be mixed into it.

#### Scenario: Heading survives opening a tournament
- **WHEN** a fencer opens a tournament from any list
- **THEN** the top row still shows the title, the identity block and the account menu, exactly as the list showed them

#### Scenario: Detail controls sit below
- **WHEN** the detail page is open
- **THEN** the tournament's name, its tab control, and its close control are on a second row under the bar

#### Scenario: Closing returns to the tab it was opened from
- **WHEN** a fencer opens a tournament from the Announced tab and closes the detail
- **THEN** the Announced list is shown again

#### Scenario: Filter tab leaves the detail
- **WHEN** a tournament's detail is open
- **THEN** the four filter tabs are not shown anywhere on the page, and the close control rather than a tab is the way back to the list

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL open with the tournament's identity stated as consecutive lines in this order: the title; the subtitle when set; the date, the city and the qualification statement on one line; the address on its own line when set; the registration opening moment and closing date on one line; the titular organizers; and the description. Parts sharing a line SHALL be separated by the spaced middle dot, and a line whose every part is absent SHALL be omitted rather than left blank. The logo, when set, stands beside these lines.

The opening moment SHALL be stated with its time of day whenever the tournament sets one, and with the zone that time is stated in. Where the tournament sets no opening time, the opening SHALL be stated as a date alone exactly as before, with no invented hour and no zone.

Below them the screen SHALL show three grouped sections. The disciplines section SHALL list each discipline by its name — never its slug (`discipline-identity`) — with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset rendered as an inline markdown field (`organizer-prose`), so that a ruleset naming versions in more than one language presents each version as its own link. Several disciplines classified alike SHALL each be listed on their own line under their own name, with their own fee and their own count. A team discipline SHALL be listed in the same section, marked as a team event, with its per-team fee, its roster bounds, and its count stated in teams as entered/capacity (or waitlist length when full); the team-event marker SHALL be set off from the discipline's name by horizontal space rather than sitting flush against it. When the tournament sets a team composition deadline and offers at least one team discipline, the deadline SHALL be stated in this section. The discounts section SHALL follow the disciplines section and SHALL list every discount the tournament configures, in configured order, each with its name, its condition stated as text, and its configured value — a fixed amount in each configured currency, or a percentage. The discounts section SHALL NOT show selection markers, since the information screen carries no selection, and SHALL be omitted entirely when the tournament configures no discounts. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, it SHALL be reached through the page's `Register` tab rather than through a control on the information screen itself.

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

### Requirement: Waiting for registration to open
When a fencer opens the detail page of a published tournament whose registration has not yet opened, the page SHALL state the opening moment and SHALL open registration in place when that moment passes, without asking the fencer to reload. Registration opening is the busiest moment of a tournament's life, and a page that requires a manual refresh turns that into a burst of reloads at exactly the wrong time.

Within the last day before the opening moment, the page SHALL additionally show a **live countdown** to it, stated as a figure that decreases once per second. Outside that last day the opening moment SHALL be stated without any counter. The countdown SHALL be text and nothing more, as fixed by `design-system`: it SHALL NOT be accompanied by a bar, a ring, a spinner, or any moving decoration, and its line SHALL NOT reflow, shift, or change width as its digits change. It SHALL stop at the opening moment and be replaced by the opened state; it SHALL NEVER show a negative figure.

The page SHALL measure its own clock against the server's, using the server instant the response carries (`registration`), and SHALL count down and unlock against the corrected time rather than against the device clock. It SHALL NOT poll the server while waiting: the wait SHALL cost no request until the opening moment itself, at which point the page SHALL refresh the tournament once so that seat counts are current as registration opens. A page whose timer did not fire on time — a backgrounded tab, a sleeping device — SHALL re-evaluate the moment when it becomes visible or focused again, so that a fencer returning after the opening finds registration open immediately.

Opening the form in place is presentation only. The system's gate remains the authority (`registration`), and where a submission is nonetheless rejected as not yet open, the page SHALL return to the waiting state with its countdown recomputed from that response rather than showing a generic failure.

#### Scenario: Countdown inside the last day
- **WHEN** a fencer opens the detail page four hours before registration opens
- **THEN** the page states the opening moment and shows a countdown that decreases once per second

#### Scenario: No countdown far out
- **WHEN** a fencer opens the detail page six weeks before registration opens
- **THEN** the page states the opening moment and shows no counter

#### Scenario: Opens in place
- **WHEN** the fencer has the detail page open as the opening moment passes
- **THEN** the countdown ends, the tournament is refreshed once, and the `Register` tab becomes available without the fencer reloading the page

#### Scenario: Waiting costs no requests
- **WHEN** a fencer leaves the detail page open for an hour before the opening moment
- **THEN** the page issues no repeated requests for the tournament during that hour

#### Scenario: Tab returned to after the moment
- **WHEN** a fencer leaves the detail page in a background tab and returns to it ten minutes after registration opened
- **THEN** the page shows registration open as soon as it is looked at again

#### Scenario: Device clock is wrong
- **WHEN** a fencer's device clock is several minutes ahead of the server's
- **THEN** the countdown and the in-place opening still follow the server's clock, and the fencer is not shown a registration form the system would reject

#### Scenario: Submission still beats the gate
- **WHEN** a registration submitted from the opened form is rejected as not yet open
- **THEN** the page returns to stating the opening moment with its countdown, rather than showing a generic error

#### Scenario: The countdown does not move the page
- **WHEN** the countdown ticks from one second to the next
- **THEN** only the digits change: the line keeps its width and position, and nothing animates, fades, fills, or slides

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
WHEN the tournament's payments feature is on and the account holds an unpaid reservation for it, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and an SPAYD QR code. The QR code and the full transfer details SHALL always be shown together.

WHEN the tournament's payments feature is off, no payment instructions SHALL be shown for any registration it holds, whatever that registration owes on paper. There is no account to quote, no variable symbol in use and no expiry to state, and showing a partial set would tell the fencer to do something the tournament is not asking of them.

The QR code presumes two devices — the code on a screen, a phone in hand — and is inert to a fencer reading it on the phone they would pay with. The instructions SHALL therefore also be actionable on a single device, at every viewport width:

- The slip SHALL offer an action that hands the QR image to the device, so it can be taken into a banking application. Where the browser can share a file, the action SHALL offer the image to the system share sheet, from which it can be saved to the photo library or sent directly to an application. Where it cannot, the action SHALL fall back to downloading the image. The action SHALL NOT be offered as a download alone, because a downloaded file does not reach the photo library that banking applications read from on all platforms.
- Each transfer detail that must be entered by hand — bank account number, IBAN, variable symbol, and amount — SHALL offer an action to copy its value to the clipboard.
- A copy action SHALL be offered only where the browser exposes a clipboard, which requires a secure context; where it does not, the action SHALL be absent rather than present and failing.
- Confirmation that a value was copied SHALL be static text beside the field, leaving by fade-out. No toast, no entrance animation, and no animated indicator SHALL be used.

Below 480px the slip SHALL stack in the order the fencer needs it: the QR image first, centred and sized to the narrower of its intrinsic width and a fraction of the column; the actions below it; the transfer details last.

#### Scenario: Payment panel after registering
- **WHEN** a fencer completes a registration for a payments-enabled tournament
- **THEN** the page shows the QR code alongside IBAN, amount, VS, and the VS-in-message instruction, and states when the reservation expires

#### Scenario: No instructions for a payments-off tournament
- **WHEN** a fencer opens the detail page of a payments-off tournament they are registered for
- **THEN** no payment instructions, account, variable symbol, QR code or expiry date is shown

#### Scenario: Paying on the device showing the QR code
- **WHEN** a fencer on a phone opens the payment slip for an unpaid reservation
- **THEN** the slip offers an action that hands the QR image to the device's share sheet, from which it can be saved to the photo library or opened in a banking application

#### Scenario: Copying the variable symbol
- **WHEN** a fencer activates the copy action beside the variable symbol on a secure origin
- **THEN** the variable symbol is placed on the clipboard and a static note beside the field states that it was copied, then fades out

#### Scenario: Copy actions on a desktop
- **WHEN** the payment slip is shown at 1024px
- **THEN** the copy actions and the QR action are offered there too

#### Scenario: Clipboard unavailable
- **WHEN** the payment slip is shown on an origin where the browser exposes no clipboard
- **THEN** no copy action is rendered, and the values remain readable

#### Scenario: Payment slip on a narrow phone
- **WHEN** the payment slip renders at 390px
- **THEN** the QR image stands first and centred, the actions follow it, the transfer details follow those, and the fields are not compressed into a narrow column beside the code

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
The tournament list SHALL be the landing screen for every visitor, signed in or not, whatever role they hold. The tournament picker SHALL remain at its own URL, reachable through the account menu's My tournaments entry, which is shown only where the account holds a tournament to open (`profile-page`), and SHALL NOT contain the organizer plea section (the plea lives on the Profile page). The picker SHALL remain the only screen listing a tournament that the public list cannot show — a draft, or a cancelled tournament — which is why the Spravovat control on a card does not replace it.

Creating a tournament SHALL be offered from the account menu (`tournament-admin`), so an organizer reaches it from any screen rather than only from the picker.

#### Scenario: Organizer lands on the tournament list
- **WHEN** an organizer holding a tournament logs in
- **THEN** they land on the tournament list, the same one every visitor sees, and reach the tournament picker via the account menu

#### Scenario: Plea only on profile
- **WHEN** a plain fencer opens the tournament picker via the account menu
- **THEN** no plea section is shown there

#### Scenario: A draft is still reachable
- **WHEN** an organizer whose only tournament is an unpublished draft opens the picker
- **THEN** the draft is listed there, marked as a draft, and its console opens from that row

### Requirement: A payments-off registration presents no money to settle
WHEN the tournament's payments feature is off, the detail page SHALL present the fencer's registration as confirmed rather than as reserved awaiting payment, and SHALL state no expiry date and no outstanding balance. The selected disciplines, teams and extra services SHALL still be listed with their amounts and total, aligned as `Registration management` fixes, because what the tournament costs is information the fencer needs.

Cancellation SHALL be offered as usual. Its confirmation SHALL ask for confirmation alone, with no mention of refunds, because Squire has taken nothing to refund. Amendment, the roster editor and the queue positions SHALL be unaffected by the payments feature.

#### Scenario: Registration reads as confirmed
- **WHEN** a fencer opens a registration on a payments-off tournament
- **THEN** it is presented as confirmed, with no expiry date, no outstanding balance and no payment prompt

#### Scenario: Amounts still shown
- **WHEN** that registration holds two disciplines and an extra service
- **THEN** each is listed with its amount and the total closes the column, exactly as on a payments-enabled tournament

#### Scenario: Cancellation mentions no money
- **WHEN** a fencer cancels a registration on a payments-off tournament
- **THEN** the confirmation asks only whether to cancel, saying nothing about refunds

#### Scenario: Rosters unaffected
- **WHEN** a fencer who entered a team on a payments-off tournament opens their registration
- **THEN** the team is listed with its roster and the roster editor is offered as usual

### Requirement: Managing a tournament from its card
A card in any tab SHALL carry a **Spravovat** control when, and only when, the account reading it may manage that tournament — as its Tournament Owner or as a member of its console team. The control SHALL open that tournament's console. It SHALL be the only difference between what an organizer sees on the list and what anyone else sees.

The control SHALL be a link carrying the console's URL, so middle-click and modifier-click open it in a new browser tab, and SHALL be reachable without opening the card: activating it SHALL open the console and SHALL NOT also open the fencer-facing detail the card links to.

It SHALL appear on a past tournament's card as it does on an upcoming one — a held tournament's console is still where its records are read — and SHALL be absent for an anonymous visitor, who may manage nothing.

#### Scenario: Owner sees the control
- **WHEN** a Tournament Owner opens the tournament list and their tournament is listed
- **THEN** that card carries a Spravovat control and no other card does

#### Scenario: Console team member sees the control
- **WHEN** a console team member who is not the owner opens the same list
- **THEN** the card carries the same control

#### Scenario: Plain fencer sees no control
- **WHEN** a fencer who neither owns nor staffs any tournament opens the list
- **THEN** no card carries a Spravovat control

#### Scenario: The control opens the console, not the detail
- **WHEN** an organizer activates Spravovat on a card
- **THEN** that tournament's console opens and the fencer-facing detail does not

#### Scenario: The control is a link
- **WHEN** an organizer middle-clicks Spravovat
- **THEN** the console opens in a new browser tab at that tournament's console URL

#### Scenario: A held tournament can still be managed
- **WHEN** an organizer finds a tournament they ran last month in the Past tab
- **THEN** its card carries the Spravovat control

#### Scenario: Anonymous visitor sees no control
- **WHEN** a visitor with no account opens the list
- **THEN** no card carries a Spravovat control

### Requirement: The default filter tab follows what there is to show
WHEN the URL names no tab, the tab shown SHALL be resolved from what the visitor has to
read, in this order: **Mine** when the account holds entries there, then **Open** when it
holds any, then **Announced**. An anonymous visitor, having no Mine, SHALL start the same
sequence at Open. The rule exists so that the landing screen is never an empty list while
another tab has something in it.

Resolution SHALL happen once per visit to the bare URL, from the lists as they arrive, and
SHALL NOT re-run afterwards: a tab the visitor selected SHALL stand, and a list that empties
while they read it SHALL NOT move them off the tab they are on. While the lists are still
arriving the page SHALL show the design system's loading treatment rather than a tab chosen
on incomplete information and then swapped.

Resolution SHALL push no browser history entry and SHALL leave the URL as `/`.

#### Scenario: Account with its own tournaments opens on Mine
- **WHEN** a fencer holding a registration for an upcoming tournament opens `/`
- **THEN** the Mine tab is shown

#### Scenario: Account with nothing of its own opens on Open
- **WHEN** a fencer with no registration and no organized tournament opens `/` while registration is open somewhere
- **THEN** the Open tab is shown

#### Scenario: Nothing open falls back to Announced
- **WHEN** that fencer opens `/` while no tournament has registration open but two are announced
- **THEN** the Announced tab is shown

#### Scenario: Anonymous visitor opens on Open
- **WHEN** a visitor with no account opens `/` while registration is open somewhere
- **THEN** the Open tab is shown

#### Scenario: Anonymous visitor with nothing open
- **WHEN** a visitor with no account opens `/` while no registration is open
- **THEN** the Announced tab is shown

#### Scenario: A chosen tab is not overridden
- **WHEN** a fencer whose Mine list is non-empty opens `/?tab=announced`
- **THEN** the Announced tab is shown and no resolution takes place

#### Scenario: Resolution does not repeat
- **WHEN** a visitor lands on the resolved Open tab and the last open registration closes while they read it
- **THEN** they stay on the Open tab, which shows its empty-state message, rather than being moved to Announced

#### Scenario: No history entry for the default
- **WHEN** a fencer opens `/`, lands on the resolved tab, and presses Back
- **THEN** they leave the application rather than stepping through a resolved tab
