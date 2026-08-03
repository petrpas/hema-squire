## ADDED Requirements

### Requirement: Every screen has a URL
The application SHALL address each of its screens by a URL, and the browser's address bar
SHALL always name the screen on display. The scheme SHALL be:

| path | screen |
| --- | --- |
| `/` | Fencer Home, Open filter tab |
| `/?tab=announced` \| `open` \| `past` \| `mine` | Fencer Home on that filter tab |
| `/t/:slug` | the tournament's fencer-facing detail page |
| `/organizer` | the tournament picker |
| `/organizer/:slug/console` | that tournament's console, Load phase |
| `/organizer/:slug/console/:phase` | that tournament's console on that phase |
| `/admin` | the admin panel |
| `/profile` | the profile page |

Navigating to a screen SHALL change the URL, and entering a URL SHALL open that screen, in
both directions and for every row of the table. No screen SHALL be reachable only through
in-memory state.

#### Scenario: Address bar follows navigation
- **WHEN** an organizer moves from Fencer Home to the picker and opens a tournament's console
- **THEN** the address bar reads `/`, then `/organizer`, then `/organizer/<slug>/console/setup` or the phase opened, without the page being reloaded

#### Scenario: URL opens the screen
- **WHEN** a logged-in fencer types `/t/spring-open-2026` into a fresh tab
- **THEN** the tournament detail page for `spring-open-2026` opens directly, with no intermediate landing on Fencer Home

#### Scenario: Console short URL keeps working
- **WHEN** a logged-in organizer opens `/organizer/spring-open-2026/console`
- **THEN** the console opens on the Load phase and the URL is left as typed

### Requirement: Back, forward, and refresh
Screen-to-screen transitions SHALL push browser history entries, so that Back returns to the
previously displayed screen and Forward returns to the one left. Selecting a Fencer Home
filter tab and switching a console phase SHALL each push an entry, because both are named by
the URL. State that the URL does not name — the tournament detail's `Tournament`/`Register`
tabs, the Setup section tabs, the Setup preview tabs, open dialogs, and in-progress sheet
edits — SHALL NOT push entries.

Reloading the page SHALL redisplay the same screen with the same URL-borne state: the same
tournament, the same filter tab, the same console phase.

Navigation the user did not step into — logging out, and being shown Login for a route they
requested — SHALL replace the current entry rather than push one, so that Back never returns
to a screen the user was moved off.

#### Scenario: Back returns to the previous screen
- **WHEN** a fencer opens a tournament from Fencer Home and presses Back
- **THEN** Fencer Home is shown again, on the filter tab the tournament was opened from, and the application is not left

#### Scenario: Back steps between console phases
- **WHEN** an organizer opens the console on Load, switches to Matching on HR, then to Payments, and presses Back twice
- **THEN** the console shows Matching on HR, then Load, each time reading the phase from the URL

#### Scenario: Refresh preserves the screen
- **WHEN** the browser is refreshed on `/organizer/spring-open-2026/console/payments`
- **THEN** the Payments phase of that tournament's console is shown again after the reload

#### Scenario: Refresh preserves the filter tab
- **WHEN** a fencer selects the Mine tab and refreshes the page
- **THEN** the address bar reads `/?tab=mine` and the Mine tab is shown again

#### Scenario: Within-screen state creates no history
- **WHEN** a fencer opens a tournament detail, switches to its `Register` tab, and presses Back
- **THEN** Fencer Home is shown — Back leaves the detail rather than returning to its `Tournament` tab

#### Scenario: Back after logout does not re-enter
- **WHEN** an organizer logs out from the console and presses Back
- **THEN** they are not returned to the console

### Requirement: Deep links resolve their own data
A screen addressed by URL SHALL obtain everything it needs from that URL and the API, without
depending on data handed to it by the screen a user would otherwise have come from. While a
screen is resolving its data it SHALL show the design system's loading treatment — static
text, never a spinner or animated progress indicator.

#### Scenario: Console resolves its tournament from the slug
- **WHEN** an organizer opens `/organizer/spring-open-2026/console/matching` without having visited the picker
- **THEN** the console fetches that tournament itself, shows the loading text while it does, and then renders the Matching on HR phase

#### Scenario: Detail resolves its tournament from the slug
- **WHEN** a fencer opens `/t/spring-open-2026` directly
- **THEN** the tournament detail page renders that tournament, on its `Tournament` tab

### Requirement: Unauthenticated visits keep their destination
An unauthenticated visit to any route SHALL present the Login screen while leaving the
requested URL in the address bar, and on successful authentication SHALL show the originally
requested screen — path, tournament slug, console phase, and query string alike. Logging in
SHALL NOT leave a history entry that Back would return to afterwards. Logging out SHALL
return to `/`.

#### Scenario: Deep link survives login
- **WHEN** a logged-out visitor follows `/organizer/spring-open-2026/console/payments`
- **THEN** Login is shown, and after they authenticate the Payments phase of that tournament's console is displayed

#### Scenario: Query string survives login
- **WHEN** a logged-out visitor follows `/?tab=mine`
- **THEN** Login is shown, and after they authenticate Fencer Home opens on the Mine tab

#### Scenario: Back after login does not return to Login
- **WHEN** a visitor authenticates from a deep link and presses Back
- **THEN** the Login screen is not shown again

#### Scenario: Logout returns home
- **WHEN** an authenticated user logs out from any screen
- **THEN** the Login screen is shown at `/`

### Requirement: Unknown URLs end at a not-found screen
A URL that names no screen SHALL render a not-found screen carrying the page's title, one
line of prose explaining that the address leads nowhere, and a link home. A tournament slug
that does not exist, or that the account may not open, SHALL render the same screen rather
than an empty or partly rendered one, and SHALL be indistinguishable from a slug that does
not exist, so that the URL discloses nothing about which tournaments exist. A console phase
segment outside the known phases SHALL render the not-found screen rather than falling back
to a default phase.

The not-found screen SHALL obey the design prohibitions: no emoji, no exclamation marks, no
default-blue link, sentence case throughout.

#### Scenario: Nonsense path
- **WHEN** a logged-in fencer opens `/nonsense`
- **THEN** the not-found screen is shown with a link back to Fencer Home

#### Scenario: Unknown tournament slug
- **WHEN** a fencer opens `/t/no-such-tournament`
- **THEN** the not-found screen is shown, not a blank detail page

#### Scenario: Tournament the account may not open
- **WHEN** an organizer opens `/organizer/<slug>/console` for a tournament they have no access to
- **THEN** the not-found screen is shown, worded identically to the unknown-slug case

#### Scenario: Unknown console phase
- **WHEN** an organizer opens `/organizer/spring-open-2026/console/invoicing`
- **THEN** the not-found screen is shown rather than the Load phase

### Requirement: Navigation targets are links
A control whose whole purpose is to open another screen — a tournament card on Fencer Home, a
row in the tournament picker, a Fencer Home filter tab, and each account-menu destination —
SHALL be a link carrying its target URL, so that middle-click and modifier-click open it in a
new tab and the browser offers to copy its address. Such links SHALL keep the visual
treatment of the control they replace and SHALL NOT be rendered in the browser's default link
colour or with a default underline.

Controls that act on the current screen rather than opening another — the console's phase
tabs, dialog buttons, form submissions — MAY remain buttons.

#### Scenario: Middle-click opens a tournament in a new tab
- **WHEN** a fencer middle-clicks a tournament card on Fencer Home
- **THEN** that tournament's detail page opens in a new browser tab at `/t/<slug>`

#### Scenario: Copy link address
- **WHEN** a fencer opens the context menu on a tournament card
- **THEN** the browser offers to copy the link address, and the copied address is the tournament's `/t/<slug>` URL

#### Scenario: Links keep their appearance
- **WHEN** the tournament cards, filter tabs and picker rows render as links
- **THEN** they look exactly as they did as buttons, with no default-blue text and no default underline
