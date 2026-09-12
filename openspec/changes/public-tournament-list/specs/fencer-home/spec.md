## MODIFIED Requirements

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

### Requirement: Navigation rewiring
The tournament list SHALL be the landing screen for every visitor, signed in or not, whatever role they hold. The tournament picker SHALL remain at its own URL, reachable through the account menu's My tournaments entry, and SHALL NOT contain the organizer plea section (the plea lives on the Profile page). The picker SHALL remain the only screen listing a tournament that the public list cannot show — a draft, or a cancelled tournament — which is why the Spravovat control on a card does not replace it.

Creating a tournament SHALL be offered from the account menu (`tournament-admin`), so an organizer reaches it from any screen rather than only from the picker.

#### Scenario: Organizer lands on Fencer Home
- **WHEN** an organizer logs in
- **THEN** they land on the tournament list, the same one every visitor sees, and reach the tournament picker via the account menu

#### Scenario: Plea only on profile
- **WHEN** a plain fencer opens the tournament picker via the account menu
- **THEN** no plea section is shown there

#### Scenario: A draft is still reachable
- **WHEN** an organizer whose only tournament is an unpublished draft opens the picker
- **THEN** the draft is listed there, marked as a draft, and its console opens from that row

## ADDED Requirements

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
